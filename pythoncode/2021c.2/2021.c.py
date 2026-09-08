import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 设置中文显示（防止图表乱码）
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
plt.rcParams["axes.unicode_minus"] = False

# =====================================================
# 1 数据读取
# =====================================================
file = "附件1 近5年402家供应商的相关数据.xlsx"

order = pd.read_excel(file, sheet_name=0)
supply = pd.read_excel(file, sheet_name=1)

print("订货数据:")
print(order.head())
print("供货数据:")
print(supply.head())

# =====================================================
# 2 数据清洗 + IQR异常值处理（论文要求新增）
# =====================================================
order = order.fillna(0)
supply = supply.fillna(0)

# 240周数据
week_cols = order.columns[2:]
order_week = order[week_cols].astype(float)
supply_week = supply[week_cols].astype(float)

# 负数截断为0
order_week[order_week < 0] = 0
supply_week[supply_week < 0] = 0

# ----------------------新增：IQR四分位异常清洗函数----------------------
def iqr_clean(row):
    data = row.values
    valid = data[data > 0]
    if len(valid) == 0:
        return row
    q1 = np.percentile(valid, 25)
    q3 = np.percentile(valid, 75)
    iqr = q3 - q1
    low = q1 - 1.5 * iqr
    high = q3 + 1.5 * iqr
    clean_r = row.copy()
    clean_r[(clean_r < low) | (clean_r > high)] = np.nan
    return clean_r

# 清洗后供货矩阵（后续统计、指标全部用这个）
supply_clean_week = supply_week.apply(iqr_clean, axis=1)
print("IQR异常值清洗完成")

print("基础数据清洗完成")

# ==============================
# 3. 数据统计分析（删除错误平均差值，修复除零bug）
# ==============================
stat = pd.DataFrame()
stat["供应商ID"] = supply.iloc[:,0]

# 供货次数（原始未清洗，统计断供周数）
stat["供货次数"] = (supply_week > 0).sum(axis=1)

# 供货总量（使用IQR清洗后数据，剔除极端异常值）
stat["供货总量"] = supply_clean_week.sum(axis=1)

# 平均供货量：修复除以0报错
supply_mean_clean = supply_clean_week.mean(axis=1)
stat["平均供货量"] = np.where(stat["供货次数"] == 0, 0, supply_mean_clean)

# =========删除你原来的平均差值代码（论文无此指标，无用）=========

# 保留两位小数
stat = stat.round(1)
print(stat.head())

# 保存统计表
stat.to_excel("表5-1供应商数据统计分析.xlsx", index=False)

# =====================================================
# 3 五个评价指标构建（全部改用IQR清洗后供货数据）
# =====================================================
data = pd.DataFrame()
data["供应商"] = supply.iloc[:,0]
data["材料类别"] = supply.iloc[:,1]

# -----------------------------------------------------
# 指标5 材料价值权重
# -----------------------------------------------------
category_weight = {"A":1.2, "B":1.1, "C":1.0}
data["材料价值权重"] = data["材料类别"].map(category_weight)

# -----------------------------------------------------
# 指标1 供货规模（清洗后供货总量×材料权重）
# -----------------------------------------------------
total_supply = supply_clean_week.sum(axis=1)
data["供货规模"] = total_supply * data["材料价值权重"]

# -----------------------------------------------------
# 指标2 供货稳定性 CV倒数（清洗后数据计算均值标准差）
# -----------------------------------------------------
mean_supply = supply_clean_week.mean(axis=1)
std_supply = supply_clean_week.std(axis=1)

CV = std_supply / mean_supply.replace(0, np.nan)
CV = CV.fillna(999)
data["供货稳定性"] = 1 / (CV + 1e-12)

# -----------------------------------------------------
# 指标3 订单满足率（论文规则：仅q>0周、超供不计分）
# -----------------------------------------------------
real_supply = np.minimum(supply_week, order_week)
sum_real = real_supply.sum(axis=1)
sum_order_all = order_week.sum(axis=1).replace(0, np.nan)

data["订单满足率"] = sum_real / sum_order_all
data["订单满足率"] = data["订单满足率"].fillna(0)

# -----------------------------------------------------
# 指标4 供货连续性（原始供货非零周/240）
# -----------------------------------------------------
non_zero_week = (supply_week > 0).sum(axis=1)
data["供货连续性"] = non_zero_week / 240

# 保存指标
data.to_excel("五个评价指标结果.xlsx", index=False)

# =====================================================
# 4 熵权法
# =====================================================
X = data[["供货规模","供货稳定性","订单满足率","供货连续性","材料价值权重"]]

# ------------------极差标准化------------------
Z = X.copy().astype(float)
for col in Z.columns:
    min_x = Z[col].min()
    max_x = Z[col].max()
    Z[col] = (Z[col] - min_x) / (max_x - min_x + 1e-12)

# ------------------特征比重------------------
P = Z / Z.sum(axis=0)
P = P.replace(0, 1e-12)
n = len(Z)

# ------------------熵值------------------
entropy = -1 / np.log(n) * (P * np.log(P)).sum(axis=0)

# ------------------权重------------------
d = 1 - entropy
weight = d / d.sum()

# 输出熵值权重
weight_table = pd.DataFrame({
    "评价指标":X.columns,
    "熵值":entropy,
    "权重":weight
})
weight_table.to_excel("熵权法结果.xlsx", index=False)
print("\n=====熵值与指标权重=====")
print(weight_table)

# =====================新增：指标权重折线图=====================
plt.figure(figsize=(10,5))
plt.plot(weight_table["评价指标"], weight_table["权重"], marker="o", linewidth=2, color="#1f77b4")
plt.title("各评价指标熵权权重折线图", fontsize=14)
plt.xlabel("评价指标", fontsize=12)
plt.ylabel("指标权重", fontsize=12)
plt.grid(alpha=0.3)
for x,y in zip(weight_table["评价指标"], weight_table["权重"]):
    plt.text(x, y+0.005, f"{y:.4f}", ha="center")
plt.tight_layout()
plt.savefig("指标权重折线图.png", dpi=300)
plt.show()

# =====================================================
# 5 TOPSIS
# =====================================================
# 加权矩阵
V = Z * weight.values

# 正、负理想解
positive = V.max(axis=0)
negative = V.min(axis=0)

# 欧氏距离
D_plus = np.sqrt(((V - positive)**2).sum(axis=1))
D_minus = np.sqrt(((V - negative)**2).sum(axis=1))

# 贴近度
C = D_minus / (D_plus + D_minus + 1e-12)
data["TOPSIS得分"] = C

# 排名
data["排名"] = data["TOPSIS得分"].rank(ascending=False, method="first")

# =====================================================
# 6 输出结果
# =====================================================
result = data.sort_values("TOPSIS得分", ascending=False)
result.to_excel("402家供应商TOPSIS排名.xlsx", index=False)

top50 = result.head(50)
top50.to_excel("前50重要供应商.xlsx", index=False)

print("\n=====TOP50供应商=====")
print(top50[["供应商","材料类别","TOPSIS得分","排名"]])

# =====================新增：TOP50供应商得分折线图=====================
plt.figure(figsize=(14,6))
x_rank = np.arange(1, 51)
score_50 = top50["TOPSIS得分"].values
plt.plot(x_rank, score_50, marker=".", linewidth=1.5, color="#ff4b5c")
plt.title("前50家核心供应商TOPSIS综合得分折线图", fontsize=14)
plt.xlabel("供应商排名（1~50）", fontsize=12)
plt.ylabel("综合贴近度得分", fontsize=12)
plt.grid(alpha=0.3)
plt.xticks(np.arange(0, 51, 5))
plt.tight_layout()
plt.savefig("TOP50供应商得分折线图.png", dpi=300)
plt.show()

print("\n程序运行完成，已生成两张折线图图片！")