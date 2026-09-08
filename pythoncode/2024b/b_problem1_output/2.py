# -*- coding: utf-8 -*-
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams['figure.dpi'] = 300
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.linestyle'] = '--'
plt.rcParams['grid.alpha'] = 0.3

COLOR_MAIN = "#1f77b4"
OUT_DIR = "./b_problem2_output"
if not os.path.exists(OUT_DIR):
    os.makedirs(OUT_DIR)

cases = [
    {
        "name": "情形1",
        "p1": 0.1, "p2": 0.1, "p3": 0.1,
        "c1": 4, "c2": 3,
        "ct1": 1, "ct2": 1,
        "c_ass": 2, "ctf": 2,
        "c_dis": 3, "c_ex": 30, "price": 30
    },
    {
        "name": "情形2",
        "p1": 0.1, "p2": 0.1, "p3": 0.1,
        "c1": 20, "c2": 18,
        "ct1": 1, "ct2": 1,
        "c_ass": 2, "ctf": 2,
        "c_dis": 3, "c_ex": 30, "price": 30
    },
    {
        "name": "情形3",
        "p1": 0.1, "p2": 0.1, "p3": 0.1,
        "c1": 4, "c2": 3,
        "ct1": 1, "ct2": 1,
        "c_ass": 2, "ctf": 2,
        "c_dis": 3, "c_ex": 40, "price": 30
    },
    {
        "name": "情形4",
        "p1": 0.1, "p2": 0.1, "p3": 0.1,
        "c1": 20, "c2": 20,
        "ct1": 1, "ct2": 1,
        "c_ass": 2, "ctf": 2,
        "c_dis": 3, "c_ex": 30, "price": 30
    },
    {
        "name": "情形5",
        "p1": 0.1, "p2": 0.2, "p3": 0.1,
        "c1": 10, "c2": 18,
        "ct1": 1, "ct2": 1,
        "c_ass": 2, "ctf": 2,
        "c_dis": 3, "c_ex": 10, "price": 30
    },
    {
        "name": "情形6",
        "p1": 0.05, "p2": 0.05, "p3": 0.05,
        "c1": 4, "c2": 3,
        "ct1": 1, "ct2": 1,
        "c_ass": 2, "ctf": 2,
        "c_dis": 3, "c_ex": 10, "price": 30
    }
]

def calc_strategy_profit(param, d1, d2, d3, d4, dd1, dd2, dd3, max_iter=1000, tol=1e-12):
    p1, p2, p3 = param["p1"], param["p2"], param["p3"]
    c1, c2 = param["c1"], param["c2"]
    ct1, ct2 = param["ct1"], param["ct2"]
    c_ass = param["c_ass"]
    ctf = param["ctf"]
    c_dis = param["c_dis"]
    c_ex = param["c_ex"]
    S = param["price"]

    def new_part_cost(p, c, ct, detect):
        if detect:
            return (c + ct) / (1.0 - p)
        else:
            return c

    cost_p1_new = new_part_cost(p1, c1, ct1, d1)
    cost_p2_new = new_part_cost(p2, c2, ct2, d2)
    p1_in_new = 0.0 if d1 else p1
    p2_in_new = 0.0 if d2 else p2
    p_pass_new = (1.0 - p1_in_new) * (1.0 - p2_in_new) * (1.0 - p3)
    p_fail_new = 1.0 - p_pass_new

    if p_fail_new < 1e-15:
        total_cost = cost_p1_new + cost_p2_new + c_ass + d3 * ctf
        return S - total_cost

    p1_post = p1_in_new / p_fail_new
    p2_post = p2_in_new / p_fail_new

    def dis_part_cost(s, ct, detect):
        if detect:
            return ct / (1.0 - s)
        else:
            return 0.0

    cost_p1_dis = dis_part_cost(p1_post, ct1, dd1)
    cost_p2_dis = dis_part_cost(p2_post, ct2, dd2)
    p1_in_dis = 0.0 if dd1 else p1_post
    p2_in_dis = 0.0 if dd2 else p2_post
    p_pass_dis = (1.0 - p1_in_dis) * (1.0 - p2_in_dis) * (1.0 - p3)
    p_fail_dis = 1.0 - p_pass_dis

    C_new = cost_p1_new + cost_p2_new + c_ass + d3 * ctf
    C_dis = c_dis + cost_p1_dis + cost_p2_dis + c_ass + dd3 * ctf

    for _ in range(max_iter):
        loss_new = c_ex if not d3 else 0.0
        if d4:
            follow_new = loss_new + C_dis
        else:
            follow_new = loss_new + C_new
        C_new_next = cost_p1_new + cost_p2_new + c_ass + d3 * ctf + p_fail_new * follow_new

        loss_dis = c_ex if not dd3 else 0.0
        if d4:
            follow_dis = loss_dis + C_dis
        else:
            follow_dis = loss_dis + C_new
        C_dis_next = c_dis + cost_p1_dis + cost_p2_dis + c_ass + dd3 * ctf + p_fail_dis * follow_dis

        if abs(C_new_next - C_new) < tol and abs(C_dis_next - C_dis) < tol:
            C_new, C_dis = C_new_next, C_dis_next
            break
        C_new, C_dis = C_new_next, C_dis_next

    profit = S - C_new
    return profit

strategy_list = []
for d1 in [0, 1]:
    for d2 in [0, 1]:
        for d3 in [0, 1]:
            for d4 in [0, 1]:
                if d4 == 0:
                    desc = f"{'检测' if d1 else '不检测'}配件1，{'检测' if d2 else '不检测'}配件2，{'检测' if d3 else '不检测'}成品，报废"
                    strategy_list.append({"d1":d1,"d2":d2,"d3":d3,"d4":d4,"dd1":0,"dd2":0,"dd3":0,"desc":desc})
                else:
                    for dd1 in [0, 1]:
                        for dd2 in [0, 1]:
                            for dd3 in [0, 1]:
                                desc = f"{'检测' if d1 else '不检测'}配件1，{'检测' if d2 else '不检测'}配件2，{'检测' if d3 else '不检测'}成品，拆解；拆件{'检测' if dd1 else '不检测'}1，{'检测' if dd2 else '不检测'}2，重成品{'检测' if dd3 else '不检测'}"
                                strategy_list.append({"d1":d1,"d2":d2,"d3":d3,"d4":d4,"dd1":dd1,"dd2":dd2,"dd3":dd3,"desc":desc})

all_result = []
best_result = []

for case in cases:
    case_name = case["name"]
    best_profit = -np.inf
    best_strat = None

    for strat in strategy_list:
        profit = calc_strategy_profit(case, strat["d1"], strat["d2"], strat["d3"], strat["d4"], strat["dd1"], strat["dd2"], strat["dd3"])
        all_result.append({"情形": case_name, "策略": strat["desc"], "期望利润": round(profit, 3)})
        if profit > best_profit:
            best_profit = profit
            best_strat = strat

    best_result.append({
        "情形": case_name,
        "配件1": "检测" if best_strat["d1"] else "不检测",
        "配件2": "检测" if best_strat["d2"] else "不检测",
        "成品": "检测" if best_strat["d3"] else "不检测",
        "处理": "拆解" if best_strat["d4"] else "报废",
        "拆件1": "检测" if best_strat["dd1"] else "不检测",
        "拆件2": "检测" if best_strat["dd2"] else "不检测",
        "重成品": "检测" if best_strat["dd3"] else "不检测",
        "期望利润": round(best_profit, 3)
    })

df_all = pd.DataFrame(all_result)
df_best = pd.DataFrame(best_result)

df_all.to_csv(os.path.join(OUT_DIR, "all_strategies_detail.csv"), index=False, encoding="utf_8_sig")
df_best.to_csv(os.path.join(OUT_DIR, "best_strategy_summary.csv"), index=False, encoding="utf_8_sig")

print("="*70)
print("最优策略汇总：")
print(df_best.to_string(index=False))
print("="*70)

# ===================== 替换为折线图（无柱状图） =====================
fig, ax = plt.subplots(figsize=(9, 5))
x = np.arange(len(cases))
profits = [item["期望利润"] for item in best_result]

# 折线+圆形数据标记
ax.plot(x, profits, color=COLOR_MAIN, marker='o', linewidth=2.2, markersize=7, zorder=3)

# 数值标注
for xi, val in zip(x, profits):
    offset = 0.5 if val >= 0 else -1.5
    ax.text(xi, val + offset, f"{val:.3f}", ha="center", va="bottom", fontsize=10, zorder=4)

# 盈亏参考线
ax.axhline(y=0, color='black', linewidth=0.9, linestyle='--', zorder=1)

ax.set_xticks(x)
ax.set_xticklabels([c["name"] for c in cases], fontsize=11)
ax.set_ylabel("期望利润（元/套）", fontsize=11)
ax.set_title("图5 六种情形最优策略下的期望利润对比", fontsize=13)
ax.set_ylim(min(profits) - 6, max(profits) * 1.18)
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
fig.savefig(os.path.join(OUT_DIR, "fig5_profit_compare.png"), dpi=300, bbox_inches="tight")
plt.close(fig)

print(f"\n结果已输出至：{OUT_DIR}")
