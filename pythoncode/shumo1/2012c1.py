import pandas as pd
import numpy as np

# ==============================
# 1. 读取数据
# ==============================

file = "附件1 近5年402家供应商的相关数据.xlsx"

order = pd.read_excel(
    file,
    sheet_name=0
)

supply = pd.read_excel(
    file,
    sheet_name=1
)


print("订货数据：")
print(order.head())

print("供货数据：")
print(supply.head())

# ==============================
# 2. 数据清洗
# ==============================

# 缺失值处理
order = order.fillna(0)
supply = supply.fillna(0)


# 取240周数据
week_cols = order.columns[2:]


order_week = order[week_cols].astype(float)
supply_week = supply[week_cols].astype(float)


# 删除异常负值
order_week[order_week < 0] = 0
supply_week[supply_week < 0] = 0


# ==============================
# 3. 构造供应商评价指标
# ==============================

data = pd.DataFrame()

data["供应商"] = supply.iloc[:,0]

data["材料类别"] = supply.iloc[:,1]

# ----------指标1：总供货量----------

data["总供货量"] = supply_week.sum(axis=1)


# ----------指标2：平均供货量----------

data["平均供货量"] = supply_week.mean(axis=1)


# ----------指标3：供货次数----------

data["供货次数"] = (
    supply_week > 0
).sum(axis=1)


# ----------指标4：平均履约率----------

ratio = supply_week / order_week.replace(0,np.nan)

data["履约率"] = ratio.mean(axis=1)

data["履约率"] = data["履约率"].fillna(0)


# ----------指标5：供货稳定性----------

std = supply_week.std(axis=1)

mean = supply_week.mean(axis=1)


data["变异系数"] = std / mean.replace(0,np.nan)

data["变异系数"] = data["变异系数"].fillna(0)


# ----------指标6：供货满足率----------

mask = order_week > 0


success = (
    supply_week >= order_week
) & mask


data["满足率"] = (
    success.sum(axis=1)
    /
    mask.sum(axis=1)
)


data["满足率"] = data["满足率"].fillna(0)



# ==============================
# 4. 材料类别价格因素修正
# ==============================

# A成本最高，重要性略提升

category_weight = {
    "A":1.2,
    "B":1.1,
    "C":1.0
}


data["材料权重"] = (
    data["材料类别"]
    .map(category_weight)
)


# 增加材料因素

data["总供货量"] *= data["材料权重"]



# 删除无关列

X = data[
[
"总供货量",
"平均供货量",
"供货次数",
"履约率",
"变异系数",
"满足率"
]
]



# ==============================
# 5. 数据标准化
# ==============================

# 正向指标
positive = [
0,1,2,3,5
]


# 负向指标
negative = [
4
]


Z = X.copy().astype(float)


# 正向处理

for i in positive:

    Z.iloc[:,i] = (
        Z.iloc[:,i]
        -
        Z.iloc[:,i].min()
    ) / (
        Z.iloc[:,i].max()
        -
        Z.iloc[:,i].min()
        +
        1e-12
    )


# 负向处理

for i in negative:

    Z.iloc[:,i] = (
        Z.iloc[:,i].max()
        -
        Z.iloc[:,i]
    ) / (
        Z.iloc[:,i].max()
        -
        Z.iloc[:,i].min()
        +
        1e-12
    )



# ==============================
# 6. 熵权法
# ==============================


P = Z / Z.sum(axis=0)


P = P.replace(
    0,
    1e-12
)


n = len(Z)


k = 1 / np.log(n)


entropy = (
    -k *
    (P*np.log(P)).sum(axis=0)
)


weight = (
    1-entropy
)


weight = (
    weight /
    weight.sum()
)


# ==========================================================
# 输出熵值和指标权重
# ==========================================================


print("\n======================")
print("指标熵值")
print("======================")


for name,e in zip(
    X.columns,
    E
):
    print(
        name,
        round(e,6)
    )



print("\n======================")
print("指标权重")
print("======================")


for name,w in zip(
    X.columns,
    W
):
    print(
        name,
        round(w,6)
    )

# 保存熵权结果表

weight_table = pd.DataFrame({

    "评价指标": X.columns,

    "熵值": E,

    "权重": W

})


weight_table.to_excel(
    "熵权法指标权重结果.xlsx",
    index=False
)

# ==============================
# 7. TOPSIS评价
# ==============================


V = Z * weight.values



# 正理想解

best = V.max(axis=0)


# 负理想解

worst = V.min(axis=0)



# 距离

D_plus = np.sqrt(
    ((V-best)**2).sum(axis=1)
)


D_minus = np.sqrt(
    ((V-worst)**2).sum(axis=1)
)



# 综合得分

score = (
    D_minus /
    (D_plus+D_minus)
)


data["综合得分"] = score



# ==============================
# 8. 排序取前50
# ==============================


result = (
    data
    .sort_values(
        by="综合得分",
        ascending=False
    )
)


top50 = result.head(50)



print("\n前50重要供应商")

print(
    top50[
    [
    "供应商",
    "材料类别",
    "综合得分"
    ]
    ]
)



# ==============================
# 9. 保存结果
# ==============================


data.to_excel(
    "全部供应商评价结果.xlsx",
    index=False
)


top50.to_excel(
    "最重要50家供应商.xlsx",
    index=False
)


print("\n运行完成！")