import numpy as np
from collections import deque
import time
import matplotlib.pyplot as plt
from numba import jit
import os
import hashlib

# ====================== 物理参数 ======================
L_CUBE = 10000
HALF_L = 5000
V_CUBE = L_CUBE ** 3
rA, hA = 30, 5000
VA = np.pi * rA**2 * hA
rB = 200
VB = 4/3 * np.pi * rB**3
D_CONDUCT = 1.8
P_TARGET = 0.90

# 成本换算（元/μm³ → 元/nm³）
costA = 1.05 / 1e9
costB = 0.05 / 1e9

# ====================== 仿真精度与搜索参数（优化后） ======================
# 粗扫：少量仿真，大步长
COARSE_BATCH = 25          # 每次批量仿真数
COARSE_MIN = 25            # 最少仿真数（达到即可，不要求严格置信）
# 细扫：较高精度，但适当放宽误差，速度优先
FINE_BATCH = 120
FINE_MIN = 120
CONF_ERR = 0.08            # 放宽至 8% 半宽（仍可分辨 0.90 阈值）

# 搜索网格步长
A_STEP_COARSE = 25
B_STEP_COARSE = 100
A_MAX = 200
B_MAX = 500
# 细扫邻域范围
A_NEIGHBOR = 20
B_NEIGHBOR = 100

# 固定随机种子以便复现（正式运行可注释）
np.random.seed(2026)

# ====================== 周期偏移向量 ======================
# 周期偏移：仅y、z方向周期边界，x方向为极板（非周期）
# 共 1×3×3 = 9 个偏移
OFFSETS = np.array([
    [0, -L_CUBE, -L_CUBE], [0, -L_CUBE, 0], [0, -L_CUBE, L_CUBE],
    [0, 0, -L_CUBE],       [0, 0, 0],       [0, 0, L_CUBE],
    [0, L_CUBE, -L_CUBE],  [0, L_CUBE, 0],  [0, L_CUBE, L_CUBE],
], dtype=np.float64)

# ====================== Numba 几何核心（不变） ======================
@jit(nopython=True, fastmath=True, cache=True)
def seg_dist(p0, p1, q0, q1):
    a = p1 - p0
    b = q1 - q0
    c = q0 - p0
    a_dot_a = np.dot(a, a)
    b_dot_b = np.dot(b, b)
    a_dot_b = np.dot(a, b)
    a_dot_c = np.dot(a, c)
    b_dot_c = np.dot(b, c)
    denom = a_dot_a * b_dot_b - a_dot_b ** 2
    if denom < 1e-12:
        t0, t1 = 0.0, 0.0
    else:
        t0 = (a_dot_c * b_dot_b - b_dot_c * a_dot_b) / denom
        t1 = (a_dot_c * a_dot_b - b_dot_c * a_dot_a) / denom
    t0 = max(0.0, min(1.0, t0))
    t1 = max(0.0, min(1.0, t1))
    p = p0 + t0 * a
    q = q0 + t1 * b
    return np.linalg.norm(p - q)

@jit(nopython=True, fastmath=True, cache=True)
def point_seg_dist(pt, p0, p1):
    a = p1 - p0
    b = pt - p0
    t = np.dot(b, a) / np.dot(a, a)
    t = max(0.0, min(1.0, t))
    proj = p0 + t * a
    return np.linalg.norm(pt - proj)

@jit(nopython=True, fastmath=True, cache=True)
def seg_has_valid_region(p0, p1):
    cube_min = np.array([-HALF_L, -HALF_L, -HALF_L])
    cube_max = np.array([HALF_L, HALF_L, HALF_L])
    seg_dir = p1 - p0
    seg_len = np.linalg.norm(seg_dir)
    if seg_len < 1e-9:
        return False
    seg_dir = seg_dir / seg_len
    for k in range(OFFSETS.shape[0]):
        shift_vec = OFFSETS[k]
        s0 = p0 + shift_vec
        s1 = p1 + shift_vec
        tmin, tmax = 0.0, 1.0
        hit = True
        for axis in range(3):
            d = seg_dir[axis]
            a0, a1 = s0[axis], s1[axis]
            cm, cM = cube_min[axis], cube_max[axis]
            if abs(d) < 1e-12:
                if max(a0, a1) < cm or min(a0, a1) > cM:
                    hit = False
                    break
                continue
            t1 = (cm - a0) / d
            t2 = (cM - a0) / d
            t_low = min(t1, t2)
            t_high = max(t1, t2)
            tmin = max(tmin, t_low)
            tmax = min(tmax, t_high)
            if tmin > tmax + 1e-12:
                hit = False
                break
        if hit:
            return True
    return False

# ---------- 圆柱-圆柱 ----------
@jit(nopython=True, fastmath=True, cache=True)
def cyl_cyl_surf_dist(p0i, p1i, p0j, p1j):
    min_seg = 1e12
    for k in range(OFFSETS.shape[0]):
        shift = OFFSETS[k]
        d = seg_dist(p0i, p1i, p0j + shift, p1j + shift)
        if d < min_seg:
            min_seg = d
    return min_seg - 2 * rA

# ---------- 圆柱到极板（x方向非周期，直接计算） ----------
@jit(nopython=True, fastmath=True, cache=True)
def cyl_plane_min_dist(p0, p1):
    x0, x1 = p0[0], p1[0]
    x_min = min(x0, x1)
    x_max = max(x0, x1)
    L_plane = -HALF_L
    R_plane = HALF_L
    # 到左极板
    if L_plane >= x_min - 1e-9 and L_plane <= x_max + 1e-9:
        dL = -rA
    else:
        dL = min(abs(x0 - L_plane), abs(x1 - L_plane)) - rA
    # 到右极板
    if R_plane >= x_min - 1e-9 and R_plane <= x_max + 1e-9:
        dR = -rA
    else:
        dR = min(abs(x0 - R_plane), abs(x1 - R_plane)) - rA
    return dL, dR

# ---------- 球体-球体 ----------
@jit(nopython=True, fastmath=True, cache=True)
def sphere_sphere_surf_dist(c1, c2):
    min_d = 1e12
    for k in range(OFFSETS.shape[0]):
        shift = OFFSETS[k]
        d = np.linalg.norm(c1 - (c2 + shift))
        if d < min_d:
            min_d = d
    return min_d - 2 * rB

# ---------- 圆柱-球体 ----------
@jit(nopython=True, fastmath=True, cache=True)
def cyl_sphere_surf_dist(p0, p1, c):
    min_d = 1e12
    for k in range(OFFSETS.shape[0]):
        shift = OFFSETS[k]
        d = point_seg_dist(c + shift, p0, p1)
        if d < min_d:
            min_d = d
    return min_d - rA - rB

# ---------- 球体到极板（x方向非周期，直接计算） ----------
@jit(nopython=True, fastmath=True, cache=True)
def sphere_plane_dist(c):
    dL = abs(c[0] - (-HALF_L)) - rB
    dR = abs(c[0] - HALF_L) - rB
    return dL, dR

# ====================== 随机生成 ======================
def gen_one_cyl():
    while True:
        p0 = np.random.uniform(-HALF_L, HALF_L, size=3)
        vec = np.random.randn(3)
        vec = vec / np.linalg.norm(vec)
        p1 = p0 + vec * hA
        if seg_has_valid_region(p0, p1):
            return p0, p1

def gen_one_sphere():
    return np.random.uniform(-HALF_L, HALF_L, size=3)

def gen_cyl_array(nA):
    arr = np.zeros((nA, 2, 3), dtype=np.float64)
    for i in range(nA):
        p0, p1 = gen_one_cyl()
        arr[i, 0, :] = p0
        arr[i, 1, :] = p1
    return arr

def gen_sphere_array(nB):
    arr = np.zeros((nB, 3), dtype=np.float64)
    for i in range(nB):
        arr[i, :] = gen_one_sphere()
    return arr

# ====================== 单次仿真（混合） ======================
def single_simulation_mix(nA, nB):
    total = nA + nB
    S, T = total, total + 1
    adj = [[] for _ in range(total + 2)]
    cyls = gen_cyl_array(nA) if nA else np.empty((0, 2, 3))
    spheres = gen_sphere_array(nB) if nB else np.empty((0, 3))

    # 到极板
    for i in range(nA):
        p0, p1 = cyls[i, 0, :], cyls[i, 1, :]
        dL, dR = cyl_plane_min_dist(p0, p1)
        if dL <= D_CONDUCT:
            adj[S].append(i); adj[i].append(S)
        if dR <= D_CONDUCT:
            adj[T].append(i); adj[i].append(T)
    for j in range(nB):
        idx = nA + j
        c = spheres[j]
        dL, dR = sphere_plane_dist(c)
        if dL <= D_CONDUCT:
            adj[S].append(idx); adj[idx].append(S)
        if dR <= D_CONDUCT:
            adj[T].append(idx); adj[idx].append(T)

    # A-A
    for i in range(nA):
        p0i, p1i = cyls[i, 0, :], cyls[i, 1, :]
        for j in range(i+1, nA):
            if cyl_cyl_surf_dist(p0i, p1i, cyls[j,0,:], cyls[j,1,:]) <= D_CONDUCT:
                adj[i].append(j); adj[j].append(i)
    # B-B
    for i in range(nB):
        ci = spheres[i]
        for j in range(i+1, nB):
            if sphere_sphere_surf_dist(ci, spheres[j]) <= D_CONDUCT:
                ii = nA+i; jj = nA+j
                adj[ii].append(jj); adj[jj].append(ii)
    # A-B
    for i in range(nA):
        p0, p1 = cyls[i, 0, :], cyls[i, 1, :]
        for j in range(nB):
            if cyl_sphere_surf_dist(p0, p1, spheres[j]) <= D_CONDUCT:
                adj[i].append(nA+j); adj[nA+j].append(i)

    # BFS
    visited = [False] * (total+2)
    q = deque([S]); visited[S] = True
    while q:
        u = q.popleft()
        if u == T:
            return True
        for v in adj[u]:
            if not visited[v]:
                visited[v] = True
                q.append(v)
    return False

# ====================== 蒙特卡洛（带缓存） ======================
_cache = {}
def monte_carlo_mix(nA, nB, batch_sim, min_sim):
    key = (nA, nB, batch_sim, min_sim)  # 不同精度分开缓存
    if key in _cache:
        return _cache[key]
    total_run, success = 0, 0
    while True:
        for _ in range(batch_sim):
            if single_simulation_mix(nA, nB):
                success += 1
        total_run += batch_sim
        p_est = success / total_run
        pc = np.clip(p_est, 1e-9, 1-1e-9)
        err_95 = 1.96 * np.sqrt(pc*(1-pc) / total_run)
        if total_run >= min_sim and err_95 <= CONF_ERR:
            result = (p_est, err_95, total_run)
            _cache[key] = result
            return result

# ====================== 成本 ======================
def total_cost(nA, nB):
    return (nA * VA) * costA + (nB * VB) * costB

# ====================== 日志绘图 ======================
def log_and_plot(records, best_config, best_cost, best_prob, runtime):
    if not records:
        return
    costs = [r[4] for r in records]
    probs = [r[2] for r in records]
    A_vals = [r[0] for r in records]
    B_vals = [r[1] for r in records]

    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12,5))
    # 成本-概率
    ok = [p >= P_TARGET for p in probs]
    ax1.scatter(costs, probs, c=['g' if o else 'r' for o in ok], alpha=0.6, s=20)
    ax1.axhline(P_TARGET, color='b', linestyle='--', label=f'Target {P_TARGET}')
    if best_config:
        ax1.scatter(best_cost, best_prob, color='gold', s=100, marker='*', label='Best')
    ax1.set_xlabel('Total Cost (yuan)')
    ax1.set_ylabel('Conduction Probability')
    ax1.legend(); ax1.grid(alpha=0.4)
    # 参数空间
    sc = ax2.scatter(A_vals, B_vals, c=probs, cmap='coolwarm', s=30, vmin=0.7, vmax=1.0)
    if best_config:
        ax2.scatter(best_config[0], best_config[1], color='gold', s=150, marker='*')
    ax2.set_xlabel('Number of Medium A')
    ax2.set_ylabel('Number of Medium B')
    ax2.set_title('Probability Distribution')
    plt.colorbar(sc, ax=ax2)
    plt.tight_layout()
    plt.savefig('problem4_optimized.png', dpi=300)
    plt.close()

    # 日志
    with open('problem4_optimized_log.txt', 'w') as f:
        f.write(f"Total runtime: {runtime:.1f} s\n")
        f.write("nA,nB,prob,error,cost,feasible\n")
        for r in records:
            f.write(f"{r[0]},{r[1]},{r[2]:.4f},{r[3]:.4f},{r[4]:.6f},{'Y' if r[2]>=P_TARGET else 'N'}\n")
        if best_config:
            f.write(f"\nBest: A={best_config[0]}, B={best_config[1]}, cost={best_cost:.6f}, prob={best_prob:.4f}\n")

# ====================== 主搜索（优化版） ======================
def search_optimal():
    print("===== Problem 4 Optimization Search (Fast Version) =====")
    start_time = time.time()
    records = []
    best_cost = np.inf
    best_config = None
    best_prob = 0.0

    # ---------- 粗扫 ----------
    print(f"\n--- Coarse Scan (A step={A_STEP_COARSE}, B step={B_STEP_COARSE}) ---")
    A_range = range(0, A_MAX+1, A_STEP_COARSE)
    B_range = range(0, B_MAX+1, B_STEP_COARSE)
    total_combos = len(A_range)*len(B_range)
    cnt = 0
    for nA in A_range:
        for nB in B_range:
            if nA==0 and nB==0:
                continue
            cnt += 1
            if cnt % 30 == 0:
                print(f"  Coarse progress: {cnt}/{total_combos}")
            cost_val = total_cost(nA, nB)
            p, err, sims = monte_carlo_mix(nA, nB, COARSE_BATCH, COARSE_MIN)
            records.append((nA, nB, p, err, cost_val))
            if p >= P_TARGET and cost_val < best_cost:
                best_cost = cost_val
                best_config = (nA, nB)
                best_prob = p
                print(f"  [Coarse] A={nA}, B={nB}, cost={cost_val:.4f}, P={p:.3f} (sim={sims})")

    if best_config is None:
        print("\nNo feasible solution in coarse scan, please increase range.")
        log_and_plot(records, None, None, None, time.time()-start_time)
        return

    print(f"\nCoarse best: A={best_config[0]}, B={best_config[1]}, cost={best_cost:.4f}, P={best_prob:.3f}")

    # ---------- 细扫 ----------
    A0, B0 = best_config
    A_low = max(0, A0 - A_NEIGHBOR)
    A_high = min(A_MAX, A0 + A_NEIGHBOR)
    B_low = max(0, B0 - B_NEIGHBOR)
    B_high = min(B_MAX, B0 + B_NEIGHBOR)
    print(f"\n--- Fine Scan (A in [{A_low},{A_high}], B in [{B_low},{B_high}]) ---")
    for nA in range(A_low, A_high+1):
        for nB in range(B_low, B_high+1):
            cost_val = total_cost(nA, nB)
            if cost_val >= best_cost and best_config is not None:
                continue  # 安全剪枝
            p, err, sims = monte_carlo_mix(nA, nB, FINE_BATCH, FINE_MIN)
            records.append((nA, nB, p, err, cost_val))
            if p >= P_TARGET and cost_val < best_cost:
                best_cost = cost_val
                best_config = (nA, nB)
                best_prob = p
                print(f"  [Fine] A={nA}, B={nB}, cost={cost_val:.4f}, P={p:.3f} (sim={sims})")

    # ---------- 最终结果 ----------
    runtime = time.time() - start_time
    print("\n===== Optimal Mixed Filling Scheme =====")
    nA_opt, nB_opt = best_config
    volA = nA_opt * VA / V_CUBE * 100
    volB = nB_opt * VB / V_CUBE * 100
    print(f"Medium A: {nA_opt} cylinders, volume fraction {volA:.3f}%")
    print(f"Medium B: {nB_opt} spheres, volume fraction {volB:.3f}%")
    print(f"Conduction probability: {best_prob:.3f} (95% CI half-width {err:.4f})")
    print(f"Total cost: {best_cost:.4f} yuan")
    print(f"Total runtime: {runtime:.1f} s")

    log_and_plot(records, best_config, best_cost, best_prob, runtime)
    print("\nResults saved to problem4_optimized_log.txt and problem4_optimized.png")
    return best_config, best_cost, best_prob

if __name__ == "__main__":
    search_optimal()