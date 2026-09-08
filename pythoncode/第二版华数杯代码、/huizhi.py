import numpy as np
import matplotlib.pyplot as plt

# 基础中文设置
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

width_list = [0.1500, 0.0750, 0.0375, 0.0188, 0.0094]
iter_idx = np.arange(1, len(width_list)+1)

fig2, ax2 = plt.subplots(figsize=(9, 5.5))
ax2.plot(iter_idx, width_list, 'o-', color="#d62728", markersize=7)
ax2.axhline(y=0.01, color='blue', linestyle='--', label="收敛精度0.01")

ax2.set_yscale("log")
# 手动纯小数刻度，不用10^-x指数写法
ax2.set_yticks([0.001, 0.01, 0.1])
ax2.set_yticklabels(["0.001", "0.01", "0.1"])

ax2.set_xlabel("迭代次数", fontsize=11)
ax2.set_xticks([1, 2, 3, 4, 5])
ax2.set_ylabel("区间宽度 (%)", fontsize=11)
ax2.set_title("二分收敛过程", fontsize=13)

ax2.legend(loc="upper right")
# 关键：关闭网格，消除内部负号字符，不再弹出警告
ax2.grid(False)

plt.tight_layout()
plt.savefig("fig2_二分收敛过程.png", dpi=300, bbox_inches="tight")
plt.close(fig2)
print("图片二已生成：fig2_二分收敛过程.png")