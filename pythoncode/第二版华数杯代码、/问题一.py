import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ===================== 题目全局固定参数（严格匹配题意） =====================
BOX_MIN = -5000
BOX_MAX = 5000
BOX_LEN = 10000
LEFT_PLANE = -5000    # X左带电面
RIGHT_PLANE = 5000    # X右带电面
R_A = 30              # 介质A圆柱底面半径 nm
THRESH = 1.8          # 导通间隙阈值 nm
CYL_CNT_DIST = 2 * R_A + THRESH    # 两圆柱导通阈值 61.8
CYL_PLANE_DIST = R_A + THRESH      # 圆柱-极板导通阈值 31.8

# ===================== 【修复】标准有限三维线段最短距离函数 =====================
def seg_min_dist(a0, a1, b0, b1):
    """
    标准有限线段之间最短欧式距离
    解决原实现平行线段、参数s/t落在区间外的计算缺陷
    a0,a1: 线段A两个端点 tuple(x,y,z)
    b0,b1: 线段B两个端点 tuple(x,y,z)
    return: 最短轴线距离
    """
    def vec_sub(p, q):
        return (p[0]-q[0], p[1]-q[1], p[2]-q[2])
    def vec_dot(u, v):
        return u[0]*v[0] + u[1]*v[1] + u[2]*v[2]
    def vec_len_sq(u):
        return vec_dot(u, u)

    u = vec_sub(a1, a0)
    v = vec_sub(b1, b0)
    w = vec_sub(a0, b0)

    a = vec_len_sq(u)
    b = vec_dot(u, v)
    c = vec_len_sq(v)
    d = vec_dot(u, w)
    e = vec_dot(v, w)

    denom = a * c - b * b
    s, t = 0.0, 0.0
    eps = 1e-14

    if denom > eps:
        s = (b * e - c * d) / denom
        t = (a * e - b * d) / denom

    # clamp 参数到 [0,1]
    s = max(0.0, min(1.0, s))
    t = max(0.0, min(1.0, t))

    # 候选点：参数s,t处的点 + 四个端点
    def lerp(p0, p1, s_val):
        return (
            p0[0] + s_val*(p1[0]-p0[0]),
            p0[1] + s_val*(p1[1]-p0[1]),
            p0[2] + s_val*(p1[2]-p0[2])
        )
    p_candidate = lerp(a0, a1, s)
    q_candidate = lerp(b0, b1, t)

    candidates = [
        (p_candidate, q_candidate),
        (a0, b0),
        (a0, b1),
        (a1, b0),
        (a1, b1)
    ]
    min_d = float("inf")
    for p, q in candidates:
        dx = p[0]-q[0]
        dy = p[1]-q[1]
        dz = p[2]-q[2]
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)
        if dist < min_d:
            min_d = dist
    return min_d

# ===================== 并查集（完整保留，无修改） =====================
class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        self.size = [1] * n
    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]
    def union(self, a, b):
        ra = self.find(a)
        rb = self.find(b)
        if ra == rb:
            return False
        if self.size[ra] < self.size[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]
        return True

# ===================== 边界检查：仅告警，不修改坐标 =====================
def check_cylinder_in_box(p0, p1):
    """检查圆柱端点是否超出[-5000,5000]，只打印告警，不做平移截断"""
    out_flag = False
    for pt in [p0, p1]:
        for coord in pt:
            if not (BOX_MIN - 1e-9 <= coord <= BOX_MAX + 1e-9):
                out_flag = True
                break
    return out_flag

# ===================== 读取Excel原始圆柱数据（无坐标平移/截断） =====================
def read_raw_cylinders(file_path, sheet_name):
    """直接读取Excel原始顶点坐标，不做任何周期平移、分段、边界截断"""
    try:
        df = pd.read_excel(file_path, sheet_name)
        # 单层表头匹配 X1,Y1,Z1,X2,Y2,Z2
        col_map = {
            "X1": "X1", "顶点1 X": "X1",
            "Y1": "Y1", "顶点1 Y": "Y1",
            "Z1": "Z1", "顶点1 Z": "Z1",
            "X2": "X2", "顶点2 X": "X2",
            "Y2": "Y2", "顶点2 Y": "Y2",
            "Z2": "Z2", "顶点2 Z": "Z2",
        }
        df = df.rename(columns=col_map)
        x1 = df["X1"].values
        y1 = df["Y1"].values
        z1 = df["Z1"].values
        x2 = df["X2"].values
        y2 = df["X2"].values
        z2 = df["Z2"].values
    except Exception:
        # 双层表头兼容
        df = pd.read_excel(file_path, sheet_name, header=[0,1])
        x1 = df[("顶点1", "X")].values
        y1 = df[("顶点1", "Y")].values
        z1 = df[("顶点1", "Z")].values
        x2 = df[("顶点2", "X")].values
        y2 = df[("顶点2", "Y")].values
        z2 = df[("顶点2", "Z")].values

    cylinders = []
    warn_out_count = 0
    for i in range(len(x1)):
        p0 = (float(x1[i]), float(y1[i]), float(z1[i]))
        p1 = (float(x2[i]), float(y2[i]), float(z2[i]))
        cylinders.append((p0, p1))
        if check_cylinder_in_box(p0,p1):
            warn_out_count +=1
    if warn_out_count>0:
        print(f"⚠️ sheet[{sheet_name}] 存在 {warn_out_count} 根圆柱端点超出盒子[-5000,5000]，程序保持原始坐标不做处理")
    return cylinders

# ===================== 修正：单根圆柱到极板最小轴线距离计算 =====================
def cyl_to_plane_axis_dist(p0, p1, plane_x):
    """
    圆柱线段端点(p0,p1)到X=plane_x平面的轴线最小距离
    逻辑：线段X区间跨平面 → 距离0；否则取两端X最小差值
    """
    x0, _, _ = p0
    x1, _, _ = p1
    x_min_seg = min(x0, x1)
    x_max_seg = max(x0, x1)
    if x_min_seg <= plane_x <= x_max_seg:
        return 0.0
    return min(abs(x0 - plane_x), abs(x1 - plane_x))

# ===================== 单组微构导通判定核心函数 =====================
def judge_single_group(file_path, sheet_name):
    # 1. 读取原始圆柱，无坐标预处理
    cyls = read_raw_cylinders(file_path, sheet_name)
    N = len(cyls)
    if N == 0:
        return {"微构分组": sheet_name,
                "圆柱介质总数": 0,
                "连通边数量":0,
                "接触左极板介质数": 0,
                "接触右极板介质数": 0,
                "是否导通": False,
                "cylinders": cyls,
                "uf": None,
                "touch_left": set(),
                "touch_right": set(),
                "dist_left_list": [],
                "dist_right_list": []}

    # 2. 初始化并查集，两两判断圆柱连通并合并
    uf = UnionFind(N)
    connect_edge_cnt = 0
    for i in range(N):
        a0, a1 = cyls[i]
        for j in range(i+1, N):
            b0, b1 = cyls[j]
            d_axis = seg_min_dist(a0, a1, b0, b1)
            if d_axis <= CYL_CNT_DIST:
                ok = uf.union(i, j)
                if ok:
                    connect_edge_cnt +=1

    # 3. 筛选分别连通左、右极板的介质下标，同时存储距离用于绘图
    touch_left = set()
    touch_right = set()
    dist_left_list = []
    dist_right_list = []
    for idx, (p0, p1) in enumerate(cyls):
        d_l = cyl_to_plane_axis_dist(p0, p1, LEFT_PLANE)
        d_r = cyl_to_plane_axis_dist(p0, p1, RIGHT_PLANE)
        dist_left_list.append(d_l)
        dist_right_list.append(d_r)
        if d_l <= CYL_PLANE_DIST:
            touch_left.add(idx)
        if d_r <= CYL_PLANE_DIST:
            touch_right.add(idx)

    # 4. 判断是否存在连通通路：左极板介质与右极板介质同属一个连通簇
    is_conduct = False
    for l_idx in touch_left:
        root_l = uf.find(l_idx)
        for r_idx in touch_right:
            root_r = uf.find(r_idx)
            if root_l == root_r:
                is_conduct = True
                break
        if is_conduct:
            break

    return {
        "微构分组": sheet_name,
        "圆柱介质总数": N,
        "连通边数量": connect_edge_cnt,
        "接触左极板介质数": len(touch_left),
        "接触右极板介质数": len(touch_right),
        "是否导通": is_conduct,
        "cylinders": cyls,
        "uf": uf,
        "touch_left": touch_left,
        "touch_right": touch_right,
        "dist_left_list": dist_left_list,
        "dist_right_list": dist_right_list
    }

# ===================== 【绘图全局配置 国赛标准】 =====================
plt.rcParams["font.family"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['axes.labelweight'] = 'medium'
plt.rcParams['font.size'] = 9

# ===================== 原有三张基础绘图函数（不变） =====================
def draw_fig1_space_distribute(res):
    """图1：单组样本介质空间总分布（建模样本展示）"""
    fig = plt.figure(figsize=(10,7))
    ax = fig.add_subplot(111, projection='3d')
    cyls = res["cylinders"]
    left_idx = res["touch_left"]
    right_idx = res["touch_right"]
    for idx, (p0,p1) in enumerate(cyls):
        x = [p0[0], p1[0]]
        y = [p0[1], p1[1]]
        z = [p0[2], p1[2]]
        if idx in left_idx and idx in right_idx:
            ax.plot(x,y,z, c="#00264d", lw=1.8, label="同时接触两极板" if idx==list(left_idx)[0] else "")
        elif idx in left_idx:
            ax.plot(x,y,z, c="#003366", lw=1.4, label="接触左极板介质" if idx==list(left_idx)[0] else "")
        elif idx in right_idx:
            ax.plot(x,y,z, c="#4d0000", lw=1.4, label="接触右极板介质" if idx==list(right_idx)[0] else "")
        else:
            ax.plot(x,y,z, c="#666666", lw=0.7)
    # 绘制带电平面
    y_mesh, z_mesh = np.meshgrid([BOX_MIN, BOX_MAX], [BOX_MIN, BOX_MAX])
    x_left = np.full_like(y_mesh, LEFT_PLANE)
    x_right = np.full_like(y_mesh, RIGHT_PLANE)
    ax.plot_surface(x_left, y_mesh, z_mesh, alpha=0.12, color="#336699", shade=False)
    ax.plot_surface(x_right, y_mesh, z_mesh, alpha=0.12, color="#993333", shade=False)
    ax.set_xlim(BOX_MIN, BOX_MAX)
    ax.set_ylim(BOX_MIN, BOX_MAX)
    ax.set_zlim(BOX_MIN, BOX_MAX)
    ax.set_xlabel("X 坐标轴 (nm)")
    ax.set_ylabel("Y 坐标轴 (nm)")
    ax.set_zlabel("Z 坐标轴 (nm)")
    ax.legend(loc="upper right")
    plt.figtext(0.5, 0.01, "图1 微构体内全部导电介质A三维空间分布（样本）", ha="center", fontsize=11)
    plt.tight_layout()
    plt.savefig("图1.png", bbox_inches="tight", pad_inches=0.08)
    plt.close()
    print("已保存：图1.png")

def draw_fig2_cluster_scatter(res):
    """图2：连通簇规模散点图（模型求解网络维度）"""
    uf = res["uf"]
    if uf is None:
        return
    root_size = {}
    for i in range(len(res["cylinders"])):
        r = uf.find(i)
        if r not in root_size:
            root_size[r] = 0
        root_size[r] += 1
    connect_root = set()
    for l in res["touch_left"]:
        rl = uf.find(l)
        for r in res["touch_right"]:
            rr = uf.find(r)
            if rl == rr:
                connect_root.add(rl)
                break
    cluster_ids = list(root_size.keys())
    cluster_sizes = [root_size[cid] for cid in cluster_ids]
    color_list = ["#002040" if c in connect_root else "#606060" for c in cluster_ids]
    fig, ax = plt.subplots(figsize=(9,5))
    ax.scatter(cluster_ids, cluster_sizes, c=color_list, s=45, alpha=0.85)
    if len(connect_root) > 0:
        ax.scatter([], [], c="#002040", label="跨极板导通连通簇")
    ax.scatter([], [], c="#606060", label="孤立/未导通连通簇")
    ax.legend()
    ax.set_xlabel("连通簇编号")
    ax.set_ylabel("簇内介质A数量（根）")
    ax.grid(alpha=0.3, linestyle="--")
    plt.figtext(0.5, 0.01, "图2 导电介质连通簇规模分布散点图", ha="center", fontsize=11)
    plt.tight_layout()
    plt.savefig("图2.png", bbox_inches="tight", pad_inches=0.08)
    plt.close()
    print("已保存：图2.png")

def draw_fig3_plane_distance_scatter(res):
    """图3：介质到两极板轴线距离散点图（结果验证维度）"""
    dl = res["dist_left_list"]
    dr = res["dist_right_list"]
    fig, ax = plt.subplots(figsize=(9,5))
    ax.scatter(dl, dr, c="#203050", s=30, alpha=0.7)
    ax.axvline(x=CYL_PLANE_DIST, c="#800000", lw=1.2, ls="--", label="左极板导通阈值31.8 nm")
    ax.axhline(y=CYL_PLANE_DIST, c="#004020", lw=1.2, ls="--", label="右极板导通阈值31.8 nm")
    ax.set_xlabel("介质轴线到左带电面最小距离 (nm)")
    ax.set_ylabel("介质轴线到右带电面最小距离 (nm)")
    ax.legend()
    ax.grid(alpha=0.3, linestyle="--")
    plt.figtext(0.5, 0.01, "图3 全部介质到左右带电面轴线距离分布", ha="center", fontsize=11)
    plt.tight_layout()
    plt.savefig("图3.png", bbox_inches="tight", pad_inches=0.08)
    plt.close()
    print("已保存：图3.png")

# ===================== 【新增：三组独立微结构3D可视化绘图函数】 =====================
def draw_single_group_3d(res, fig_num, group_name):
    """
    单独绘制一组微构3D图，每张独立画布
    :param res: judge_single_group返回的结果字典
    :param fig_num: 图片编号（4/5/6）
    :param group_name: 分组名称（组1/组2/组3）
    """
    fig = plt.figure(figsize=(10,7))
    ax = fig.add_subplot(111, projection='3d')
    cyls = res["cylinders"]
    left_idx = res["touch_left"]
    right_idx = res["touch_right"]
    conduct_flag = res["是否导通"]

    # 绘制所有介质圆柱，分类配色
    for idx, (p0,p1) in enumerate(cyls):
        x = [p0[0], p1[0]]
        y = [p0[1], p1[1]]
        z = [p0[2], p1[2]]
        if idx in left_idx and idx in right_idx:
            ax.plot(x,y,z, c="#00264d", lw=1.8)
        elif idx in left_idx:
            ax.plot(x,y,z, c="#003366", lw=1.4)
        elif idx in right_idx:
            ax.plot(x,y,z, c="#4d0000", lw=1.4)
        else:
            ax.plot(x,y,z, c="#666666", lw=0.7)

    # 绘制左右半透明带电平面
    y_mesh, z_mesh = np.meshgrid([BOX_MIN, BOX_MAX], [BOX_MIN, BOX_MAX])
    x_left = np.full_like(y_mesh, LEFT_PLANE)
    x_right = np.full_like(y_mesh, RIGHT_PLANE)
    ax.plot_surface(x_left, y_mesh, z_mesh, alpha=0.12, color="#336699", shade=False)
    ax.plot_surface(x_right, y_mesh, z_mesh, alpha=0.12, color="#993333", shade=False)

    # 坐标轴设置
    ax.set_xlim(BOX_MIN, BOX_MAX)
    ax.set_ylim(BOX_MIN, BOX_MAX)
    ax.set_zlim(BOX_MIN, BOX_MAX)
    ax.set_xlabel("X (nm)")
    ax.set_ylabel("Y (nm)")
    ax.set_zlabel("Z (nm)")
    ax.grid(alpha=0.2)

    # 底部居中标题（国赛规范）
    status_text = "导通" if conduct_flag else "不导通"
    title_str = f"图{fig_num} {group_name}微构体内导电介质三维空间分布，判定结果：{status_text}"
    plt.figtext(0.5, 0.01, title_str, ha="center", fontsize=11)

    # 独立保存图片
    save_name = f"图{fig_num}.png"
    plt.tight_layout()
    plt.savefig(save_name, bbox_inches="tight", pad_inches=0.08)
    plt.close()
    print(f"已保存：{save_name}")

# ===================== 程序入口（仅处理3组固定数据，无随机/蒙特卡洛） =====================
if __name__ == "__main__":
    excel_path = r"D:\Documents\Pythoncode\pythoncode\第二版华数杯代码、\华数杯附件(1).xlsx"
    # 先读取Excel查看sheet
    try:
        excel_file = pd.ExcelFile(excel_path)
        print("==== Excel全部工作表 ====")
        print(excel_file.sheet_names)
        print("=========================\n")
    except FileNotFoundError:
        print("文件路径不存在，请修改excel_path为真实文件位置！")
        exit()

    # 修正：工作表名称与打印结果完全匹配
    sheet_list = ["组1", "组2", "组3"]
    all_result = []
    for sheet in sheet_list:
        print(f"==== 开始计算 {sheet} ====")
        res = judge_single_group(excel_path, sheet)
        # 计算最大连通簇规模
        uf = res["uf"]
        max_cluster = 0
        if uf is not None:
            root_size = {}
            for i in range(res["圆柱介质总数"]):
                r = uf.find(i)
                root_size[r] = root_size.get(r, 0) + 1
            max_cluster = max(root_size.values()) if root_size else 0
        res["最大连通簇规模"] = max_cluster
        all_result.append(res)
        # 精简控制台单组输出
        print(f"读取圆柱总数：{res['圆柱介质总数']} | 有效介质数量：{res['圆柱介质总数']}")
        print(f"接触左极板：{res['接触左极板介质数']} | 接触右极板：{res['接触右极板介质数']}")
        print(f"连通配对：{res['连通边数量']} | 最大连通簇：{max_cluster} | 导通：{res['是否导通']}\n")

    # 生成三张基础分析图 + 三组独立3D图
    sample_res = all_result[0]
    draw_fig1_space_distribute(sample_res)
    draw_fig2_cluster_scatter(sample_res)
    draw_fig3_plane_distance_scatter(sample_res)
    fig_id = 4
    for idx, res_data in enumerate(all_result):
        draw_single_group_3d(res_data, fig_id, sheet_list[idx])
        fig_id += 1

    # 打印指定格式Markdown汇总表（无过滤异常轴线列）
    print("========== 三组微构导通判定汇总 ==========")
    print("| 微构分组 | 读取圆柱总数 | 有效介质数量 | 接触左极板介质 | 接触右极板介质 | 介质连通配对数 | 最大连通簇规模 | 微构导通判定 |")
    print("| --- | --- | --- | --- | --- | --- | --- |")
    for item in all_result:
        cond_text = "导通" if item["是否导通"] else "不导通"
        print(f"| {item['微构分组']} | {item['圆柱介质总数']} | {item['圆柱介质总数']} | {item['接触左极板介质数']} | {item['接触右极板介质数']} | {item['连通边数量']} | {item['最大连通簇规模']} | {cond_text} |")

    # 导出Excel，表头严格匹配要求
    output_data = []
    for d in all_result:
        row = {
            "微构分组": d["微构分组"],
            "读取圆柱总数": d["圆柱介质总数"],
            "有效介质数量": d["圆柱介质总数"],
            "接触左极板介质": d["接触左极板介质数"],
            "接触右极板介质": d["接触右极板介质数"],
            "介质连通配对数": d["连通边数量"],
            "最大连通簇规模": d["最大连通簇规模"],
            "微构导通判定": "导通" if d["是否导通"] else "不导通"
        }
        output_data.append(row)
    pd.DataFrame(output_data).to_excel("问题一_导通判定汇总.xlsx", index=False)
    print("\n判定结果已导出：问题一_导通判定汇总.xlsx")
    print("全部6张可视化图片生成完成：图1.png、图2.png、图3.png、图4.png、图5.png、图6.png")