import numpy as np
from scipy.optimize import bisect, fsolve
import matplotlib.pyplot as plt

# ===================== 国赛绘图全局配置 =====================
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['axes.linewidth'] = 1.0
plt.rcParams['grid.linewidth'] = 0.6
plt.rcParams['legend.frameon'] = True
plt.rcParams['legend.framealpha'] = 0.9
plt.rcParams['figure.dpi'] = 300
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['axes.labelsize'] = 10
plt.rcParams['legend.fontsize'] = 9
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9

colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#17becf']

# ===================== 原题物理参数 =====================
p = 0.55
b = p / (2 * np.pi)
v_head = 1.0
L_head = 2.86
L_body = 1.65
theta_0_initial = 32 * np.pi
N_handles = 224
EPS = 1e-8

# 极角转直角坐标
def spiral_coords(theta):
    r = b * theta
    return r * np.cos(theta), r * np.sin(theta)

# 弧长解析原函数
def arc_length_integral(theta):
    return (b / 2) * (theta * np.sqrt(theta**2 + 1) + np.log(theta + np.sqrt(theta**2 + 1)))

# 二分反解t时刻龙头极角
def get_theta_head(t):
    if t <= EPS:
        return theta_0_initial
    S0 = arc_length_integral(theta_0_initial)
    def target(theta):
        return (S0 - arc_length_integral(theta)) - t
    return bisect(target, 0.1, theta_0_initial, xtol=EPS)

# 已知内侧点，向外求解外侧铰接点（距离约束）
def solve_next_theta(theta_k, L):
    x_k, y_k = spiral_coords(theta_k)
    def dist_target(theta_next):
        x_n, y_n = spiral_coords(theta_next)
        return np.sqrt((x_k - x_n)**2 + (y_k - y_n)**2) - L
    lower = theta_k + EPS
    upper = theta_k + 12.0
    try:
        sol = fsolve(dist_target, theta_k + 0.3, xtol=EPS)[0]
        if lower < sol < upper and abs(dist_target(sol)) < 1e-6:
            return sol
    except:
        pass
    thetas = np.linspace(lower, upper, 3000)
    vals = np.array([dist_target(th) for th in thetas])
    for i in range(len(vals)-1):
        if vals[i] * vals[i+1] < 0:
            return bisect(dist_target, thetas[i], thetas[i+1], xtol=1e-8)
    idx_min = np.argmin(np.abs(vals))
    if abs(vals[idx_min]) < 1e-6:
        return thetas[idx_min]
    raise RuntimeError(f"无解 theta_k={theta_k:.6f}, L={L}")

# 单时刻求解全部把手坐标+解析速度
def compute_all_handles(t):
    theta_handles = np.zeros(N_handles)
    theta_handles[0] = get_theta_head(t)
    for k in range(N_handles - 1):
        L = L_head if k == 0 else L_body
        theta_handles[k+1] = solve_next_theta(theta_handles[k], L)
    coords = np.array([spiral_coords(th) for th in theta_handles])
    th0 = theta_handles[0]
    dtheta_dt = v_head / (b * np.sqrt(th0**2 + 1))
    speeds = np.array([b * np.sqrt(th**2 + 1) * dtheta_dt for th in theta_handles])
    return coords, speeds

# ===================== 主计算 0~300s全时刻 =====================
print("正在计算 0~300s 全部时刻数据……")
time_steps = np.arange(0, 301, 1)
all_results = []
for t in time_steps:
    coords, speeds = compute_all_handles(t)
    all_results.append([coords, speeds])
    if t % 50 == 0:
        print(f"  完成 t = {t} s")

# 自检
x0, y0 = all_results[0][0][0]
v0 = all_results[0][1][0]
print(f"\n【自检】t=0 龙头坐标 x={x0:.6f}, y={y0:.6f}")
print(f"       龙头速度 v={v0:.6f} m/s")
print("全部计算完成！\n")

# ===================== 绘图模块 =====================
target_times = [0, 60, 120, 180, 240, 300]
target_indices = [0, 1, 51, 101, 151, 201, 223]
label_names = ['龙头', '第1节龙身', '第51节龙身', '第101节龙身',
               '第151节龙身', '第201节龙身', '龙尾（后）']

# 图1：多时刻盘龙叠加图
print("生成图1：多时刻盘龙叠加图 dragon_all.png")
fig1, ax1 = plt.subplots(figsize=(10, 10))
theta_plot = np.linspace(0.1, theta_0_initial + 20, 6000)
x_plot, y_plot = spiral_coords(theta_plot)
ax1.plot(x_plot, y_plot, 'k-', lw=0.8, alpha=0.3, label='基准阿基米德螺线')
for idx, t in enumerate(target_times):
    coords, _ = all_results[t]
    c = colors[idx]
    ax1.plot(coords[:, 0], coords[:, 1], color=c, lw=1.5, alpha=0.85, label=f't={t} s')
    ax1.plot(coords[0,0], coords[0,1], 'o', color=c, ms=6)
    ax1.plot(coords[-1,0], coords[-1,1], '^', color=c, ms=6)
ax1.set_aspect('equal')
ax1.set_xlabel('X 坐标 / m')
ax1.set_ylabel('Y 坐标 / m')
ax1.set_title('图1 板凳龙盘入过程不同时刻空间形态对比')
ax1.grid(True, linestyle=':', alpha=0.6)
ax1.legend(loc='upper right')
plt.tight_layout()
plt.savefig('dragon_all.png', dpi=300)
plt.close()

# 图2：关键把手速度时序曲线
print("生成图2：速度时序曲线 speed_curve.png")
fig2, ax2 = plt.subplots(figsize=(9,6))
for i, idx in enumerate(target_indices):
    v_series = [all_results[t][1][idx] for t in time_steps]
    ax2.plot(time_steps, v_series, color=colors[i], lw=1.4, label=label_names[i])
ax2.set_xlabel('时间 t / s')
ax2.set_ylabel('切向速度 v / (m/s)')
ax2.set_title('图2 各关键把手切向速度随时间变化曲线')
ax2.grid(True, linestyle='--', alpha=0.5)
ax2.legend()
plt.tight_layout()
plt.savefig('speed_curve.png', dpi=300)
plt.close()

# 图3：单独绘制 t=300s 极限盘入位置
print("生成图3：300s极限位置放大图 dragon_300_limit.png")
fig3, ax3 = plt.subplots(figsize=(9, 9))
ax3.plot(x_plot, y_plot, 'k-', lw=0.8, alpha=0.3, label='基准螺线')
coords_300, speeds_300 = all_results[300]
ax3.plot(coords_300[:,0], coords_300[:,1], color='#d62728', lw=2, alpha=0.9, label='t=300s 极限盘入位置')
ax3.scatter(coords_300[:,0], coords_300[:,1], color='#d62728', s=8, alpha=0.8)
ax3.plot(coords_300[0,0], coords_300[0,1], 'o', color='red', ms=8, label='龙头')
ax3.plot(coords_300[-1,0], coords_300[-1,1], '^', color='darkred', ms=8, label='龙尾')
ax3.set_aspect('equal')
ax3.set_xlabel('X 坐标 / m')
ax3.set_ylabel('Y 坐标 / m')
ax3.set_title('图3 t=300s板凳龙极限盘入空间位置')
ax3.grid(False)
ax3.legend(loc='upper right')
plt.tight_layout()
plt.savefig('dragon_300_limit.png', dpi=300)
plt.close()

# 图4：【重点】全程龙头轨迹图，只显示所有时刻龙头位置，无龙身、无时间标注
print("生成全程龙头轨迹总图 head_trace_all.png")
fig_head, axh = plt.subplots(figsize=(10, 10))
axh.plot(x_plot, y_plot, 'k-', lw=0.8, alpha=0.3)

head_x = []
head_y = []
for t in range(0, 301):
    coords_t, _ = all_results[t]
    hx = float(coords_t[0, 0])
    hy = float(coords_t[0, 1])
    head_x.append(hx)
    head_y.append(hy)

axh.scatter(head_x, head_y, color='#d62728', s=3, alpha=0.6)
axh.plot(head_x, head_y, color='#d62728', lw=1, alpha=0.8)

axh.set_aspect('equal')
axh.set_xlabel('X 坐标 / m')
axh.set_ylabel('Y 坐标 / m')
axh.set_title('0~300秒龙头全程运动轨迹')
axh.grid(False)
plt.tight_layout()
plt.savefig('head_trace_all.png', dpi=300)
plt.close()

print("✅ 四张图片全部保存完成！")
print("输出文件清单：")
print("1. dragon_all.png")
print("2. speed_curve.png")
print("3. dragon_300_limit.png")
print("4. head_trace_all.png【龙头轨迹图】")