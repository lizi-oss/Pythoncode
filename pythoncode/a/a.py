import numpy as np
from scipy.optimize import minimize_scalar
from scipy.integrate import quad
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import rcParams

# ===================== 全局绘图设置：符合数模竞赛学术规范 =====================
rcParams['font.sans-serif'] = ['SimSun', 'Times New Roman']  # 中文宋体+英文Times New Roman
rcParams['axes.unicode_minus'] = False  # 解决负号显示异常
rcParams['font.size'] = 11
rcParams['axes.linewidth'] = 0.8
rcParams['xtick.direction'] = 'in'
rcParams['ytick.direction'] = 'in'
rcParams['figure.dpi'] = 100

# ===================== 1. 基准参数定义 =====================
R = 300.4  # 基准球面半径 (米)
rho_max = 150.0  # 300m有效口径的半径 (米)
z_f = -160.41  # 焦点z坐标（由题目焦径比0.467推导）
max_travel = 0.6  # 促动器最大行程 (米)


# ===================== 2. 径向偏差核心计算 =====================
def calc_radial_deviation(rho, f):
    """
    计算指定径向距离处的球面-抛物面径向偏差
    参数:
        rho: 节点到z轴的径向距离 (米)
        f: 抛物面焦距 (米)
    返回:
        delta_r: 径向偏差 (米)，正表示抛物面在基准球面外侧（远离球心）
    """
    z_v = z_f - f  # 抛物面顶点z坐标

    sin_theta = rho / R
    cos_theta = -np.sqrt(1 - sin_theta ** 2)

    # 构建径向射线与抛物面交点的二次方程
    a = sin_theta ** 2
    b = -4 * f * cos_theta
    c = 4 * f * z_v

    discriminant = b ** 2 - 4 * a * c
    if discriminant < 0:
        return np.nan

    r_parabola = (-b + np.sqrt(discriminant)) / (2 * a)
    delta_r = r_parabola - R
    return delta_r


# ===================== 3. 优化目标与约束 =====================
def objective_rms(f):
    """目标函数：300m口径内径向偏差的均方根(RMS)"""
    integrand = lambda rho: (calc_radial_deviation(rho, f) ** 2) * rho
    integral, _ = quad(integrand, 0, rho_max)
    rms = np.sqrt(2 * integral / (rho_max ** 2))
    return rms


def get_max_deviation(f):
    """计算口径内最大绝对径向偏差"""
    rho_samples = np.linspace(0, rho_max, 2000)
    deltas = np.array([calc_radial_deviation(rho, f) for rho in rho_samples])
    return np.max(np.abs(deltas))


# ===================== 4. 一维优化求解 =====================
opt_result = minimize_scalar(
    objective_rms,
    bounds=(135, 145),
    method='bounded'
)

f_opt = opt_result.x
z_v_opt = z_f - f_opt
max_dev = get_max_deviation(f_opt)
rms_opt = opt_result.fun

# 控制台输出优化结果
print("=" * 55)
print("主动反射面优化结果")
print(f"最优焦距 f = {f_opt:.4f} m")
print(f"抛物面顶点 z坐标 = {z_v_opt:.4f} m")
print(f"口径内最小RMS偏差 = {rms_opt:.4f} m")
print(f"口径内最大径向偏差 = {max_dev:.4f} m")
print(f"促动器行程约束校验(≤0.6m): {'满足' if max_dev <= max_travel else '不满足'}")
print("=" * 55)

# ===================== 5. 结果表格输出（Excel文件） =====================
# 5.1 典型半径偏差表（对应论文正文中的结果表）
rho_list = [0, 30, 60, 90, 120, 150]
table_typical = []
for rho in rho_list:
    z_sphere = -np.sqrt(R ** 2 - rho ** 2)
    delta_r = calc_radial_deviation(rho, f_opt)
    actuator_d = -delta_r
    z_parabola = -(R + delta_r) * np.sqrt(1 - (rho / R) ** 2)  # 抛物面交点z坐标
    table_typical.append([
        round(rho, 0),
        round(z_sphere, 4),
        round(z_parabola, 4),
        round(delta_r, 4),
        round(actuator_d, 4)
    ])

df_typical = pd.DataFrame(
    table_typical,
    columns=['径向距离ρ(m)', '基准面Z坐标(m)', '抛物面Z坐标(m)', '径向偏差δr(m)', '促动器伸缩量d(m)']
)

# 5.2 主索节点批量计算示例（可扩展至附件1全部节点）
# 此处选取附件1前10个节点演示，实际使用时可通过pd.read_excel读取全量数据
nodes_demo = [
    ["A0", 0, 0, -300.4],
    ["B1", 6.1078, 8.407, -300.2202],
    ["C1", 9.8827, -3.211, -300.2202],
    ["D1", 0, -10.391, -300.2202],
    ["E1", -9.8827, -3.211, -300.2202],
    ["A1", -6.1078, 8.407, -300.2202],
    ["A3", 0, 16.818, -299.9289],
    ["B2", 12.2084, 16.804, -299.6811],
    ["B3", 15.9942, 5.197, -299.9289],
    ["C2", 19.7536, -6.418, -299.6811]
]

node_results = []
for name, x, y, z in nodes_demo:
    rho = np.sqrt(x ** 2 + y ** 2)
    if rho <= rho_max:
        delta_r = calc_radial_deviation(rho, f_opt)
        actuator_d = -delta_r
        node_results.append([name, round(x, 4), round(y, 4), round(z, 4), round(delta_r, 4), round(actuator_d, 4)])
    else:
        node_results.append([name, x, y, z, "超出有效口径", "超出有效口径"])

df_nodes = pd.DataFrame(
    node_results,
    columns=['节点编号', 'X坐标(m)', 'Y坐标(m)', 'Z坐标(m)', '径向偏差δr(m)', '促动器伸缩量d(m)']
)

# 保存为Excel文件，双工作表
with pd.ExcelWriter('FAST主动反射面调整结果.xlsx') as writer:
    df_typical.to_excel(writer, sheet_name='典型半径偏差表', index=False)
    df_nodes.to_excel(writer, sheet_name='节点计算结果', index=False)

print("\n✅ 结果表格已保存：FAST主动反射面调整结果.xlsx")
print("   包含工作表：① 典型半径偏差表  ② 节点计算结果")

# ===================== 6. 4张学术风结果图绘制 =====================

# ---------- 图1：径向偏差与促动器伸缩量分布（核心结果图） ----------
fig1, ax1 = plt.subplots(figsize=(7, 4.5))
rho_plot = np.linspace(0, rho_max, 300)
delta_plot = np.array([calc_radial_deviation(r, f_opt) for r in rho_plot])
actuator_plot = -delta_plot

ax1.plot(rho_plot, delta_plot, 'k-', linewidth=1.5, label='径向偏差 $\\delta_r$')
ax1.plot(rho_plot, actuator_plot, 'k--', linewidth=1.2, label='促动器伸缩量 $d$')

ax1.axhline(0, color='gray', linestyle=':', linewidth=0.8)
ax1.axhline(max_travel, color='r', linestyle=':', linewidth=0.8, label='行程约束 $\\pm 0.6\\mathrm{m}$')
ax1.axhline(-max_travel, color='r', linestyle=':', linewidth=0.8)

ax1.set_xlabel('径向距离 $\\rho$ / m', fontsize=12)
ax1.set_ylabel('偏差量 / m', fontsize=12)
ax1.set_title('图1 300m口径内径向偏差与促动器伸缩量分布', fontsize=12, pad=10)
ax1.legend(fontsize=10, frameon=False)
ax1.grid(True, linestyle='--', alpha=0.3)
ax1.set_xlim(0, rho_max)

plt.tight_layout()
plt.savefig('图1 径向偏差与伸缩量分布.png', dpi=300, bbox_inches='tight')
plt.close()

# ---------- 图2：基准球面与抛物面子午截面对比（物理示意图） ----------
fig2, ax2 = plt.subplots(figsize=(7, 5))
x_sec = np.linspace(-rho_max, rho_max, 500)
z_sphere_sec = -np.sqrt(R ** 2 - x_sec ** 2)  # 基准球面截面
z_parabola_sec = z_v_opt + x_sec ** 2 / (4 * f_opt)  # 抛物面截面

ax2.plot(x_sec, z_sphere_sec, 'k-', linewidth=1.2, label='基准球面')
ax2.plot(x_sec, z_parabola_sec, 'k--', linewidth=1.5, label='理想抛物面')

# 标注关键几何要素
ax2.scatter(0, 0, s=30, c='k', marker='o')
ax2.text(6, 3, '球心 $O$', fontsize=10)
ax2.scatter(0, z_f, s=35, c='k', marker='*')
ax2.text(6, z_f, '焦点 $P$', fontsize=10)
ax2.scatter(0, z_v_opt, s=30, c='k', marker='s')
ax2.text(6, z_v_opt, '抛物面顶点', fontsize=9)

# 标注口径边界
ax2.vlines([-rho_max, rho_max], ymin=-R - 2, ymax=0, linestyles=':', colors='gray', linewidth=0.8)
ax2.text(rho_max + 3, -R / 2, '300m口径边界', fontsize=9, rotation=90, va='center')

ax2.set_xlabel('$x$ / m', fontsize=12)
ax2.set_ylabel('$z$ / m', fontsize=12)
ax2.set_title('图2 基准球面与理想抛物面子午截面对比', fontsize=12, pad=10)
ax2.legend(fontsize=10, frameon=False, loc='upper right')
ax2.set_aspect('equal', adjustable='box')
ax2.grid(True, linestyle='--', alpha=0.3)

plt.tight_layout()
plt.savefig('图2 球面与抛物面截面对比.png', dpi=300, bbox_inches='tight')
plt.close()

# ---------- 图3：焦距优化性能曲线（优化过程展示） ----------
fig3, ax3 = plt.subplots(figsize=(7, 4.5))
f_scan = np.linspace(135, 145, 100)
rms_scan = [objective_rms(f) for f in f_scan]
max_scan = [get_max_deviation(f) for f in f_scan]

ax3.plot(f_scan, rms_scan, 'k-', linewidth=1.5, label='RMS偏差')
ax3.plot(f_scan, max_scan, 'k--', linewidth=1.2, label='最大绝对偏差')
ax3.axhline(max_travel, color='r', linestyle=':', linewidth=0.8, label='行程上限 0.6m')

# 标注最优解
ax3.scatter(f_opt, rms_opt, s=40, c='k', zorder=5)
ax3.text(f_opt + 0.15, rms_opt, f'最优解\n$f={f_opt:.2f}\\mathrm{{m}}$', fontsize=9, va='bottom')

ax3.set_xlabel('抛物面焦距 $f$ / m', fontsize=12)
ax3.set_ylabel('偏差量 / m', fontsize=12)
ax3.set_title('图3 不同焦距下的偏差性能与约束边界', fontsize=12, pad=10)
ax3.legend(fontsize=10, frameon=False)
ax3.grid(True, linestyle='--', alpha=0.3)

plt.tight_layout()
plt.savefig('图3 焦距优化性能曲线.png', dpi=300, bbox_inches='tight')
plt.close()

# ---------- 图4：径向偏差等高线分布（平面分布展示） ----------
fig4, ax4 = plt.subplots(figsize=(6, 5))
xx, yy = np.meshgrid(np.linspace(-rho_max, rho_max, 200),
                     np.linspace(-rho_max, rho_max, 200))
rho_grid = np.sqrt(xx ** 2 + yy ** 2)
delta_grid = np.where(rho_grid <= rho_max,
                      np.vectorize(calc_radial_deviation)(rho_grid, f_opt),
                      np.nan)

# 灰度填充等高线（适配黑白印刷）
contour = ax4.contourf(xx, yy, delta_grid, levels=20, cmap='Greys')
cs = ax4.contour(xx, yy, delta_grid, levels=8, colors='k', linewidths=0.5)
ax4.clabel(cs, inline=True, fontsize=8, fmt='%.3f')

# 绘制口径边界
circle = plt.Circle((0, 0), rho_max, color='k', fill=False, linewidth=1)
ax4.add_artist(circle)

ax4.set_xlabel('$x$ / m', fontsize=12)
ax4.set_ylabel('$y$ / m', fontsize=12)
ax4.set_title('图4 300m口径内径向偏差等高线分布', fontsize=12, pad=10)
ax4.set_aspect('equal')

cbar = plt.colorbar(contour, ax=ax4)
cbar.set_label('径向偏差 $\\delta_r$ / m', fontsize=10)

plt.tight_layout()
plt.savefig('图4 径向偏差等高线分布.png', dpi=300, bbox_inches='tight')
plt.close()

print("\n✅ 4张竞赛级配图已生成保存：")
print("   1. 图1 径向偏差与伸缩量分布.png（核心结果曲线）")
print("   2. 图2 球面与抛物面截面对比.png（几何原理示意图）")
print("   3. 图3 焦距优化性能曲线.png（优化过程与约束验证）")
print("   4. 图4 径向偏差等高线分布.png（全口径平面分布）")
print("   所有图片分辨率300DPI，黑白风格适配论文印刷。")