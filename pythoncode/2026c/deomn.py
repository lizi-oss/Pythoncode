import pandas as pd
import numpy as np
import pulp
from pulp import LpProblem, LpVariable, LpMinimize, LpBinary, LpContinuous, lpSum, value
import os
import warnings
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
warnings.filterwarnings("ignore")

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.dpi'] = 300

ACADEMIC_COLORS = ['#0072BD', '#D95319', '#EDB120', '#7E2F8E', '#77AC30', '#4DBEEE']
COLOR_REALTIME = '#D95319'
COLOR_BATCH = '#00897B'
COLOR_TRAIN = '#3949AB'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

GPU_FILE = os.path.join(BASE_DIR, "GPU_information.xlsx")
WORKLOAD_FILE = os.path.join(BASE_DIR, "workload_trace.xlsx")
LATENCY_FILE = os.path.join(BASE_DIR, "network_latency.xlsx")
POWER_MAP_FILE = os.path.join(BASE_DIR, "power_mapping.xlsx")
REGION_TIME_FILE = os.path.join(BASE_DIR, "region_time_data.xlsx")

gpu_df = pd.read_excel(GPU_FILE)
workload_df = pd.read_excel(WORKLOAD_FILE)
latency_df = pd.read_excel(LATENCY_FILE)
power_map_df = pd.read_excel(POWER_MAP_FILE)
region_time_df = pd.read_excel(REGION_TIME_FILE)

regions = ['RegionA', 'RegionB', 'RegionC', 'RegionD', 'RegionE', 'RegionF']
east_regions = {'RegionA', 'RegionB', 'RegionC'}
west_regions = {'RegionD', 'RegionE', 'RegionF'}

gpu_capacity = {row['Region']: row['Available_GPU'] for _, row in gpu_df.iterrows()}

latency_matrix = {}
for _, row in latency_df.iterrows():
    latency_matrix[(row['FromRegion'], row['ToRegion'])] = row['NetworkLatency_ms']

ARRIVE_START = 2376
ARRIVE_END = 2399
FINISH_LIMIT = 2406
time_horizon = list(range(ARRIVE_START, FINISH_LIMIT))

mask = (workload_df["ArrivalHour"] >= ARRIVE_START) & (workload_df["ArrivalHour"] <= ARRIVE_END)
task_df = workload_df.loc[mask].copy().reset_index(drop=True)
task_df["DurationHour"] = task_df["EstimatedDuration_min"] / 60.0
print(f"【调试模式，仅GPU+任务调度】筛选任务数：{len(task_df)}")

feasible_irs = dict()
overlap_irs = dict()
for i, task in task_df.iterrows():
    src_r = task["SourceRegion"]
    arr_t = task["ArrivalHour"]
    max_lat = task["MaxLatency_ms"]
    dur_h = task["DurationHour"]
    feasible_irs[i] = []
    overlap_irs[i] = dict()
    for r in regions:
        lat = latency_matrix[(src_r, r)]
        if lat > max_lat:
            continue
        for s in time_horizon:
            if s < arr_t:
                continue
            if s + dur_h > FINISH_LIMIT:
                continue
            feasible_irs[i].append((r, s))
            od = {}
            tc = s
            end_t = s + dur_h
            while tc < end_t:
                if tc >= FINISH_LIMIT:
                    break
                tn = min(np.floor(tc)+1, end_t)
                ov = tn - tc
                od[int(np.floor(tc))] = ov
                tc = tn
            overlap_irs[i][(r, s)] = od

prob2 = LpProblem("DebugOnlyGpu", LpMinimize)
M_POWER = 10000.0

x = {}
for i in task_df.index:
    for (r, s) in feasible_irs[i]:
        x[(i, r, s)] = LpVariable(f"x_{i}_{r}_{s}", cat=LpBinary)

# 每个任务选一组(r,s)
for i in task_df.index:
    prob2 += lpSum([x[(i, r, s)] for (r, s) in feasible_irs[i]]) == 1

# 实时推理必须到达立刻开工
for i, task in task_df.iterrows():
    if task["TaskType"] == "RealTimeInference":
        arr = task["ArrivalHour"]
        prob2 += lpSum([x[(i, r, s)] for (r, s) in feasible_irs[i] if s == arr]) == 1

# GPU容量约束
for t in time_horizon:
    for r in regions:
        expr_gpu = []
        for i in task_df.index:
            gpu_d = task_df.loc[i, "GPU_Demand"]
            for (rr, s) in feasible_irs[i]:
                if rr != r: continue
                od = overlap_irs[i][(rr, s)]
                if t not in od: continue
                expr_gpu.append(gpu_d * od[t] * x[(i, rr, s)])
        prob2 += lpSum(expr_gpu) <= gpu_capacity[r]

# 虚拟目标：0，只求可行解
prob2 += 0

print("\n=====调试：仅GPU+任务调度，无电力无功率上限=====")
prob2.solve(pulp.PULP_CBC_CMD(msg=1, timeLimit=300, gapRel=0.1, threads=4))
solve_status = prob2.status
print(f"status={solve_status}, 1=可行")

if solve_status == 1:
    print("✅【结论】仅GPU+任务调度是可行的，不可行根源在 IT/设施功率 或者电力‑储能约束")
else:
    print("❌【结论】GPU‑任务调度本身就不可行，任务/时延/GPU资源层面矛盾")
