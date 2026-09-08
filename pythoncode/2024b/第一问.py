import numpy as np
import matplotlib.pyplot as plt

# ====================== 1. 题目给定SPRT参数（按你原题） ======================
p0 = 0.05     # H0：可接受次品率
p1 = 0.20     # H1：不可接受次品率
alpha = 0.10  # 第一类错误
beta = 0.10   # 第二类错误

# Wald SPRT公式
A = (1 - beta) / alpha
B = beta / (1 - alpha)

# 边界线参数 h1, h2, k
logA = np.log(A)
logB = np.log(B)

log_term1 = np.log(p1 / p0)
log_term2 = np.log((1 - p1) / (1 - p0))

h1 = logA / (log_term1 - log_term2)
h2 = -logB / (log_term1 - log_term2)
k  = - log_term2 / (log_term1 - log_term2)

print("==== SPRT计算参数 ====")
print(f"A = {A:.4f}, B = {B:.4f}")
print(f"h1(拒收截距) = {h1:.4f}")
print(f"h2(接收截距) = {h2:.4f}")
print(f"k(斜率) = {k:.4f}")

# ====================== 2. 绘图（修复版！！！n从1开始，不是0） ======================
plt.rcParams["font.sans-serif"] = ["SimSun"]
plt.rcParams["axes.unicode_minus"] = False

n = np.linspace(1, 120, 500)   # ✅修复：起点n=1，不是0
r_reject = h1 + k * n          # 拒收边界（红线）
r_accept = -h2 + k * n         # 接收边界（蓝线）

plt.figure(figsize=(14,8), dpi=120)
plt.plot(n, r_reject, color='#c82423', linewidth=2.2, label="拒收边界")
plt.plot(n, r_accept, color='#1f77b4', linewidth=2.2, label="接收边界")

# 继续抽样填充区域
plt.fill_between(n, r_accept, r_reject, color="#e2e2e2", alpha=0.5, label="继续抽样区")

# X轴向左扩，看到向外延伸斜线效果
plt.xlim(-8, 120)
plt.ylim(-4, 22)

plt.xlabel("抽样件数 $n$", fontsize=12)
plt.ylabel("累计检出次品数 $r$", fontsize=12)
plt.title("图4 SPRT序贯概率比检验判定边界", fontsize=14)
plt.legend(loc="upper left", fontsize=11)
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("SPRT边界图.png", dpi=300)
plt.show()

# ======================3. SPRT模拟抽样函数（可选，仿真序贯停止过程） ======================
def sprt_simulate(true_p, max_n=500):
    """
    true_p:真实次品率
    返回：停止抽样数stop_n，累计次品r，判定结果:"接收H0"/"拒绝H0"/"未终止"
    """
    cum_r = 0
    for ni in range(1, max_n+1):
        xi = np.random.binomial(1, true_p)
        cum_r += xi
        upper = h1 + k * ni
        lower = -h2 + k * ni
        if cum_r >= upper:
            return ni, cum_r, "拒绝H0"
        elif cum_r <= lower:
            return ni, cum_r, "接收H0"
    return max_n, cum_r, "未终止"

# 简单仿真示例
np.random.seed(42)
stop_n, r_out, res = sprt_simulate(true_p=0.05)
print(f"\n仿真测试：真实次品率0.05，停止n={stop_n},次品数={r_out},结果:{res}")
stop_n2, r_out2, res2 = sprt_simulate(true_p=0.20)
print(f"仿真测试：真实次品率0.20，停止n={stop_n2},次品数={r_out2},结果:{res2}")
