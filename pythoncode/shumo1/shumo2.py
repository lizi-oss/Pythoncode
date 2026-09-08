import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# ===================== 全局统一配置 =====================
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
EPS = 1e-8
c_line_blue = "#1f77b4"
c_all_score = "#2980b9"
c_top50_red = "#ff4b5c"
pie_color = ["#1f77b4", "#ff7f0e", "#2ca02c"]

# ===================== 1 读取数据 =====================
file = "附件1 近5年402家供应商的相关数据.xlsx"
order = pd.read_excel(file, sheet_name=0)
supply = pd.read_excel(file, sheet_name=1)
print("订货表尺寸：", order.shape)
print("供货表尺寸：", supply.shape)

# ===================== 2 基础清洗 =====================
order = order.fillna(0)
supply = supply.fillna(0)
# 提取纯数值240周列
week_cols = order.columns[2:]
order_week = order[week_cols].astype(float)
supply_week = supply[week_cols].astype(float)
# 负值清零
order_week[order_week < 0] = 0
supply_week[supply_week < 0] = 0

# ===================== 3 IQR异常值处理 =====================
def IQR_clean(row):
    Q1 = row.quantile(0.25)
    Q3 = row.quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    return row.clip(lower=lower, upper=upper)

supply_clean_week = supply_week.apply(IQR_clean, axis=1)
print("IQR异常值清洗完成")

# ===================== 4 构建6项评价指标 =====================
data = pd.DataFrame()
data["供应商"] = supply.iloc[:, 0]
data["材料类别"] = supply.iloc[:, 1]

# 指标：材料价值权重
map_lam = {"A":1.2, "B":1.1, "C":1.0}
data["材料价值权重"] = data["材料类别"].map(map_lam)

# 供货实力
data["总供货量"] = supply_clean_week.sum(axis=1)
data["平均供货量"] = supply_clean_week.mean(axis=1)

# 供货连续性
zero_count = (supply_week > 0).sum(axis=1)
data["供货连续性"] = zero_count / 240

# 供货稳定性（CV倒数正向化）
mean_p = supply_clean_week.mean(axis=1)
std_p = supply_clean_week.std(axis=1)
CV = std_p / mean_p.replace(0, np.nan)
CV = CV.fillna(999)
data["供货稳定性"] = 1 / (CV + EPS)

# 订单满足率（仅q>0周计算）
sat_list = []
valid_q_list = []
n_supp = len(order_week)
for i in range(n_supp):
    q_row = order_week.iloc[i]
    p_row = supply_week.iloc[i]
    mask = q_row > 0
    q_valid = q_row[mask]
    p_valid = p_row[mask]
    sat = np.minimum(p_valid, q_valid)
    sat_list.append(sat.sum())
    valid_q_list.append(q_valid.sum())
sum_sat = np.array(sat_list)
sum_q = np.array(valid_q_list)
rate = np.where(sum_q == 0, 0, sum_sat / (sum_q + EPS))
data["订单满足率"] = rate

# 输出指标表格
data.to_excel("六个评价指标结果.xlsx", index=False)
print("\n六项指标前5行：")
print(data.head())

# ===================== 5 熵权法计算6指标权重 =====================
X = data[["总供货量","平均供货量","供货连续性","供货稳定性","订单满足率","材料价值权重"]]
# 极差标准化
Z = pd.DataFrame()
for col in X.columns:
    min_x = X[col].min()
    max_x = X[col].max()
    Z[col] = (X[col] - min_x) / (max_x - min_x + EPS)
# 特征比重
P = Z / Z.sum(axis=0)
P = P.replace(0, EPS)
n = len(Z)
# 熵值、权重
E = -1 / np.log(n) * (P * np.log(P)).sum(axis=0)
D = 1 - E
W = D / D.sum()
# 权重表输出
weight_df = pd.DataFrame({"评价指标":X.columns, "熵值":E, "权重":W})
weight_df.to_excel("熵权法结果_6指标.xlsx", index=False)
print("\n熵权计算结果：")
print(weight_df.round(4))

# ===================== 6 TOPSIS综合评价 =====================
W_mat = W.values.reshape(1, -1)
V = Z * W_mat
v_plus = V.max(axis=0)
v_minus = V.min(axis=0)
D_plus = np.sqrt(((V - v_plus) ** 2).sum(axis=1))
D_minus = np.sqrt(((V - v_minus) ** 2).sum(axis=1))
score = D_minus / (D_plus + D_minus + EPS)
data["TOPSIS得分"] = score
data["排名"] = data["TOPSIS得分"].rank(ascending=False, method="first")
result = data.sort_values("TOPSIS得分", ascending=False)
# 导出全部供应商、TOP50表格
result.to_excel("402家供应商TOPSIS排名_6指标.xlsx", index=False)
top50 = result.head(50)
top50.to_excel("前50重要供应商_6指标.xlsx")
print("\n前50核心供应商预览：")
print(top50[["供应商","材料类别","TOPSIS得分","排名"]])

# ===================== 7 TOP50与全体均值对比 =====================
all_avg = result[["总供货量","供货稳定性"]].mean()
top50_avg = top50[["总供货量","供货稳定性"]].mean()
diff_val = top50_avg - all_avg
rise_pct = (diff_val / all_avg) * 100
print("\n==== TOP50对比全体均值 ====")
print("全体均值：\n", all_avg.round(4))
print("TOP50均值：\n", top50_avg.round(4))
print("高出数值：\n", diff_val.round(4))
print("提升百分比(%)：\n", rise_pct.round(2))

# ===================== 8 绘图  =====================
# 6个指标各自独立折线图
indicator_list = ["总供货量","平均供货量","供货连续性","供货稳定性","订单满足率","材料价值权重"]
for col_name in indicator_list:
    plt.figure(figsize=(12,4))
    plt.plot(np.arange(1,403), data[col_name], linewidth=1, color=c_line_blue)
    plt.xlabel("供应商编号(1~402)")
    plt.ylabel(f"{col_name}数值")
    plt.title(f"{col_name}指标分布折线图")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"单指标图_{col_name}.png", dpi=300)
    plt.show()

# 图1 指标权重折线图
plt.figure(figsize=(12,5))
plt.plot(X.columns, W, marker="o", linewidth=2, color=c_line_blue)
plt.ylabel("指标权重", fontsize=12)
plt.xlabel("评价指标", fontsize=12)
plt.title("各评价指标熵权权重折线图", fontsize=14)
plt.xticks(rotation=30)
for idx, val in enumerate(W):
    plt.text(idx, val+0.008, f"{val:.4f}", ha="center")
plt.grid(alpha=0.3)
plt.ylim(0, max(W)+0.1)
plt.tight_layout()
plt.savefig("图1_指标权重折线.png", dpi=300)
plt.show()

# 图2 全部402家综合得分总图
plt.figure(figsize=(12,5))
rank_all = np.arange(1, len(result)+1)
plt.plot(rank_all, result["TOPSIS得分"], linewidth=1.2, color=c_all_score)
plt.xlabel("供应商全局排名", fontsize=12)
plt.ylabel("TOPSIS综合得分", fontsize=12)
plt.title("402家供应商综合评价得分排序折线图", fontsize=14)
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("图2_全部供应商得分折线.png", dpi=300)
plt.show()

# 图3 TOP50得分总图
plt.figure(figsize=(12,5))
plt.plot(range(1,51), top50["TOPSIS得分"], marker="o", linewidth=2, color=c_top50_red)
plt.xlabel("供应商排名（1~50）", fontsize=12)
plt.ylabel("TOPSIS综合贴近度得分", fontsize=12)
plt.title("前50家核心供应商TOPSIS综合得分折线图", fontsize=14)
plt.xticks(range(0,51,5))
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("图3_TOP50供应商折线.png", dpi=300)
plt.show()

# 图4 材料类别饼图（允许，非柱状）
plt.figure(figsize=(6,5))
cat_count = result["材料类别"].value_counts()
plt.pie(cat_count, labels=cat_count.index, autopct="%1.1f%%", colors=pie_color)
plt.title("A/B/C材料供应商分布")
plt.tight_layout()
plt.savefig("图4_材料类别饼图.png", dpi=300)
plt.show()

# 图5 相关性热力图
plt.figure(figsize=(9,7))
ax = sns.heatmap(X.corr(), annot=True, cmap="YlGnBu", fmt=".2f", cbar_kws={"label":"相关系数"})
plt.title("供应商评价指标相关性分析")
plt.tight_layout()
plt.savefig("图5_指标相关性热力图.png", dpi=300)
plt.show()

print("\n全部运行完成！所有Excel表格完整输出，无柱状图，6个指标各一张独立折线图+综合图表")