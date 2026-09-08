import numpy as np
from collections import deque
import matplotlib.pyplot as plt
from numba import jit

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
np.random.seed(42)  # 固定随机种子，复现结果

# ====================== 原题物理参数 ======================
L_CUBE = 10000    # 微构边长 nm
HALF_L = 5000     # 半边长 ±5000
V_CUBE = L_CUBE ** 3
# 介质A参数
rA = 30
hA = 5000
VA = np.pi * (rA ** 2) * hA
D_CONDUCT = 1.8   # 导通临界表面距离 nm
P_TARGET = 0.90   # 导通概率下限

# ---------- 【提速修改关键参数】----------
EPS_PHI = 0.01    # 二分收敛精度不变（题目要求保留两位小数）
FINE_STEP = 0.005
CONF_ERR = 0.08    # 置信误差放宽，提前停止仿真
MIN_SIM = 80
BATCH_SIM = 300    # 单次批量放大，减少循环开销

# 周期偏移向量：仅y、z方向周期边界，x方向为极板（非周期）
# 共 1×3×3 = 9 个偏移
OFFSETS = np.array([
    [0, -L_CUBE, -L_CUBE], [0, -L_CUBE, 0], [0, -L_CUBE, L_CUBE],
    [0, 0, -L_CUBE],       [0, 0, 0],       [0, 0, L_CUBE],
    [0, L_CUBE, -L_CUBE],  [0, L_CUBE, 0],  [0, L_CUBE, L_CUBE],
], dtype=np.float64)

# ====================== Numba几何底层 ======================
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
                if max(a0,a1) < cm or min(a0,a1) > cM:
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

@jit(nopython=True, fastmath=True, cache=True)
def calc_pair_surf_dist(p0i, p1i, p0j, p1j):
    min_seg_d = 1e12
    for k in range(OFFSETS.shape[0]):
        shift = OFFSETS[k]
        d = seg_dist(p0i, p1i, p0j+shift, p1j+shift)
        if d < min_seg_d:
            min_seg_d = d
    return min_seg_d - 2 * rA

@jit(nopython=True, fastmath=True, cache=True)
def seg_plane_min_dist(p0, p1):
    # 圆柱到极板距离：不考虑周期偏移（x方向是极板，非周期）
    x0, x1 = p0[0], p1[0]
    x_min = min(x0, x1)
    x_max = max(x0, x1)
    L_plane = -HALF_L
    R_plane = HALF_L
    dL = min(abs(x0-L_plane), abs(x1-L_plane)) - rA
    dR = min(abs(x0-R_plane), abs(x1-R_plane)) - rA
    if L_plane >= x_min - 1e-9 and L_plane <= x_max + 1e-9:
        dL = -rA
    if R_plane >= x_min - 1e-9 and R_plane <= x_max + 1e-9:
        dR = -rA
    return dL, dR

# ====================== 介质生成 ======================
def gen_one_cyl():
    while True:
        p0 = np.random.uniform(-HALF_L, HALF_L, size=3)
        vec = np.random.randn(3)
        vec = vec / np.linalg.norm(vec)
        p1 = p0 + vec * hA
        if seg_has_valid_region(p0, p1):
            return p0, p1

def gen_cyl_array(N):
    arr = np.zeros((N, 2, 3), dtype=np.float64)
    for i in range(N):
        p0, p1 = gen_one_cyl()
        arr[i,0,:] = p0
        arr[i,1,:] = p1
    return arr

# 无jit，避免numba列表性能衰减
def build_adjacency(seg_arr, N):
    adj = [[] for _ in range(N)]
    for i in range(N):
        p0i = seg_arr[i,0,:]
        p1i = seg_arr[i,1,:]
        for j in range(i+1, N):
            p0j = seg_arr[j,0,:]
            p1j = seg_arr[j,1,:]
            surf_d = calc_pair_surf_dist(p0i, p1i, p0j, p1j)
            if surf_d <= D_CONDUCT:
                adj[i].append(j)
                adj[j].append(i)
    return adj

# ====================== 单次仿真 ======================
def single_simulation(N):
    seg_arr = gen_cyl_array(N)
    n = N
    S = n
    T = n+1
    adj_all = [[] for _ in range(n+2)]

    # 绑定极板
    for idx in range(n):
        p0 = seg_arr[idx,0,:]
        p1 = seg_arr[idx,1,:]
        dl, dr = seg_plane_min_dist(p0, p1)
        if dl <= D_CONDUCT:
            adj_all[S].append(idx)
            adj_all[idx].append(S)
        if dr <= D_CONDUCT:
            adj_all[T].append(idx)
            adj_all[idx].append(T)

    # 介质内部连通
    inner_adj = build_adjacency(seg_arr, n)
    for i in range(n):
        adj_all[i].extend(inner_adj[i])

    # BFS 判断跨极板导通
    vis = [False]*(n+2)
    q = deque([S])
    vis[S] = True
    while q:
        u = q.popleft()
        if u == T:
            return True
        for v in adj_all[u]:
            if not vis[v]:
                vis[v] = True
                q.append(v)
    return False

# ====================== 蒙特卡洛概率估计 ======================
def monte_carlo_phi(N):
    total_run = 0
    success = 0
    while True:
        batch_ok = 0
        for _ in range(BATCH_SIM):
            if single_simulation(N):
                batch_ok += 1
        success += batch_ok
        total_run += BATCH_SIM
        p_est = success / total_run
        pc = np.clip(p_est, 1e-9, 1-1e-9)
        err_95 = 1.96 * np.sqrt(pc * (1-pc) / total_run)
        if total_run >= MIN_SIM and err_95 <= CONF_ERR:
            return p_est, err_95

def phi_to_N(phi):
    total_vol = V_CUBE * phi / 100.0
    return round(total_vol / VA)

# ====================== 绘图 ======================
def plot_log(records, best_phi):
    if not records:
        return
    phis, ps, errs, widths = zip(*records)
    iters = list(range(1, len(records)+1))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12,5))
    ax1.errorbar(phis, ps, yerr=errs, fmt='o-', capsize=4, color='#1f77b4')
    ax1.axhline(P_TARGET, c='r', ls='--', label=f'目标P={P_TARGET}')
    ax1.axvline(best_phi, c='g', ls='-.', label=f'最小φ={best_phi:.2f}%')
    ax1.set_xlabel('体积分数 φ (%)')
    ax1.set_ylabel('导通概率 P')
    ax1.set_title('二分迭代概率曲线')
    ax1.legend()
    ax1.grid(alpha=0.6)
    ax2.plot(iters, widths, 'o-', c='#d62728')
    ax2.axhline(EPS_PHI, c='blue', ls='--', label=f'精度{EPS_PHI}%')
    ax2.set_xlabel('迭代次数')
    ax2.set_ylabel('区间宽度 (%)')
    ax2.set_title('二分收敛')
    ax2.set_yscale('log')
    ax2.legend()
    ax2.grid(alpha=0.6)
    plt.tight_layout()
    plt.savefig('prob_binary.png', dpi=300)
    plt.savefig('prob_binary.pdf')
    plt.close()

# ====================== 精细扫描 ======================
def fine_scan_verify(start_phi, end_phi, step):
    print("\n===== 精细扫描校验（文档要求） =====")
    min_ok = None
    current = start_phi
    while current <= end_phi + 1e-6:
        N = phi_to_N(current)
        p, err = monte_carlo_phi(N)
        flag = "达标" if p >= P_TARGET else "不达标"
        print(f"φ={current:.3f}% | N={N} | P={p:.4f} ±{err:.4f} | {flag}")
        if p >= P_TARGET:
            if min_ok is None or current < min_ok:
                min_ok = current
        current += step
    return min_ok

# ====================== 二分主程序 ======================
def binary_search_main():
    log_file = open("problem3_log.txt", "w", encoding="utf-8")
    log_file.write("迭代,体积分数(%),介质数,概率,置信误差,区间宽度\n")
    phi_low = 0.70
    phi_high = 1.00
    best_phi = phi_high
    record_list = []
    iter_num = 0
    print("===== 华数杯A题 问题3 提速轻量化版本 =====")
    while phi_high - phi_low > EPS_PHI:
        iter_num += 1
        mid_phi = (phi_low + phi_high) / 2
        N_mid = phi_to_N(mid_phi)
        p_mid, err_mid = monte_carlo_phi(N_mid) if N_mid>0 else (0.0, 0.0)
        width = phi_high - mid_phi
        record_list.append((mid_phi, p_mid, err_mid, width))
        print(f"迭代{iter_num} | φ={mid_phi:.4f} | N={N_mid} | P={p_mid:.4f} ±{err_mid:.4f}")
        log_file.write(f"{iter_num},{mid_phi:.4f},{N_mid},{p_mid},{err_mid},{width:.4f}\n")
        if p_mid >= P_TARGET:
            best_phi = mid_phi
            phi_high = mid_phi
        else:
            phi_low = mid_phi
    log_file.close()
    plot_log(record_list, best_phi)

    # 精细扫描区间
    scan_s = max(0.50, best_phi - 0.02)
    scan_e = best_phi + 0.02
    raw_min = fine_scan_verify(scan_s, scan_e, FINE_STEP)
    final_res = round(raw_min, 2)
    print(f"\n===== 最终结果 =====")
    print(f'满足导通概率≥90%最低体积分数：{final_res:.2f} %')
    print(f'对应介质数量：{phi_to_N(final_res)} 根')
    print(f'精细扫描原始临界值：{raw_min:.4f} %')
    return final_res

if __name__ == "__main__":
    res = binary_search_main()