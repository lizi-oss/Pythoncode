import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import binom
from numba import njit

# ===================== 全局参数 与问题一完全统一 =====================
BOX_MIN = -5000
BOX_MAX = 5000
BOX_LEN = 10000
LEFT_PLANE = -5000
RIGHT_PLANE = 5000
R_A = 30
L_A = 5000
THRESH = 1.8
CYL_CNT_DIST = 2 * R_A + THRESH    # 61.8nm 两圆柱导通阈值
CYL_PLANE_DIST = R_A + THRESH      # 31.8nm 圆柱极板导通阈值

# 问题2指定体积分数(%)
target_vol_pct = [0.50, 0.60, 0.70, 1.00]
SIM_NUM = 500    # 每组蒙特卡洛仿真次数

# ===================== 复用问题一标准线段最短距离（完全对齐判定逻辑） =====================
@njit
def seg_min_dist(a0x,a0y,a0z,a1x,a1y,a1z, b0x,b0y,b0z,b1x,b1y,b1z):
    ux = a1x - a0x
    uy = a1y - a0y
    uz = a1z - a0z
    vx = b1x - b0x
    vy = b1y - b0y
    vz = b1z - b0z
    wx = a0x - b0x
    wy = a0y - b0y
    wz = a0z - b0z

    a = ux*ux + uy*uy + uz*uz
    b = vx*vx + vy*vy + vz*vz
    c = ux*vx + uy*vy + uz*vz
    d = ux*wx + uy*wy + uz*wz
    e = vx*wx + vy*wy + vz*wz
    denom = a * b - c * c
    eps = 1e-14
    s, t = 0.0, 0.0
    if denom > eps:
        s = (c*e - b*d) / denom
        t = (a*e - c*d) / denom
    s = max(0.0, min(1.0, s))
    t = max(0.0, min(1.0, t))

    px = a0x + s*ux
    py = a0y + s*uy
    pz = a0z + s*uz
    qx = b0x + t*vx
    qy = b0y + t*vy
    qz = b0z + t*vz
    dx = px - qx
    dy = py - qy
    dz = pz - qz
    return math.sqrt(dx*dx + dy*dy + dz*dz)

# ===================== 坐标周期折叠 与问题一规则完全一致 =====================
@njit
def fold_coord(x):
    box = BOX_LEN
    x = x % box
    if x > BOX_MAX:
        x -= box
    return x

@njit
def fold_cyl(x0,y0,z0,x1,y1,z1):
    x0 = fold_coord(x0)
    y0 = fold_coord(y0)
    z0 = fold_coord(z0)
    x1 = fold_coord(x1)
    y1 = fold_coord(x1)
    z1 = fold_coord(z1)
    return x0,y0,z0,x1,y1,z1

# ===================== 并查集 与问题一逻辑一致，numba加速 =====================
@njit
def uf_init(n):
    parent = np.arange(n)
    size = np.ones(n, dtype=np.int64)
    return parent, size

@njit
def uf_find(parent, x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x

@njit
def uf_union(parent, size, a, b):
    ra = uf_find(parent, a)
    rb = uf_find(parent, b)
    if ra == rb:
        return False
    if size[ra] < size[rb]:
        ra, rb = rb, ra
    parent[rb] = ra
    size[ra] += size[rb]
    return True

# ===================== 单根圆柱到极板距离 对齐问题一 =====================
@njit
def cyl_plane_dist(x0,y0,z0,x1,y1,z1, plane_x):
    x_min = min(x0, x1)
    x_max = max(x0, x1)
    if x_min <= plane_x <= x_max:
        return 0.0
    return min(abs(x0-plane_x), abs(x1-plane_x))

# ===================== 随机生成单根介质A（生成后自动周期折叠） =====================
@njit
def generate_one_cyl():
    # 生成单位随机方向
    while True:
        ux = np.random.uniform(-1,1)
        uy = np.random.uniform(-1,1)
        uz = np.random.uniform(-1,1)
        r2 = ux*ux + uy*uy + uz*uz
        if 1e-12 < r2 <= 1:
            break
    r = math.sqrt(r2)
    ux /= r
    uy /= r
    uz /= r
    half_L = L_A / 2
    # 随机中心
    cx = np.random.uniform(BOX_MIN, BOX_MAX)
    cy = np.random.uniform(BOX_MIN, BOX_MAX)
    cz = np.random.uniform(BOX_MIN, BOX_MAX)
    # 原始端点
    x0 = cx - half_L * ux
    y0 = cy - half_L * uy
    z0 = cz - half_L * uz
    x1 = cx + half_L * ux
    y1 = cy + half_L * uy
    z1 = cz + half_L * uz
    # 边界折叠
    return fold_cyl(x0,y0,z0,x1,y1,z1)

@njit
def gen_cyl_array(N):
    arr = np.empty((N,6), dtype=np.float64)
    for i in range(N):
        x0,y0,z0,x1,y1,z1 = generate_one_cyl()
        arr[i,0]=x0;arr[i,1]=y0;arr[i,2]=z0
        arr[i,3]=x1;arr[i,4]=y1;arr[i,5]=z1
    return arr

# ===================== 单次仿真导通判定 =====================
@njit
def single_simulation(N):
    cyls = gen_cyl_array(N)
    parent, size = uf_init(N)
    # 两两连通合并
    for i in range(N):
        x0a,y0a,z0a,x1a,y1a,z1a = cyls[i]
        for j in range(i+1, N):
            x0b,y0b,z0b,x1b,y1b,z1b = cyls[j]
            d = seg_min_dist(x0a,y0a,z0a,x1a,y1a,z1a, x0b,y0b,z0b,x1b,y1b,z1b)
            if d <= CYL_CNT_DIST:
                uf_union(parent, size, i, j)
    # 标记接触左右极板
    touch_left = np.zeros(N, dtype=np.bool_)
    touch_right = np.zeros(N, dtype=np.bool_)
    for idx in range(N):
        x0,y0,z0,x1,y1,z1 = cyls[idx]
        dl = cyl_plane_dist(x0,y0,z0,x1,y1,z1, LEFT_PLANE)
        dr = cyl_plane_dist(x0,y0,z0,x1,y1,z1, RIGHT_PLANE)
        if dl <= CYL_PLANE_DIST:
            touch_left[idx] = True
        if dr <= CYL_PLANE_DIST:
            touch_right[idx] = True
    # 判断通路
    left_roots = set()
    for i in range(N):
        if touch_left[i]:
            left_roots.add(uf_find(parent, i))
    for i in range(N):
        if touch_right[i]:
            rt = uf_find(parent, i)
            if rt in left_roots:
                return True
    return False

# ===================== 体积分数换算N 题目规则：四舍五入 =====================
def vol_frac_to_N(pct):
    V_box = BOX_LEN ** 3
    V_A = math.pi * (R_A**2) * L_A
    N_float = pct * V_box / (100 * V_A)
    N_int = round(N_float)
    return N_int, N_float, V_A, V_box

# ===================== 批量蒙特卡洛仿真 =====================
def batch_run(N):
    succ = 0
    for _ in range(SIM_NUM):
        if single_simulation(N):
            succ += 1
    prob = succ / SIM_NUM
    # 95%置信区间
    ci_low, ci_high = binom.interval(0.95, SIM_NUM, prob)
    ci_low = max(ci_low / SIM_NUM, 0.0)
    ci_high = min(ci_high / SIM_NUM, 1.0)
    return succ, prob, ci_low, ci_high

# ===================== 绘图函数【彻底重写，修复之前丑陋错误图表】 =====================
def plot_result(df):
    plt.rcParams["font.family"] = ["SimHei"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams['figure.dpi'] = 300
    plt.rcParams['font.size'] = 10

    fig, ax = plt.subplots(figsize=(9, 5.5))
    x = df["实际体积分数(%)"]
    y = df["导通概率"]
    # 置信区间误差棒
    err_low = y - df["95%CI下界"]
    err_high = df["95%CI上界"] - y
    err = [err_low, err_high]

    # 标准绘图，线条清晰、标记醒目
    ax.errorbar(x, y, yerr=err, fmt='o-', color='#003366', capsize=7,
                markersize=9, linewidth=2, elinewidth=1.2, label='导通概率±95%置信区间')
    # 阈值辅助线 y=0.9
    ax.axhline(y=0.9, color='#c82423', linestyle='--', linewidth=1.5, label='导通概率90%临界线')

    ax.set_xlabel("介质A体积分数（%）", fontsize=11)
    ax.set_ylabel("微构体导通概率", fontsize=11)
    ax.set_title("问题二 介质A填充体积分数与导通概率关系曲线", fontsize=12, pad=12)
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3, linestyle='-.')
    ax.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig("问题二_体积分数导通概率曲线.png", bbox_inches="tight")
    plt.close()
    print("✅ 标准曲线图已保存：问题二_体积分数导通概率曲线.png")

# ===================== 主程序入口 =====================
if __name__ == "__main__":
    output_list = []
    print("========== 华数杯A题 问题二 蒙特卡洛仿真 ==========")
    print(f"每组仿真次数：{SIM_NUM} | 目标体积分数：{target_vol_pct}\n")

    for frac_pct in target_vol_pct:
        N_int, N_float, V_A, V_box = vol_frac_to_N(frac_pct)
        real_frac = (N_int * V_A / V_box) * 100
        print(f"目标体积分数 {frac_pct:.2f}% | 理论介质数={N_float:.4f}，取整N={N_int}")
        succ_cnt, p, cil, cih = batch_run(N_int)
        row = {
            "目标体积分数(%)": round(frac_pct,2),
            "介质A数量N": N_int,
            "实际体积分数(%)": round(real_frac,4),
            "导通样本数": succ_cnt,
            "总仿真次数": SIM_NUM,
            "导通概率": round(p,4),
            "95%CI下界": round(cil,4),
            "95%CI上界": round(cih,4)
        }
        output_list.append(row)
        print(f"仿真结果：概率={p:.4f}，置信区间[{cil:.4f},{cih:.4f}]\n")

    # 汇总表格输出
    res_df = pd.DataFrame(output_list)
    print("========== 问题二仿真结果汇总表 ==========")
    print(res_df.to_string(index=False))
    # 导出Excel
    res_df.to_excel("问题二_导通概率仿真汇总.xlsx", index=False)
    print("\n✅ 结果表格已导出：问题二_导通概率仿真汇总.xlsx")
    # 绘制标准论文图表
    plot_result(res_df)