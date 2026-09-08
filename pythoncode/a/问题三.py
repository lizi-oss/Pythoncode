#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FAST主动反射面优化 - 问题三：光线追踪接收比计算
使用附件3实际面板连接关系（4300块三角形反射面板）
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.patches import Circle

rcParams['font.sans-serif'] = ['SimSun', 'Times New Roman']
rcParams['axes.unicode_minus'] = False
rcParams['font.size'] = 11
rcParams['axes.linewidth'] = 0.8
rcParams['xtick.direction'] = 'in'
rcParams['ytick.direction'] = 'in'

# ===================== 1. 参数设置 =====================
R = 300.4           # 基准球面半径
R_f = 160.41        # 焦面半径（球心到馈源舱中心）
rho_max = 150.0     # 照明区半径（300m口径）
feed_radius = 0.5   # 馈源有效区域半径（直径1m）
alpha = np.radians(36.795)
beta = np.radians(78.169)
u = np.array([np.cos(beta)*np.cos(alpha), np.cos(beta)*np.sin(alpha), np.sin(beta)])
P = -R_f * u
f_opt = 140.427510  # 问题二最优焦距

print(f"对称轴 u = ({u[0]:.6f}, {u[1]:.6f}, {u[2]:.6f})")
print(f"焦点 P = ({P[0]:.4f}, {P[1]:.4f}, {P[2]:.4f}) m")

# ===================== 2. 读取主索节点 =====================
df1 = pd.read_excel('附件1(1).xlsx')
node_names = df1['节点编号'].values
X_node = df1[['X坐标（米）', 'Y坐标（米）', 'Z坐标（米）']].values
N_total = len(X_node)
name_to_idx = {name: i for i, name in enumerate(node_names)}

# ===================== 3. 读取附件3反射面板 =====================
df3 = pd.read_csv('附件3.csv', encoding='gbk')
panels_all = []
for _, row in df3.iterrows():
    n1, n2, n3 = row.iloc[0], row.iloc[1], row.iloc[2]
    panels_all.append([name_to_idx[n1], name_to_idx[n2], name_to_idx[n3]])
panels_all = np.array(panels_all)
print(f"反射面板总数: {len(panels_all)}")

# ===================== 4. 问题二调节方案 =====================
def calc_delta_r(X, f):
    """计算节点沿径向到理想抛物面的偏差"""
    n = X / R
    ne = n @ u
    a = 1.0 - ne**2
    if a < 1e-12:
        return R_f + f - R
    nP = n @ P
    b = -2.0*nP - 2.0*(R_f+2.0*f)*ne
    c = -4.0*f*(R_f+f)
    r = (-b + np.sqrt(b**2-4*a*c))/(2*a)
    return r - R

dot_prod = X_node @ u
perp_dist_sq = np.sum(X_node**2, axis=1) - dot_prod**2
in_illum_node = (perp_dist_sq <= rho_max**2) & (dot_prod < 0)
print(f"照明区内节点数: {np.sum(in_illum_node)}")

deltas = np.array([calc_delta_r(X_node[i], f_opt) if in_illum_node[i] else 0.0 for i in range(N_total)])
n_vec = X_node / R
X_adj = X_node + deltas[:, np.newaxis] * n_vec  # 调节后节点坐标

# ===================== 5. 筛选照明区面板（附件3实际面板）=====================
tri_centers_base = X_node[panels_all].mean(axis=1)
tri_perp = np.sqrt(np.sum(tri_centers_base**2, axis=1) - (tri_centers_base @ u)**2)
valid_panels = tri_perp <= rho_max
panels_illum = panels_all[valid_panels]
N_tri = len(panels_illum)
print(f"照明区面板数: {N_tri}")

# 构造馈源平面基向量（用于图3投影）
if abs(u[2]) < 0.9:
    u1 = np.cross(u, np.array([0, 0, 1.0]))
else:
    u1 = np.cross(u, np.array([1.0, 0, 0]))
u1 = u1 / np.linalg.norm(u1)
u2 = np.cross(u, u1)

# ===================== 6. 光线追踪函数 =====================
def trace_rays(points, tris, u, P, feed_r, ideal=False, f=None):
    N = len(tris)
    hit = np.zeros(N, dtype=bool)
    area = np.zeros(N)
    dist_focus = np.full(N, 1e6)
    cpd = np.zeros(N)
    V = P - f * u if (ideal and f) else None

    for i in range(N):
        v0, v1, v2 = points[tris[i]]
        e1 = v1 - v0
        e2 = v2 - v0
        normal = np.cross(e1, e2)
        area[i] = 0.5 * np.linalg.norm(normal)
        center = (v0 + v1 + v2) / 3.0
        cpd[i] = np.sqrt(np.sum(center**2) - (center @ u)**2)

        if ideal and V is not None:
            # 理想情形：三个顶点处理想抛物面法向量平均
            normals = []
            for v in [v0, v1, v2]:
                d = v - V
                grad = 2*d - 2*(d @ u)*u - 4*f*u
                nh = grad / np.linalg.norm(grad)
                if nh @ u < 0: nh = -nh
                normals.append(nh)
            n_hat = np.mean(normals, axis=0)
            n_hat = n_hat / np.linalg.norm(n_hat)
            if n_hat @ u < 0: n_hat = -n_hat
        else:
            n_hat = normal / np.linalg.norm(normal)
            if n_hat @ u < 0: n_hat = -n_hat

        # 反射方向 r = -u + 2(u·n)n
        r = -u + 2.0 * (u @ n_hat) * n_hat
        ru = r @ u
        if abs(ru) < 1e-12:
            continue
        t = (P - center) @ u / ru
        if t <= 0:
            continue
        X_hit = center + t * r
        dist = np.linalg.norm(X_hit - P)
        dist_focus[i] = dist
        hit[i] = dist <= feed_r

    total = np.sum(area)
    hit_a = np.sum(area[hit])
    ratio = hit_a / total if total > 0 else 0
    return ratio, hit, area, dist_focus, cpd

# ===================== 7. 三种情形计算 =====================
print("\n开始光线追踪...")
ratio_adj, hit_adj, area_adj, dist_adj, cpd_adj = trace_rays(X_adj, panels_illum, u, P, feed_radius)
print(f"调节后抛物面接收比: {ratio_adj*100:.2f}%")

ratio_base, hit_base, area_base, dist_base, cpd_base = trace_rays(X_node, panels_illum, u, P, feed_radius)
print(f"基准球面接收比: {ratio_base*100:.2f}%")

ratio_ideal, hit_ideal, area_ideal, dist_ideal, cpd_ideal = trace_rays(
    X_adj, panels_illum, u, P, feed_radius, ideal=True, f=f_opt)
print(f"理想情形接收比: {ratio_ideal*100:.2f}%")

# 调试统计
valid_dist = dist_adj[dist_adj < 1e5]
print(f"\n调试 - 调节后反射光线交点到焦点距离统计:")
print(f"  中位数: {np.median(valid_dist):.4f} m")
print(f"  均值: {np.mean(valid_dist):.4f} m")
print(f"  ≤0.5m: {np.sum(valid_dist<=0.5)}/{len(valid_dist)} ({np.sum(valid_dist<=0.5)/len(valid_dist)*100:.1f}%)")
print(f"  ≤1m: {np.sum(valid_dist<=1)}/{len(valid_dist)} ({np.sum(valid_dist<=1)/len(valid_dist)*100:.1f}%)")
print(f"  ≤5m: {np.sum(valid_dist<=5)}/{len(valid_dist)} ({np.sum(valid_dist<=5)/len(valid_dist)*100:.1f}%)")

# ===================== 8. 分环带统计 =====================
bins = [0, 30, 60, 90, 120, 151]
bin_labels = ['0-30m', '30-60m', '60-90m', '90-120m', '120-150m']

def bin_stats(cpd, hit, area, bins, labels):
    stats = []
    for i in range(len(bins)-1):
        mask = (cpd >= bins[i]) & (cpd < bins[i+1])
        if np.sum(mask) > 0:
            total = np.sum(area[mask])
            hit_a = np.sum(area[mask & hit])
            ratio = hit_a / total * 100 if total > 0 else 0
            stats.append([labels[i], int(np.sum(mask)), round(total, 2), round(hit_a, 2), round(ratio, 2)])
    return stats

stats_adj = bin_stats(cpd_adj, hit_adj, area_adj, bins, bin_labels)
stats_base = bin_stats(cpd_base, hit_base, area_base, bins, bin_labels)

# ===================== 9. 漏光统计 =====================
miss_mask = ~hit_adj
miss_dist = dist_adj[miss_mask & (dist_adj < 1e5)]
miss_area = area_adj[miss_mask & (dist_adj < 1e5)]
total_miss = np.sum(miss_area)
dist_bins = [(0.5, 1, '0.5-1m'), (1, 2, '1-2m'), (2, 5, '2-5m'), (5, 10, '5-10m'), (10, 1e6, '>10m')]
miss_stats = []
for lo, hi, label in dist_bins:
    mask = (miss_dist >= lo) & (miss_dist < hi)
    a = np.sum(miss_area[mask])
    pct = a / total_miss * 100 if total_miss > 0 else 0
    miss_stats.append([label, int(np.sum(miss_area[mask]) if False else np.sum(mask)), round(a, 2), round(pct, 2)])

# ===================== 10. Excel输出 =====================
df_ratio = pd.DataFrame([
    ['调节后抛物面', f'{ratio_adj*100:.2f}%', round(np.sum(area_adj), 2), round(np.sum(area_adj[hit_adj]), 2)],
    ['基准球面', f'{ratio_base*100:.2f}%', round(np.sum(area_base), 2), round(np.sum(area_base[hit_base]), 2)],
    ['理想情形(可调姿态)', f'{ratio_ideal*100:.2f}%', round(np.sum(area_ideal), 2), round(np.sum(area_ideal[hit_ideal]), 2)],
], columns=['反射面类型', '接收比', '总面板面积(m²)', '命中面积(m²)'])

df_bin_adj = pd.DataFrame(stats_adj, columns=['环带区间', '面板数', '总面积(m²)', '命中面积(m²)', '接收比(%)'])
df_bin_base = pd.DataFrame(stats_base, columns=['环带区间', '面板数', '总面积(m²)', '命中面积(m²)', '接收比(%)'])
df_miss = pd.DataFrame(miss_stats, columns=['偏离距离区间', '面板数', '漏光面积(m²)', '占漏光总面积比例(%)'])

with pd.ExcelWriter('问题三_光线追踪接收比结果.xlsx') as writer:
    df_ratio.to_excel(writer, sheet_name='接收比对比', index=False)
    df_bin_adj.to_excel(writer, sheet_name='调节后分环带统计', index=False)
    df_bin_base.to_excel(writer, sheet_name='基准球面分环带统计', index=False)
    df_miss.to_excel(writer, sheet_name='漏光面板偏离统计', index=False)
print("\n✅ Excel已保存：问题三_光线追踪接收比结果.xlsx")

# ===================== 11. 4张配图（无柱状图）=====================
# 图1：接收比对比（散点图）
fig1, ax1 = plt.subplots(figsize=(7, 4.5))
cats = ['基准球面', '调节后抛物面', '理想情形\n(可调姿态)']
ratios = [ratio_base*100, ratio_adj*100, ratio_ideal*100]
markers = ['o', 's', '^']
for i, (c, r, m) in enumerate(zip(cats, ratios, markers)):
    ax1.scatter(i, r, marker=m, s=120, c='black', zorder=5, label=c)
    ax1.plot([i, i], [0, r], color='gray', linestyle='--', linewidth=0.8, alpha=0.5)
    ax1.text(i, r+2, f'{r:.2f}%', ha='center', va='bottom', fontsize=11)
ax1.set_xticks(range(3))
ax1.set_xticklabels(cats)
ax1.set_ylabel('接收比 / %', fontsize=12)
ax1.set_title('图1 不同反射面模型的馈源接收比对比', fontsize=12, pad=10)
ax1.set_ylim(0, max(ratios)*1.15)
ax1.legend(fontsize=9, frameon=False, loc='upper left')
ax1.grid(True, axis='y', linestyle='--', alpha=0.3)
plt.tight_layout()
plt.savefig('问题三_图1_接收比对比.png', dpi=300, bbox_inches='tight')
plt.close()

# 图2：分环带接收比（折线图）
fig2, ax2 = plt.subplots(figsize=(7, 4.5))
x = np.arange(len(bin_labels))
ax2.plot(x, [s[4] for s in stats_base], marker='o', linestyle='-', color='gray', linewidth=1.5, markersize=7, label='基准球面')
ax2.plot(x, [s[4] for s in stats_adj], marker='s', linestyle='-', color='black', linewidth=1.5, markersize=7, label='调节后抛物面')
ax2.fill_between(x, [s[4] for s in stats_base], [s[4] for s in stats_adj], alpha=0.1, color='gray', label='调节增益')
ax2.set_xlabel('面板中心到对称轴距离 / m', fontsize=12)
ax2.set_ylabel('接收比 / %', fontsize=12)
ax2.set_title('图2 不同径向环带的接收比分布', fontsize=12, pad=10)
ax2.set_xticks(x); ax2.set_xticklabels(bin_labels)
ax2.legend(fontsize=10, frameon=False)
ax2.grid(True, linestyle='--', alpha=0.3)
plt.tight_layout()
plt.savefig('问题三_图2_分环带接收比.png', dpi=300, bbox_inches='tight')
plt.close()

# 图3：馈源平面交点分布（散点图）
fig3, ax3 = plt.subplots(figsize=(6.5, 5.5))
hit_pts = []
for i in range(N_tri):
    v0, v1, v2 = X_adj[panels_illum[i]]
    normal = np.cross(v1-v0, v2-v0)
    nh = normal / np.linalg.norm(normal)
    if nh @ u < 0: nh = -nh
    center = (v0+v1+v2)/3
    r = -u + 2*(u @ nh)*nh
    ru = r @ u
    if abs(ru) < 1e-12: continue
    t = (P - center) @ u / ru
    if t <= 0: continue
    hp = center + t*r - P
    hit_pts.append([hp @ u1, hp @ u2])
hit_pts = np.array(hit_pts)
mask = np.sum(hit_pts**2, axis=1) <= 25
ax3.scatter(hit_pts[mask, 0], hit_pts[mask, 1], s=3, c='gray', alpha=0.5, marker='.')
ax3.add_patch(Circle((0,0), feed_radius, color='k', fill=False, lw=1.5, label=f'馈源有效区 r={feed_radius}m'))
ax3.add_patch(Circle((0,0), 1.0, color='k', fill=False, lw=0.8, ls='--', alpha=0.5, label='1m范围'))
ax3.scatter([0], [0], s=40, c='k', marker='*', zorder=5, label='焦点P')
ax3.set_xlabel('馈源平面方向1 / m', fontsize=11)
ax3.set_ylabel('馈源平面方向2 / m', fontsize=11)
ax3.set_title('图3 反射光线在馈源平面的交点分布', fontsize=12, pad=10)
ax3.legend(fontsize=9, frameon=False, loc='upper right')
ax3.set_aspect('equal'); ax3.set_xlim(-2.5, 2.5); ax3.set_ylim(-2.5, 2.5)
ax3.grid(True, linestyle='--', alpha=0.3)
plt.tight_layout()
plt.savefig('问题三_图3_馈源平面交点分布.png', dpi=300, bbox_inches='tight')
plt.close()

# 图4：漏光偏离距离分布（折线图）
fig4, ax4 = plt.subplots(figsize=(7, 4.5))
labels_p = [s[0] for s in miss_stats]
pcts = [s[3] for s in miss_stats]
x4 = np.arange(len(labels_p))
ax4.plot(x4, pcts, marker='D', linestyle='-', color='black', linewidth=1.5, markersize=7)
ax4.fill_between(x4, pcts, alpha=0.15, color='gray')
for i, p in enumerate(pcts):
    if p > 0:
        ax4.text(i, p+0.8, f'{p:.1f}%', ha='center', va='bottom', fontsize=10)
ax4.set_xlabel('反射光线交点到焦点的偏离距离', fontsize=12)
ax4.set_ylabel('占漏光面积比例 / %', fontsize=12)
ax4.set_title('图4 漏光面板反射光线偏离焦点距离分布', fontsize=12, pad=10)
ax4.set_xticks(x4); ax4.set_xticklabels(labels_p)
ax4.grid(True, linestyle='--', alpha=0.3)
plt.tight_layout()
plt.savefig('问题三_图4_漏光偏离距离分布.png', dpi=300, bbox_inches='tight')
plt.close()

print("\n✅ 4张配图已生成")
print("全部完成！")
