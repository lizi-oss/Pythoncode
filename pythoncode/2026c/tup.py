import matplotlib.pyplot as plt
import numpy as np

# ===================== 绘图全局配置（只针对这两张图）=====================
plt.rcParams['font.sans-serif'] = ['SimSun']   # 宋体，国赛论文
plt.rcParams['axes.unicode_minus'] = False     # 修复负号显示
plt.rcParams['figure.dpi'] = 100

# ========== 图1：任务调度甘特图 =====================
fig1, ax1 = plt.subplots(figsize=(16, 8))

# --------------------------
# 这里保留你自己原来画甘特图的业务代码
# for ...:
#     ax1.broken_barh(......)
# --------------------------

ax1.set_title("最后 24 小时任务调度甘特图（第 2376-2405 小时）", fontsize=14)
ax1.set_xlabel("时间（小时）", fontsize=12)
ax1.set_ylabel("区域", fontsize=12)
ax1.grid(alpha=0.3, linestyle="--")

# 保存图片
plt.tight_layout()
plt.savefig("gantt_fig.png", dpi=300, bbox_inches="tight")
plt.close(fig1)


# ========== 图2：各区域GPU利用率变化曲线 =====================
fig2, ax2 = plt.subplots(figsize=(16, 8))

# --------------------------
# 这里保留你原来画利用率曲线的业务代码
# for region_idx in range(6):
#     ax2.plot(time_axis, util_data[region_idx], label=f"Region{chr(ord('A')+region_idx)}")
# --------------------------

ax2.set_title("各区域 GPU 利用率变化曲线（第 2376-2405 小时）", fontsize=14)
ax2.set_xlabel("时间（小时）", fontsize=12)
ax2.set_ylabel("GPU 利用率", fontsize=12)
ax2.legend(loc="upper right")
ax2.grid(alpha=0.3, linestyle="--")

plt.tight_layout()
plt.savefig("util_fig.png", dpi=300, bbox_inches="tight")
plt.close(fig2)


# ========== 图3：六张子图 GPU预测对比（修复重复“小时”） =====================
fig3, axes = plt.subplots(2, 3, figsize=(18, 10))
axes = axes.flatten()

# --------------------------
# 【重点】删除循环内部每一处 axes[i].set_xlabel("小时")！！
# for i in range(6):
#     axes[i].plot(......)
#     axes[i].set_title(f"Region{xxx} GPU需求预测对比")
# --------------------------

# 全部子图绘制完成后，只设置一次全局坐标轴
fig3.supxlabel("小时", fontsize=13)
fig3.supylabel("GPU需求", fontsize=13)

plt.tight_layout()
plt.savefig("predict_fig.png", dpi=300, bbox_inches="tight")
plt.close(fig3)

print("三张图片已输出，标题不再出现方框方块")
