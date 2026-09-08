#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2021年国赛A题 问题二：倾斜理想抛物面优化
完整代码：核心计算 + Excel表格输出 + 4张学术风配图
"""

import numpy as np
from scipy.optimize import minimize_scalar
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.patches import Circle

# ===================== 全局绘图设置：数模竞赛学术规范 =====================
rcParams['font.sans-serif'] = ['SimSun', 'Times New Roman']
rcParams['axes.unicode_minus'] = False
rcParams['font.size'] = 11
rcParams['axes.linewidth'] = 0.8
rcParams['xtick.direction'] = 'in'
rcParams['ytick.direction'] = 'in'

# ===================== 1. 基准参数定义 =====================
R = 300.4  # 基准球面半径 (米)
rho_max = 150.0  # 300m照明口径的半径 (米)
R_f = 160.41  # 焦面半径（焦点到球心距离，由问题一确定）(米)
max_travel = 0.6  # 促动器最大行程 (米)

# 天体方位角与仰角（由题目给定，通过D27节点反推验证）
alpha = np.radians(36.795)  # 方位角 (rad)
beta = np.radians(78.169)  # 仰角 (rad)

# 入射方向单位向量（从球心指向天体）
e_s = np.array([
    np.cos(beta) * np.cos(alpha),
    np.cos(beta) * np.sin(alpha),
    np.sin(beta)
])
print(f"入射方向向量 e_s = ({e_s[0]:.6f}, {e_s[1]:.6f}, {e_s[2]:.6f})")
print(f"方位角 α = {np.degrees(alpha):.3f}°, 仰角 β = {np.degrees(beta):.3f}°")

# 焦点P（焦面与碗内一侧的交点）
P = -R_f * e_s
print(f"焦点 P = ({P[0]:.4f}, {P[1]:.4f}, {P[2]:.4f}) m")

# ===================== 2. 读取主索节点数据 =====================
df_nodes = pd.read_excel('附件1(1).xlsx')
node_names = df_nodes['节点编号'].values
X_all = df_nodes[['X坐标（米）', 'Y坐标（米）', 'Z坐标（米）']].values
N_total = len(X_all)
print(f"\n读取主索节点总数：{N_total}")

# ===================== 3. 300m照明区域筛选 =====================
# 节点到对称轴的垂直距离平方 = |X|² - (X·e_s)²
# 照明区条件：垂直距离 ≤ 150m
dot_prod = X_all @ e_s
perp_dist_sq = np.sum(X_all ** 2, axis=1) - dot_prod ** 2
in_illum = perp_dist_sq <= rho_max ** 2
# 只保留碗内节点（dot_prod < 0，即与天体方向相反）
in_illum = in_illum & (dot_prod < 0)

X_illum = X_all[in_illum]
names_illum = node_names[in_illum]
N_illum = len(X_illum)
print(f"300m照明区内节点数：{N_illum}")

# 照明区中心（SC与基准球面碗内交点）
X_center = -R * e_s
print(f"照明区中心坐标 = ({X_center[0]:.4f}, {X_center[1]:.4f}, {X_center[2]:.4f}) m")


# ===================== 4. 径向偏差核心计算 =====================
def calc_radial_deviation_tilt(X, f):
    """
    计算倾斜抛物面下单个节点的径向偏差
    X: 节点坐标 (3,)
    f: 抛物面焦距
    返回: delta_r (径向偏差), rho_perp (到对称轴垂直距离)
    """
    n = X / R  # 径向单位向量（从球心指向节点）
    ne = n @ e_s
    a = 1.0 - ne ** 2  # 二次方程r²系数

    # 退化情况：节点在对称轴上
    if a < 1e-12:
        r_parabola = R_f + f  # 顶点到球心距离
        delta_r = r_parabola - R
        rho_perp = 0.0
        return delta_r, rho_perp

    nP = n @ P
    b = -2.0 * nP - 2.0 * (R_f + 2.0 * f) * ne
    c = -4.0 * f * (R_f + f)

    discriminant = b ** 2 - 4.0 * a * c
    r_parabola = (-b + np.sqrt(discriminant)) / (2.0 * a)
    delta_r = r_parabola - R

    # 到对称轴的垂直距离
    rho_perp = np.sqrt(np.sum(X ** 2) - (X @ e_s) ** 2)
    return delta_r, rho_perp


def calc_all_deviations(f, X_arr):
    """批量计算所有节点的径向偏差"""
    deltas = np.zeros(len(X_arr))
    rhos = np.zeros(len(X_arr))
    for i, X in enumerate(X_arr):
        deltas[i], rhos[i] = calc_radial_deviation_tilt(X, f)
    return deltas, rhos


# ===================== 5. 焦距优化模型 =====================
def objective_sse(f):
    """目标函数：照明区内所有节点径向偏差平方和"""
    deltas, _ = calc_all_deviations(f, X_illum)
    return np.sum(deltas ** 2)


# 一维有界优化
opt_result = minimize_scalar(
    objective_sse,
    bounds=(135, 145),
    method='bounded'
)

f_opt = opt_result.x
V_opt = P - f_opt * e_s  # 顶点坐标
V_dist = np.linalg.norm(V_opt)  # 顶点到原点距离
inner_shift = R - V_dist  # 内移量

# 计算最优解下所有节点偏差
deltas_opt, rhos_opt = calc_all_deviations(f_opt, X_illum)
actuator_d = -deltas_opt  # 促动器伸缩量（与偏差反向）
max_abs_dev = np.max(np.abs(deltas_opt))
max_abs_act = np.max(np.abs(actuator_d))

print("\n" + "=" * 60)
print("          问题二 优化结果")
print("=" * 60)
print(f"  最优焦距  f*       = {f_opt:.6f} m")
print(f"  顶点坐标 V*        = ({V_opt[0]:.4f}, {V_opt[1]:.4f}, {V_opt[2]:.4f}) m")
print(f"  顶点到原点距离     = {V_dist:.6f} m")
print(f"  较基准球面内移     = {inner_shift:.6f} m")
print(f"  偏差平方和(SSE)    = {opt_result.fun:.6f} m²")
print(f"  RMS偏差            = {np.sqrt(np.mean(deltas_opt ** 2)):.6f} m")
print(f"  最大绝对径向偏差   = {max_abs_dev:.6f} m")
print(f"  最大促动器伸缩量   = {max_abs_act:.6f} m")
print(f"  行程约束(≤0.6m)    = {'满足' if max_abs_act <= max_travel else '不满足'}")
print("=" * 60)

# 抛物面方程（向量形式）
print(f"\n理想抛物面方程（向量形式）：")
print(f"  |X - V|² - ((X-V)·e_s)² = 4f × (X-V)·e_s")
print(f"  其中 f = {f_opt:.4f} m, V = ({V_opt[0]:.4f}, {V_opt[1]:.4f}, {V_opt[2]:.4f}) m")

# ===================== 6. Excel结果表格输出 =====================

# 6.1 分桶统计表（对应文档表6-1）
bins = [0, 30, 60, 90, 120, 150, 200]
bin_labels = ['0-30m', '30-60m', '60-90m', '90-120m', '120-150m', '>150m(外)']
bucket_stats = []
for i in range(len(bins) - 1):
    mask = (rhos_opt >= bins[i]) & (rhos_opt < bins[i + 1])
    if np.sum(mask) > 0:
        d_mean = np.mean(deltas_opt[mask])
        d_max = np.max(deltas_opt[mask])
        d_min = np.min(deltas_opt[mask])
        act_mean = np.mean(actuator_d[mask])
        act_max = np.max(actuator_d[mask])
        act_min = np.min(actuator_d[mask])
        bucket_stats.append([
            bin_labels[i], int(np.sum(mask)),
            round(d_mean, 4), round(d_max, 4), round(d_min, 4),
            round(act_mean, 4), round(act_max, 4), round(act_min, 4)
        ])

df_bucket = pd.DataFrame(bucket_stats, columns=[
    '到对称轴距离区间', '节点数',
    '径向偏差均值(m)', '径向偏差最大(m)', '径向偏差最小(m)',
    '促动器伸缩量均值(m)', '促动器伸缩量最大(m)', '促动器伸缩量最小(m)'
])

# 6.2 照明区节点计算结果（前50个展示，可扩展至全部）
node_results = []
for i in range(min(N_illum, 200)):
    X = X_illum[i]
    delta_r, rho_p = calc_radial_deviation_tilt(X, f_opt)
    act_d = -delta_r
    node_results.append([
        names_illum[i],
        round(X[0], 4), round(X[1], 4), round(X[2], 4),
        round(rho_p, 4), round(delta_r, 4), round(act_d, 4)
    ])

df_node_result = pd.DataFrame(node_results, columns=[
    '节点编号', 'X坐标(m)', 'Y坐标(m)', 'Z坐标(m)',
    '到对称轴距离(m)', '径向偏差δr(m)', '促动器伸缩量d(m)'
])

# 6.3 优化参数汇总表
df_summary = pd.DataFrame([
    ['最优焦距 f* (m)', round(f_opt, 6)],
    ['顶点X坐标 (m)', round(V_opt[0], 4)],
    ['顶点Y坐标 (m)', round(V_opt[1], 4)],
    ['顶点Z坐标 (m)', round(V_opt[2], 4)],
    ['顶点到原点距离 (m)', round(V_dist, 6)],
    ['较基准球面内移量 (m)', round(inner_shift, 6)],
    ['焦点X坐标 (m)', round(P[0], 4)],
    ['焦点Y坐标 (m)', round(P[1], 4)],
    ['焦点Z坐标 (m)', round(P[2], 4)],
    ['照明区内节点数', N_illum],
    ['RMS径向偏差 (m)', round(np.sqrt(np.mean(deltas_opt ** 2)), 6)],
    ['最大绝对径向偏差 (m)', round(max_abs_dev, 6)],
    ['最大促动器伸缩量 (m)', round(max_abs_act, 6)],
    ['行程约束(≤0.6m)', '满足' if max_abs_act <= max_travel else '不满足'],
], columns=['参数名称', '数值'])

# 保存Excel
with pd.ExcelWriter('问题二_倾斜抛物面优化结果.xlsx') as writer:
    df_summary.to_excel(writer, sheet_name='优化参数汇总', index=False)
    df_bucket.to_excel(writer, sheet_name='分桶统计', index=False)
    df_node_result.to_excel(writer, sheet_name='照明区节点结果', index=False)

print("\n✅ Excel结果表格已保存：问题二_倾斜抛物面优化结果.xlsx")
print("   包含工作表：① 优化参数汇总  ② 分桶统计  ③ 照明区节点结果")

# ===================== 7. 4张学术风结果图 =====================

# ---------- 图1：促动器伸缩量随到对称轴距离的分布 ----------
fig1, ax1 = plt.subplots(figsize=(7, 4.5))
# 按到对称轴距离排序
sort_idx = np.argsort(rhos_opt)
rho_sorted = rhos_opt[sort_idx]
delta_sorted = deltas_opt[sort_idx]
act_sorted = actuator_d[sort_idx]

ax1.scatter(rho_sorted, delta_sorted, s=8, c='k', marker='o', alpha=0.6, label='径向偏差 $\\delta_r$')
ax1.scatter(rho_sorted, act_sorted, s=8, c='k', marker='s', alpha=0.4, label='促动器伸缩量 $d$')

ax1.axhline(0, color='gray', linestyle=':', linewidth=0.8)
ax1.axhline(max_travel, color='r', linestyle=':', linewidth=0.8, label='行程约束 $\\pm 0.6$m')
ax1.axhline(-max_travel, color='r', linestyle=':', linewidth=0.8)
ax1.axvline(rho_max, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)

ax1.set_xlabel('到对称轴垂直距离 $\\rho_\\perp$ / m', fontsize=12)
ax1.set_ylabel('偏差量 / m', fontsize=12)
ax1.set_title('图1 照明区内径向偏差与促动器伸缩量分布', fontsize=12, pad=10)
ax1.legend(fontsize=9, frameon=False, loc='upper left')
ax1.grid(True, linestyle='--', alpha=0.3)
ax1.set_xlim(0, rho_max + 5)

plt.tight_layout()
plt.savefig('问题二_图1_偏差与伸缩量分布.png', dpi=300, bbox_inches='tight')
plt.close()

# ---------- 图2：照明区域在基准球面上的投影分布 ----------
fig2, ax2 = plt.subplots(figsize=(6.5, 5.5))
# 投影到垂直于e_s的平面：构造两个正交基向量
if abs(e_s[2]) < 0.9:
    u = np.cross(e_s, np.array([0, 0, 1]))
else:
    u = np.cross(e_s, np.array([1, 0, 0]))
u = u / np.linalg.norm(u)
v = np.cross(e_s, u)

# 所有节点投影
proj_u_all = X_all @ u
proj_v_all = X_all @ v
# 照明区节点投影
proj_u_ill = X_illum @ u
proj_v_ill = X_illum @ v

ax2.scatter(proj_u_all, proj_v_all, s=2, c='lightgray', marker='.', label='全部节点')
ax2.scatter(proj_u_ill, proj_v_ill, s=10, c='k', marker='o', alpha=0.7, label='照明区内节点')
# 画300m口径圆
circle = Circle((0, 0), rho_max, color='k', fill=False, linewidth=1.2, linestyle='--', label='300m口径边界')
ax2.add_artist(circle)
ax2.scatter([0], [0], s=40, c='k', marker='*', zorder=5, label='照明区中心')

ax2.set_xlabel('$u$ (垂直对称轴方向1) / m', fontsize=11)
ax2.set_ylabel('$v$ (垂直对称轴方向2) / m', fontsize=11)
ax2.set_title('图2 300m照明区域节点投影分布', fontsize=12, pad=10)
ax2.legend(fontsize=9, frameon=False, loc='upper right')
ax2.set_aspect('equal')
ax2.grid(True, linestyle='--', alpha=0.3)
ax2.set_xlim(-170, 170)
ax2.set_ylim(-170, 170)

plt.tight_layout()
plt.savefig('问题二_图2_照明区域投影分布.png', dpi=300, bbox_inches='tight')
plt.close()

# ---------- 图3：焦距优化性能曲线 ----------
fig3, ax3 = plt.subplots(figsize=(7, 4.5))
f_scan = np.linspace(135, 145, 80)
sse_scan = []
max_scan = []
for f in f_scan:
    deltas, _ = calc_all_deviations(f, X_illum)
    sse_scan.append(np.sum(deltas ** 2))
    max_scan.append(np.max(np.abs(deltas)))

ax3.plot(f_scan, sse_scan, 'k-', linewidth=1.5, label='偏差平方和 (SSE)')
ax3_twin = ax3.twinx()
ax3_twin.plot(f_scan, max_scan, 'k--', linewidth=1.2, label='最大绝对偏差')
ax3_twin.axhline(max_travel, color='r', linestyle=':', linewidth=0.8, label='行程上限 0.6m')

ax3.scatter(f_opt, opt_result.fun, s=40, c='k', zorder=5)
ax3.text(f_opt + 0.15, opt_result.fun, f'最优解\n$f={f_opt:.2f}$m', fontsize=9, va='bottom')

ax3.set_xlabel('抛物面焦距 $f$ / m', fontsize=12)
ax3.set_ylabel('偏差平方和 / m²', fontsize=12)
ax3_twin.set_ylabel('最大绝对偏差 / m', fontsize=12)
ax3.set_title('图3 不同焦距下的偏差性能与约束边界', fontsize=12, pad=10)

lines1, labels1 = ax3.get_legend_handles_labels()
lines2, labels2 = ax3_twin.get_legend_handles_labels()
ax3.legend(lines1 + lines2, labels1 + labels2, fontsize=9, frameon=False, loc='upper center')
ax3.grid(True, linestyle='--', alpha=0.3)

plt.tight_layout()
plt.savefig('问题二_图3_焦距优化性能曲线.png', dpi=300, bbox_inches='tight')
plt.close()

# ---------- 图4：子午截面内基准球面与倾斜抛物面对比 ----------
fig4, ax4 = plt.subplots(figsize=(7, 5))
# 在e_s-z轴构成的子午面内绘制
# 以e_s方向为横轴(s)，垂直方向为纵轴(t)
# 基准球面：s² + t² = R²
s_vals = np.linspace(-R, R, 500)
t_sphere = np.sqrt(np.maximum(R ** 2 - s_vals ** 2, 0))

# 倾斜抛物面：顶点在s = -(R_f+f), t=0，对称轴为s轴
# 方程：t² = 4f(s + (R_f+f))  （开口向s正方向）
s_parab = np.linspace(-(R_f + f_opt), R, 500)
t_parab = np.sqrt(np.maximum(4 * f_opt * (s_parab + (R_f + f_opt)), 0))

ax4.plot(s_vals, t_sphere, 'k-', linewidth=1.2, label='基准球面（上半）')
ax4.plot(s_vals, -t_sphere, 'k-', linewidth=1.2)
ax4.plot(s_parab, t_parab, 'k--', linewidth=1.5, label='理想抛物面')
ax4.plot(s_parab, -t_parab, 'k--', linewidth=1.5)

# 标注关键点
ax4.scatter(0, 0, s=30, c='k', marker='o', zorder=5)
ax4.text(5, 8, '球心 $O$', fontsize=10)
ax4.scatter(-R_f, 0, s=35, c='k', marker='*', zorder=5)
ax4.text(-R_f - 30, 8, '焦点 $P$', fontsize=10)
ax4.scatter(-(R_f + f_opt), 0, s=30, c='k', marker='s', zorder=5)
ax4.text(-(R_f + f_opt) - 10, -20, '抛物面顶点', fontsize=9)

# 照明区边界（到对称轴距离150m）
ax4.axhline(150, color='gray', linestyle=':', linewidth=0.8, alpha=0.7)
ax4.axhline(-150, color='gray', linestyle=':', linewidth=0.8, alpha=0.7)
ax4.text(-280, 155, '300m口径边界', fontsize=8)

ax4.set_xlabel('沿对称轴方向 $s$ / m', fontsize=12)
ax4.set_ylabel('垂直对称轴方向 $t$ / m', fontsize=12)
ax4.set_title('图4 子午截面内基准球面与倾斜抛物面对比', fontsize=12, pad=10)
ax4.legend(fontsize=10, frameon=False, loc='upper right')
ax4.set_aspect('equal')
ax4.grid(True, linestyle='--', alpha=0.3)
ax4.set_xlim(-320, 50)
ax4.set_ylim(-180, 180)

plt.tight_layout()
plt.savefig('问题二_图4_球面与倾斜抛物面截面对比.png', dpi=300, bbox_inches='tight')
plt.close()

print("\n✅ 4张竞赛级配图已生成：")
print("   1. 问题二_图1_偏差与伸缩量分布.png")
print("   2. 问题二_图2_照明区域投影分布.png")
print("   3. 问题二_图3_焦距优化性能曲线.png")
print("   4. 问题二_图4_球面与倾斜抛物面截面对比.png")
print("   所有图片分辨率300DPI，黑白风格适配论文印刷。")
print("\n全部计算完成！")
