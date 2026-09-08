# ========== 屏蔽全部绘图负号警告、修复宋体负号缺失 ==========
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimSun']
matplotlib.rcParams['axes.unicode_minus'] = False  # 消除\u2212字体报错
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import differential_evolution
import pandas as pd
import os

# 固定随机种子，每次运行优化结果完全一致
np.random.seed(42)

# ====================== 绘图风格 ======================
plt.rcParams.update({
    'lines.linewidth': 1.3,
    'axes.linewidth': 1.0,
    'font.size': 10,
    'font.family': 'SimSun',
    'axes.grid': True,
    'grid.color': '#dddddd',
    'grid.linestyle': '--',
    'grid.linewidth': 0.3,
    'legend.frameon': True,
    'legend.facecolor': 'white',
    'legend.edgecolor': '#666666',
    'figure.dpi': 150,
    'xtick.major.width': 0.8,
    'ytick.major.width': 0.8,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.3
})

COLORS = {
    "blue": "#1F77B4", "orange": "#FF7F0E", "green": "#2ca02c",
    "purple": "#9467BD", "red": "#D62728", "gray": "#505050", "black": "#000000"
}
LINE_SCHEME = [("-", "o"), ("--", "^"), ("-.", "s"), (":", "D")]

# ====================== 全局物理参数 ======================
O = np.array([0, 0, 0])
T = np.array([0, 200, 0])
M1_origin = np.array([20000, 0, 2000])
v_miss = 300
FY1_origin = np.array([17800, 0, 1800])
R_SMOKE = 10
V_SINK = 3
SMOKE_WINDOW = 20
g = 9.8
M1_dir = -M1_origin / np.linalg.norm(M1_origin)

# ====================== 运动学函数 ======================
def missile_location_vec(t_arr: np.ndarray):
    return M1_origin + v_miss * M1_dir * t_arr[:, None]

def fy1_drop_point(t_d: float, alpha: float, v_u: float):
    vx = -v_u * np.cos(alpha)
    vy = v_u * np.sin(alpha)
    vel = np.array([vx, vy, 0])
    return FY1_origin + vel * t_d

def smoke_detonate_pos(t_d: float, alpha: float, v_u: float, tau: float):
    drop_pt = fy1_drop_point(t_d, alpha, v_u)
    vx = -v_u * np.cos(alpha)
    vy = v_u * np.sin(alpha)
    x = drop_pt[0] + vx * tau
    y = drop_pt[1] + vy * tau
    z = drop_pt[2] - 0.5 * g * tau ** 2
    return np.array([x, y, z])

def smoke_ball_center(t_arr: np.ndarray, t_burst: float, det_pt: np.ndarray):
    delta_t = t_arr - t_burst
    z = det_pt[2] - V_SINK * delta_t
    return np.column_stack([np.full_like(delta_t, det_pt[0]),
                            np.full_like(delta_t, det_pt[1]),
                            z])

# ========== 点到线段距离函数 ==========
def distance_point_segment(P_arr: np.ndarray, A_arr: np.ndarray, B_arr: np.ndarray):
    AB = B_arr - A_arr
    AP = P_arr - A_arr
    dot_prod = np.sum(AP * AB, axis=1)
    len_sq_AB = np.sum(AB ** 2, axis=1)
    lam = dot_prod / len_sq_AB
    dist = np.empty(len(P_arr))

    mask1 = lam <= 0
    dist[mask1] = np.linalg.norm(AP[mask1], axis=1)

    mask2 = lam >= 1
    PB = P_arr[mask2] - B_arr[mask2]
    dist[mask2] = np.linalg.norm(PB, axis=1)

    mask3 = (lam > 0) & (lam < 1)
    proj = A_arr[mask3] + lam[mask3, None] * AB[mask3]
    dist[mask3] = np.linalg.norm(P_arr[mask3] - proj, axis=1)
    return dist

# 单枚烟幕时长计算
def calc_effective_time(t_d, alpha, v_u, step=0.001, tau=0):
    t_burst = t_d + tau
    t_start = t_burst
    t_end = t_burst + SMOKE_WINDOW
    det_point = smoke_detonate_pos(t_d, alpha, v_u, tau)

    coarse_t = np.arange(t_start, t_end, 0.02)
    M_coarse = missile_location_vec(coarse_t)
    C_coarse = smoke_ball_center(coarse_t, t_burst, det_point)
    T_batch = np.tile(T, (len(M_coarse), 1))
    d_coarse = distance_point_segment(C_coarse, M_coarse, T_batch)
    if np.all(d_coarse > R_SMOKE):
        return 0.0, coarse_t, d_coarse, np.array([])

    fine_t = np.arange(t_start, t_end, step)
    M_fine = missile_location_vec(fine_t)
    C_fine = smoke_ball_center(fine_t, t_burst, det_point)
    T_fine_batch = np.tile(T, (len(M_fine), 1))
    d_fine = distance_point_segment(C_fine, M_fine, T_fine_batch)
    valid_mask = d_fine <= R_SMOKE
    total_time = np.sum(valid_mask) * step
    valid_time_points = fine_t[valid_mask]
    return total_time, fine_t, d_fine, valid_time_points

# ====================== 三弹区间合并 ======================
def merge_intervals(intervals):
    if len(intervals) == 0:
        return [], 0.0
    sorted_intervals = sorted(intervals, key=lambda x: x[0])
    merged = [sorted_intervals[0]]
    for current_start, current_end in sorted_intervals[1:]:
        last_start, last_end = merged[-1]
        if current_start <= last_end:
            new_interval = (last_start, max(last_end, current_end))
            merged[-1] = new_interval
        else:
            merged.append((current_start, current_end))
    total_len = sum(end - start for start, end in merged)
    return merged, total_len

def calc_three_smoke_total_eff(vu, alpha, td_list, tau_list, step=0.001):
    single_eff_list = []
    interval_list = []
    single_info = []
    for k in range(3):
        td_k = td_list[k]
        tau_k = tau_list[k]
        teff_k, t_curve_k, d_curve_k, valid_time_points = calc_effective_time(td_k, alpha, vu, step=step, tau=tau_k)
        single_eff_list.append(teff_k)
        if len(valid_time_points) > 0:
            s = np.min(valid_time_points)
            e = np.max(valid_time_points)
            interval_list.append((s, e))
            single_info.append({"start": s, "end": e, "teff": teff_k})
        else:
            single_info.append({"start": np.nan, "end": np.nan, "teff": 0.0})
    merged_intervals, total_eff = merge_intervals(interval_list)
    return total_eff, single_eff_list, single_info

# ====================== 主程序 ======================
if __name__ == '__main__':
    # ---------------- 问题1 基准工况 ----------------
    print("="*50 + " 问题1计算结果 " + "="*50)
    vu_base = 120
    alpha_base = 0.0
    td_base = 1.5
    tau_base = 3.6
    t_burst_base = td_base + tau_base

    step_list = [0.01, 0.001, 0.0001]
    conv_data = []
    for s in step_list:
        teff, _, _, _ = calc_effective_time(td_base, alpha_base, vu_base, step=s, tau=tau_base)
        conv_data.append([s, round(teff, 4)])
    df_conv = pd.DataFrame(conv_data, columns=["步长(s)", "有效遮蔽时长(s)"])
    print("\n【表3 步长收敛性检验】")
    print(df_conv)

    teff_ref, t_curve, d_curve, valid_time_points = calc_effective_time(td_base, alpha_base, vu_base, step=0.0001, tau=tau_base)
    if len(valid_time_points) > 0:
        t_start_val = round(np.min(valid_time_points), 4)
        t_end_val = round(np.max(valid_time_points), 4)
        teff_total = round(t_end_val - t_start_val, 4)
    else:
        t_start_val = np.nan
        t_end_val = np.nan
        teff_total = 0.0

    print("\n【表1 有效遮蔽区间】")
    df_t1 = pd.DataFrame([[t_start_val, t_end_val, teff_total]],
                         columns=["有效遮蔽开始时刻(s)", "有效遮蔽结束时刻(s)", "有效遮蔽时长(s)"])
    print(df_t1)

    t_mid = 8.73
    M_mid_pos = missile_location_vec(np.array([t_mid]))[0]
    det_mid = smoke_detonate_pos(td_base, alpha_base, vu_base, tau_base)
    C_mid_pos = smoke_ball_center(np.array([t_mid]), t_burst_base, det_mid)[0]
    P_single = np.array([C_mid_pos])
    A_single = np.array([M_mid_pos])
    B_single = np.array([T])
    d_mid_val = distance_point_segment(P_single, A_single, B_single)[0]

    df_t2 = pd.DataFrame([
        ["导弹位置M", M_mid_pos, "导弹沿x负方向匀速飞行"],
        ["烟幕球心C", C_mid_pos, "起爆后匀速下沉"],
        ["真目标T", T, "圆柱下底面圆心，模型简化为几何点"],
        ["球心至视线距离d", round(d_mid_val, 2), f"烟幕半径R={R_SMOKE}m"]
    ], columns=["物理量", "三维坐标(x,y,z)", "补充备注"])
    print("\n【表2 有效区间中点t=8.73s物理量校核】")
    print(df_t2)

    # 图1
    fig1, ax1 = plt.subplots(figsize=(7, 4))
    ax1.plot(t_curve, d_curve, color=COLORS["blue"], linestyle=LINE_SCHEME[0][0], marker=LINE_SCHEME[0][1], ms=2.5, label="球心到M-T视线距离 $d(t)$")
    ax1.axhline(y=R_SMOKE, color=COLORS["red"], linestyle=LINE_SCHEME[1][0], label=f"烟幕阈值 $R={R_SMOKE}\ \mathrm{{m}}$")
    mask_fill = d_curve <= R_SMOKE
    ax1.fill_between(t_curve, 0, d_curve, where=mask_fill, color=COLORS["green"], alpha=0.25, label="有效遮蔽时段")
    ax1.set_xlabel("时间 $t$ / s")
    ax1.set_ylabel("最短距离 $d(t)$ / m")
    ax1.set_title("问题1 烟幕球心至导弹-真目标视线距离时序曲线")
    ax1.legend()
    plt.savefig("fig1_distance_time.png")
    plt.close()

    # 图2
    fig2, ax2 = plt.subplots(figsize=(6, 3.2))
    ax2.plot(df_conv["步长(s)"], df_conv["有效遮蔽时长(s)"], color=COLORS["orange"], linestyle=LINE_SCHEME[2][0], marker=LINE_SCHEME[2][1], ms=3)
    ax2.set_xscale("log")
    ax2.set_xlabel("数值扫描步长 / s（对数坐标）")
    ax2.set_ylabel("有效遮蔽时长 / s")
    ax2.set_title("步长收敛性检验曲线")
    plt.savefig("fig2_convergence.png")
    plt.close()

    # 3D图
    from mpl_toolkits.mplot3d import Axes3D
    drop_mid = fy1_drop_point(td_base, alpha_base, vu_base)
    fig3 = plt.figure(figsize=(8, 6))
    ax3 = fig3.add_subplot(111, projection="3d")
    ax3.plot([M_mid_pos[0], T[0]], [M_mid_pos[1], T[1]], [M_mid_pos[2], T[2]], color=COLORS["black"], linewidth=1.4, label="导弹-目标观测视线 $MT$")
    ax3.scatter(*T, color=COLORS["green"], marker="s", s=90, zorder=10, label="真目标中心点 $T$")
    ax3.scatter(*M1_origin, edgecolor=COLORS["red"], facecolor="white", marker="D", s=70, linewidth=1.2, label="导弹初始位置 $M_0$")
    ax3.scatter(*M_mid_pos, color=COLORS["red"], marker="o", s=60, zorder=9, label="$t=8.73\mathrm{s}$ 导弹位置 $M$")
    ax3.scatter(*C_mid_pos, color=COLORS["blue"], marker="^", s=75, zorder=10, label="烟幕云团球心 $C$")
    ax3.scatter(*drop_mid, color=COLORS["purple"], marker="x", s=80, linewidth=1.3, label="无人机投放点 $F_{Y1}$")
    offset_x, offset_y, offset_z = 300, 8, 12
    ax3.text(T[0]+offset_x, T[1]+offset_y, T[2]+offset_z, "$T(0,200,0)$", fontsize=9)
    ax3.text(M1_origin[0]-1200, M1_origin[1]+offset_y, M1_origin[2]+offset_z, "$M_0(20000,0,2000)$", fontsize=9)
    ax3.text(M_mid_pos[0]-1000, M_mid_pos[1]+offset_y, M_mid_pos[2]-offset_z, "$M(t)$", fontsize=9)
    ax3.text(C_mid_pos[0]-800, C_mid_pos[1]+offset_y, C_mid_pos[2]+offset_z, "$C(t)$", fontsize=9)
    ax3.text(drop_mid[0]-900, drop_mid[1]+offset_y, drop_mid[2]-offset_z, "投放点", fontsize=9)
    ax3.set_xlabel("$X$ 坐标 / m", fontsize=10, labelpad=12)
    ax3.set_ylabel("$Y$ 坐标 / m", fontsize=10, labelpad=12)
    ax3.set_zlabel("$Z$ 坐标 / m", fontsize=10, labelpad=12)
    ax3.tick_params(labelsize=8)
    ax3.xaxis.pane.set_edgecolor("#666666")
    ax3.yaxis.pane.set_edgecolor("#666666")
    ax3.zaxis.pane.set_edgecolor("#666666")
    ax3.xaxis.pane.fill = False
    ax3.yaxis.pane.fill = False
    ax3.zaxis.pane.fill = False
    ax3.view_init(elev=22, azim=-65)
    ax3.set_title("$t=8.73\mathrm{s}$ 攻防空域三维几何示意图", fontsize=11, pad=15)
    ax3.legend(loc="upper left", bbox_to_anchor=(1.03, 1), fontsize=8.5)
    plt.tight_layout()
    plt.savefig("fig3_3d_airspace_model.png")
    plt.close()

    # ---------------- 问题2 单弹最优投放策略差分进化优化 ----------------
    print("\n" + "="*50 + " 问题2 单弹最优投放策略差分进化优化 " + "="*50)
    bounds = [(70, 140), (0, 0.3), (0, 8), (1, 8)]

    def target_func(x):
        vu, a, td, tau = x
        t_eff, _, _, _ = calc_effective_time(td, a, vu, step=0.001, tau=tau)
        return -t_eff

    iter_record = []
    def callback(xk, convergence):
        iter_record.append(-target_func(xk))

    opt_result = differential_evolution(
        target_func,
        bounds=bounds,
        popsize=60,
        maxiter=120,
        tol=0.005,
        updating="deferred",
        workers=1,
        callback=callback
    )
    vu_opt, alpha_opt, td_opt, tau_opt = opt_result.x
    max_eff_time = round(-opt_result.fun, 4)
    t_burst_opt = round(td_opt + tau_opt, 3)
    det_opt_pos = np.round(smoke_detonate_pos(td_opt, alpha_opt, vu_opt, tau_opt), 1)

    df_t4 = pd.DataFrame([[
        round(vu_opt, 2), round(alpha_opt, 3), round(td_opt, 3), round(tau_opt, 3),
        t_burst_opt, max_eff_time, det_opt_pos[0], det_opt_pos[1], det_opt_pos[2]
    ]], columns=[
        "最优飞行速度vu(m/s)","航向α(rad)","投放时刻td(s)","起爆延迟τ(s)",
        "起爆时刻tb(s)","最大有效遮蔽时长(s)","起爆点X","起爆点Y","起爆点Z"
    ])
    print("\n【表4 问题2单弹最优投放策略】")
    print(df_t4)

    fig4, ax4 = plt.subplots(figsize=(6, 3.2))
    ax4.plot(range(len(iter_record)), iter_record, color=COLORS["purple"], linestyle=LINE_SCHEME[3][0], marker=LINE_SCHEME[3][1], ms=2)
    ax4.set_xlabel("差分进化迭代次数")
    ax4.set_ylabel("当前最优有效遮蔽时长 / s")
    ax4.set_title("问题2 单弹优化迭代收敛曲线")
    plt.savefig("fig4_optim_iter.png")
    plt.close()

    # ====================== 问题3 单机3枚烟幕协同投放优化 ======================
    print("\n" + "="*50 + " 问题3 单机3枚烟幕协同投放优化 " + "="*50)
    bounds_q3 = [
        (70, 140),          #0 vu
        (0, 0.3),           #1 alpha
        (0, 8), (0, 8), (0, 8), #2 td1, 3 td2, 4 td3
        (1, 8), (1, 8), (1, 8)  #5 τ1, 6 τ2, 7 τ3
    ]

    def target_func_q3(x):
        vu = x[0]
        alpha = x[1]
        td1, td2, td3 = x[2], x[3], x[4]
        tau1, tau2, tau3 = x[5], x[6], x[7]
        td_list = [td1, td2, td3]
        tau_list = [tau1, tau2, tau3]
        penalty = 0.0
        diff12 = abs(td1 - td2)
        diff13 = abs(td1 - td3)
        diff23 = abs(td2 - td3)
        if diff12 < 1:
            penalty += (1 - diff12) * 1000
        if diff13 < 1:
            penalty += (1 - diff13) * 1000
        if diff23 < 1:
            penalty += (1 - diff23) * 1000
        total_eff, _, _ = calc_three_smoke_total_eff(vu, alpha, td_list, tau_list, step=0.001)
        return -total_eff + penalty

    iter_record_q3 = []
    def callback_q3(xk, convergence):
        vu = xk[0]
        alpha = xk[1]
        td1, td2, td3 = xk[2], xk[3], xk[4]
        tau1, tau2, tau3 = xk[5], xk[6], xk[7]
        td_list = [td1, td2, td3]
        tau_list = [tau1, tau2, tau3]
        total_eff, _, _ = calc_three_smoke_total_eff(vu, alpha, td_list, tau_list, step=0.001)
        iter_record_q3.append(total_eff)

    # 调大种群与迭代，解决单弹失效问题
    opt_result_q3 = differential_evolution(
        target_func_q3,
        bounds_q3,
        popsize=150,
        maxiter=150,
        tol=0.001,
        updating="deferred",
        workers=1,
        callback=callback_q3
    )
    x_opt_q3 = opt_result_q3.x
    print(f"问题3优化输出变量数量：{len(x_opt_q3)}")
    if len(x_opt_q3) != 8:
        raise Exception("警告！优化输出变量不足8个，边界设置或可行域存在问题！")

    vu_opt_q3 = x_opt_q3[0]
    alpha_opt_q3 = x_opt_q3[1]
    td1_opt, td2_opt, td3_opt = x_opt_q3[2], x_opt_q3[3], x_opt_q3[4]
    tau1_opt, tau2_opt, tau3_opt = x_opt_q3[5], x_opt_q3[6], x_opt_q3[7]
    td_opt_list = [td1_opt, td2_opt, td3_opt]
    tau_opt_list = [tau1_opt, tau2_opt, tau3_opt]

    total_eff_q3, single_eff_list, single_info = calc_three_smoke_total_eff(
        vu_opt_q3, alpha_opt_q3, td_opt_list, tau_opt_list, step=0.0001
    )
    interval_list = []
    for info in single_info:
        if not np.isnan(info["start"]):
            interval_list.append((info["start"], info["end"]))
    merged_intervals, _ = merge_intervals(interval_list)
    total_eff_q3 = round(total_eff_q3, 4)

    # ========== 新版表5：匹配你指定表头 ==========
    table5_data = []
    alpha_deg = alpha_opt_q3 * 180 / np.pi
    for k in range(3):
        tk_drop = td_opt_list[k]
        tk_tau = tau_opt_list[k]
        drop_pt = np.round(fy1_drop_point(tk_drop, alpha_opt_q3, vu_opt_q3), 2)
        det_pt = np.round(smoke_detonate_pos(tk_drop, alpha_opt_q3, vu_opt_q3, tk_tau), 2)
        teff_k = round(single_eff_list[k], 4)
        table5_data.append([
            round(alpha_opt_q3, 3),
            round(vu_opt_q3, 2),
            k + 1,
            drop_pt[0], drop_pt[1], drop_pt[2],
            det_pt[0], det_pt[1], det_pt[2],
            teff_k
        ])
    df_t5 = pd.DataFrame(table5_data, columns=[
        "无人机运动方向",
        "无人机运动速度 (m/s)",
        "烟幕干扰弹编号",
        "烟幕干扰弹投放点的x坐标 (m)",
        "烟幕干扰弹投放点的y坐标 (m)",
        "烟幕干扰弹投放点的z坐标 (m)",
        "烟幕干扰弹起爆点的x坐标 (m)",
        "烟幕干扰弹起爆点的y坐标 (m)",
        "烟幕干扰弹起爆点的z坐标 (m)",
        "有效干扰时长 (s)"
    ])
    print("\n【表5 三弹投放策略_问题3（新格式）】")
    print(df_t5)

    table6_data = []
    sum_single = 0.0
    for k in range(3):
        info = single_info[k]
        val = info["teff"]
        sum_single += val
        s_str = round(info["start"],4) if not np.isnan(info["start"]) else "无"
        e_str = round(info["end"],4) if not np.isnan(info["start"]) else "无"
        table6_data.append([k+1, s_str, e_str, round(val,4)])
    table6_data.append(["合并总区间", merged_intervals, "-", total_eff_q3])
    df_t6 = pd.DataFrame(table6_data, columns=["弹编号", "有效开始时刻(s)", "有效结束时刻(s)", "有效遮蔽时长(s)"])
    print("\n【表6 三弹分弹有效遮蔽区间】")
    print(df_t6)
    print(f"\n单弹时长累加和：{sum_single:.4f} s；去重叠真实总遮蔽时长：{total_eff_q3} s")

    if teff_total > 0:
        print(f"对比问题1基准单弹时长{teff_total} s，提升倍数：{round(total_eff_q3 / teff_total, 2)}")
    else:
        print("问题1基准时长为0，无法计算提升倍数。")

    fig5, ax5 = plt.subplots(figsize=(6, 3.2))
    ax5.plot(range(len(iter_record_q3)), iter_record_q3, color=COLORS["green"], linestyle="-", marker="o", ms=2)
    ax5.set_xlabel("差分进化迭代次数")
    ax5.set_ylabel("总有效遮蔽时长 / s")
    ax5.set_title("问题3 三弹协同优化迭代收敛曲线")
    plt.savefig("fig5_q3_optim_iter.png")
    plt.close()

    fig6, ax6 = plt.subplots(figsize=(8, 3.5))
    color_list = [COLORS["blue"], COLORS["orange"], COLORS["purple"]]
    for k in range(3):
        info = single_info[k]
        if not np.isnan(info["start"]):
            ax6.hlines(y=k+1, xmin=info["start"], xmax=info["end"], color=color_list[k], lw=3, label=f"第{k+1}枚烟幕")
    for (s, e) in merged_intervals:
        ax6.hlines(y=0, xmin=s, xmax=e, color=COLORS["red"], lw=4, label="合并后总遮蔽区间")
    ax6.set_yticks([0,1,2,3])
    ax6.set_yticklabels(["总合并区间","弹1","弹2","弹3"])
    ax6.set_xlabel("时间 t / s")
    ax6.set_ylabel("烟幕编号")
    ax6.legend(loc="upper right")
    plt.savefig("fig6_q3_smoke_time_line.png")
    plt.close()

    # ========== Excel导出：输出到桌面避免权限拒绝 ==========
    desk_file = os.path.expanduser(r"~\Desktop\烟幕干扰建模结果汇总.xlsx")
    with pd.ExcelWriter(desk_file) as writer:
        df_t1.to_excel(writer, sheet_name="表1_有效遮蔽区间_问题1", index=False)
        df_t2.to_excel(writer, sheet_name="表2_中点物理校核_问题1", index=False)
        df_conv.to_excel(writer, sheet_name="表3_步长收敛检验_问题1", index=False)
        df_t4.to_excel(writer, sheet_name="表4_单弹最优策略_问题2", index=False)
        df_t5.to_excel(writer, sheet_name="表5_三弹投放策略_问题3", index=False)
        df_t6.to_excel(writer, sheet_name="表6_三弹遮蔽区间_问题3", index=False)

    print(f"\n==== 全部输出文件清单 ====")
    print(f"Excel 文件已保存至桌面：{desk_file}")
    print("图片：fig1、fig2、fig3、fig4、fig5、fig6（代码同目录）")