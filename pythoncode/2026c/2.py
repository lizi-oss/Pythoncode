import pandas as pd
import numpy as np
import pulp
from pulp import LpProblem, LpVariable, LpMinimize, LpBinary, lpSum, value
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
STORAGE_INFO_FILE = os.path.join(BASE_DIR, "storage_information.xlsx")

gpu_df = pd.read_excel(GPU_FILE)
workload_df = pd.read_excel(WORKLOAD_FILE)
latency_df = pd.read_excel(LATENCY_FILE)
power_map_df = pd.read_excel(POWER_MAP_FILE)
region_time_df = pd.read_excel(REGION_TIME_FILE)
storage_info_df = pd.read_excel(STORAGE_INFO_FILE)

regions = ['RegionA', 'RegionB', 'RegionC', 'RegionD', 'RegionE', 'RegionF']
east_regions = {'RegionA', 'RegionB', 'RegionC'}
west_regions = {'RegionD', 'RegionE', 'RegionF'}

gpu_capacity = {row['Region']: row['Available_GPU'] for _, row in gpu_df.iterrows()}
pue_dict = {row['Region']: row['PUE'] for _, row in gpu_df.iterrows()}
max_it_power_ori = {row['Region']: row['Max_IT_Power_MW'] for _, row in gpu_df.iterrows()}
max_facility_power_ori = {row['Region']: row['Max_Facility_Power_MW'] for _, row in gpu_df.iterrows()}

power_scale = 1.3
max_it_power = {r: v*power_scale for r, v in max_it_power_ori.items()}
max_facility_power = {r: v*power_scale for r, v in max_facility_power_ori.items()}

latency_matrix = {}
for _, row in latency_df.iterrows():
    latency_matrix[(row['FromRegion'], row['ToRegion'])] = row['NetworkLatency_ms']

power_map = {row['TaskType']: row['GPU_Power_MW_per_EquivalentGPU'] for _, row in power_map_df.iterrows()}

stor_soc_init = {}
stor_soc_min = {}
stor_soc_max = {}
stor_pch_max = {}
stor_pdis_max = {}
stor_eta_ch = {}
stor_eta_dis = {}
sell_limit = {}
for _, row in storage_info_df.iterrows():
    r = row["Region"]
    stor_soc_init[r] = row["InitialSOC_MWh"]
    stor_soc_min[r] = row["MinSOC_MWh"]
    stor_soc_max[r] = row["StorageCapacity_MWh"]
    stor_pch_max[r] = row["MaxChargePower_MW"]
    stor_pdis_max[r] = row["MaxDischargePower_MW"]
    stor_eta_ch[r] = row["ChargeEfficiency"]
    stor_eta_dis[r] = row["DischargeEfficiency"]
    sell_limit[r] = row["SellLimit_MW"]

renewable = {}
elec_price = {}
sell_price = {}
carbon_intensity = {}
nonai_it_load = {}
for _, row in region_time_df.iterrows():
    t = int(row["Hour"])
    r = row["Region"]
    k = (r, t)
    renewable[k] = row["AvailableRenewable_MW"]
    elec_price[k] = row["ElectricityPrice_CNY_per_MWh"]
    sell_price[k] = row["SellPrice_CNY_per_MWh"]
    carbon_intensity[k] = row["CarbonIntensity_tCO2_per_MWh"]
    nonai_it_load[k] = row["NonAI_IT_Load_MW"]

ARRIVE_START = 2376
ARRIVE_END = 2399
FINISH_LIMIT = 2406
time_horizon = list(range(ARRIVE_START, FINISH_LIMIT))

mask = (workload_df["ArrivalHour"] >= ARRIVE_START) & (workload_df["ArrivalHour"] <= ARRIVE_END)
task_df = workload_df.loc[mask].copy().reset_index(drop=True)
task_df["DurationHour"] = task_df["EstimatedDuration_min"] / 60.0
print(f"【两阶段模型第一阶段：算力调度MILP，增加负荷‑新能源偏差惩罚】筛选任务数：{len(task_df)}")

base_schedule = pd.read_csv(os.path.join(BASE_DIR, "调度明细表.csv"), encoding="utf-8-sig")
base_avg_latency = base_schedule["Latency_ms"].mean()

def calc_carbon_from_schedule(schedule_df):
    total_c = 0.0
    for _, row in schedule_df.iterrows():
        r_assigned = row["AssignedRegion"]
        gpu_d = row["GPU_Demand"]
        tt = row["TaskType"]
        sh = row["StartHour"]
        eh = row["EndHour"]
        t_cur = sh
        while t_cur < eh:
            if t_cur >= FINISH_LIMIT:
                break
            t_next = min(np.floor(t_cur)+1, eh)
            ov = t_next - t_cur
            hk = int(np.floor(t_cur))
            fac_load = (nonai_it_load[(r_assigned, hk)] + gpu_d * ov * power_map[tt]) * pue_dict[r_assigned]
            ci = carbon_intensity[(r_assigned, hk)]
            total_c += fac_load * ov * ci
            t_cur = t_next
    return total_c

C_base = calc_carbon_from_schedule(base_schedule)
alpha = 1.1
latency_upper = alpha * base_avg_latency
lambda_penalty = 50.0
# =========【关键超参数：负荷‑新能源不匹配惩罚权重，可调】========
w_penalty_imbalance = 0.0008

print(f"基准平均时延 {base_avg_latency:.2f} ms；原时延理论上限 {latency_upper:.2f} ms")
print(f"基准总碳排放 C_base = {C_base:.2f} tCO2")
print(f"负荷‑新能源偏差惩罚权重 w_penalty_imbalance={w_penalty_imbalance}")

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

prob2 = LpProblem("Stage1_TaskSchedule_ImbalancePenalty", LpMinimize)

x = {}
for i in task_df.index:
    for (r, s) in feasible_irs[i]:
        x[(i, r, s)] = LpVariable(f"x_{i}_{r}_{s}", cat=LpBinary)

dev_pos = LpVariable.dicts("dev_pos", [(r,t) for r in regions for t in time_horizon], lowBound=0)
dev_neg = LpVariable.dicts("dev_neg", [(r,t) for r in regions for t in time_horizon], lowBound=0)

for i in task_df.index:
    prob2 += lpSum([x[(i, r, s)] for (r, s) in feasible_irs[i]]) == 1, f"assign_{i}"

for i, task in task_df.iterrows():
    if task["TaskType"] == "RealTimeInference":
        arr = task["ArrivalHour"]
        prob2 += lpSum([x[(i, r, s)] for (r, s) in feasible_irs[i] if s == arr]) == 1, f"rtstart_{i}"

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
        prob2 += lpSum(expr_gpu) <= gpu_capacity[r], f"gpu_{r}_{t}"

net_load_expr = {}
for t in time_horizon:
    for r in regions:
        expr_it = []
        for i in task_df.index:
            tt = task_df.loc[i, "TaskType"]
            gpu_d = task_df.loc[i, "GPU_Demand"]
            for (rr, s) in feasible_irs[i]:
                if rr != r: continue
                od = overlap_irs[i][(rr, s)]
                if t not in od: continue
                expr_it.append(gpu_d * od[t] * power_map[tt] * x[(i, rr, s)])
        it_total = nonai_it_load[(r, t)] + lpSum(expr_it)
        prob2 += it_total <= max_it_power[r], f"itlim_{r}_{t}"
        prob2 += it_total * pue_dict[r] <= max_facility_power[r], f"faclim_{r}_{t}"
        net_load_expr[(r, t)] = it_total * pue_dict[r]
        # 绝对值线性化 net_load_expr - renew = dev_pos - dev_neg
        prob2 += net_load_expr[(r,t)] - renewable[(r,t)] == dev_pos[(r,t)] - dev_neg[(r,t)]

penalty_delay = []
cost_est = []
imbalance_penalty_terms = []

for i, task in task_df.iterrows():
    arr_i = task["ArrivalHour"]
    for (r, s) in feasible_irs[i]:
        delay_h = s - arr_i
        penalty_delay.append(lambda_penalty * delay_h * x[(i, r, s)])

for r in regions:
    for t in time_horizon:
        cost_est.append(net_load_expr[(r,t)] * elec_price[(r,t)] * 1e-6)
        imbalance_penalty_terms.append( dev_pos[(r,t)] + dev_neg[(r,t)] )

obj = (lpSum(cost_est)
       + lpSum(penalty_delay)
       + w_penalty_imbalance * lpSum(imbalance_penalty_terms))
prob2 += obj

print("\n=====第一阶段求解：增加负荷‑新能源匹配惩罚 =====")
prob2.solve(pulp.PULP_CBC_CMD(msg=1, timeLimit=600, gapRel=0.08, threads=4))
solve_status = prob2.status
print(f"stage‑1 status={solve_status}, 1=可行")
if solve_status != 1:
    raise Exception("第一阶段算力调度无解")

schedule_records2 = []
region_gpu_used2 = {r: {t:0.0 for t in time_horizon} for r in regions}
facility_load_mat = {r:{t:0.0 for t in time_horizon} for r in regions}

for i in task_df.index:
    task = task_df.loc[i]
    sel_r = None
    sel_s = None
    sel_od = None
    for (r, s) in feasible_irs[i]:
        if value(x[(i, r, s)]) > 0.5:
            sel_r = r
            sel_s = s
            sel_od = overlap_irs[i][(r, s)]
            break
    if sel_r is None:
        raise Exception(f"任务{i}未分配")
    end_h = sel_s + task["DurationHour"]
    schedule_records2.append({
        "TaskID": task["TaskID"],
        "TaskType": task["TaskType"],
        "SourceRegion": task["SourceRegion"],
        "AssignedRegion": sel_r,
        "ArrivalHour": task["ArrivalHour"],
        "StartHour": sel_s,
        "EndHour": end_h,
        "EstimatedDuration_min": task["EstimatedDuration_min"],
        "GPU_Demand": task["GPU_Demand"],
        "MaxLatency_ms": task["MaxLatency_ms"],
        "Latency_ms": latency_matrix[(task["SourceRegion"], sel_r)],
        "SatisfyLatency": latency_matrix[(task["SourceRegion"], sel_r)] <= task["MaxLatency_ms"],
        "LatestFinishHour": task["LatestFinishHour"]
    })
    for t, ov in sel_od.items():
        region_gpu_used2[sel_r][t] += task["GPU_Demand"] * ov
        ai_it = task["GPU_Demand"] * ov * power_map[task["TaskType"]]
        total_it = nonai_it_load[(sel_r, t)] + ai_it
        facility_load_mat[sel_r][t] = total_it * pue_dict[sel_r]

schedule_df2 = pd.DataFrame(schedule_records2)
schedule_df2.to_csv(os.path.join(BASE_DIR, "调度明细表_问题二.csv"), index=False, encoding="utf-8-sig")
print(f"第一阶段调度完成，任务数 {len(schedule_df2)}")

util_result = {r:[] for r in regions}
for t in time_horizon:
    for r in regions:
        util = region_gpu_used2[r][t] / gpu_capacity[r] if gpu_capacity[r]>0 else 0.0
        util_result[r].append(util)

makespan2 = schedule_df2["EndHour"].max()
avg_lat2 = schedule_df2["Latency_ms"].mean()
migrate_df2 = schedule_df2[schedule_df2["SourceRegion"] != schedule_df2["AssignedRegion"]]
e2w=w2e=ein=win=0
for _,row in migrate_df2.iterrows():
    s,a = row["SourceRegion"], row["AssignedRegion"]
    if s in east_regions and a in west_regions: e2w+=1
    elif s in west_regions and a in east_regions: w2e+=1
    elif s in east_regions and a in east_regions: ein+=1
    else: win+=1

def run_power_sim(fac_load_mat):
    sim_res = {}
    debug_rows = []
    total_cost = 0.0
    total_carbon = 0.0
    total_renew_avail = 0.0
    total_renew_use = 0.0
    for r in regions:
        soc = stor_soc_init[r]
        sim_res[r] = []
        for t in time_horizon:
            ld = fac_load_mat[r][t]
            rn = renewable[(r, t)]
            total_renew_avail += rn
            P_buy = 0.0
            P_dis = 0.0
            P_ch = 0.0
            P_sell = 0.0
            P_curtail = 0.0
            net_demand = ld - rn
            if net_demand > 1e-9:
                discharge_need = net_demand
                P_dis = min(discharge_need, stor_pdis_max[r], soc * stor_eta_dis[r])
                soc = soc - P_dis / stor_eta_dis[r]
                remain_need = net_demand - P_dis
                if remain_need > 1e-9:
                    P_buy = remain_need
            else:
                surplus = -net_demand
                max_charge_energy = (stor_soc_max[r] - soc) / stor_eta_ch[r]
                P_ch = min(surplus, stor_pch_max[r], max_charge_energy)
                soc = soc + stor_eta_ch[r] * P_ch
                surplus_after_charge = surplus - P_ch
                P_sell = min(surplus_after_charge, sell_limit[r])
                P_curtail = max(0.0, surplus_after_charge - P_sell)
            cost = P_buy * elec_price[(r, t)] - P_sell * sell_price[(r, t)]
            total_cost += cost
            total_carbon += P_buy * carbon_intensity[(r, t)]
            direct_consume = max(0.0, rn - P_ch - P_sell - P_curtail)
            total_renew_use += (direct_consume + P_ch + P_sell)
            sim_res[r].append({"t":t,"Pbuy":P_buy,"Psell":P_sell,"Pcurtail":P_curtail,"Pch":P_ch,"Pdis":P_dis,"SOC":soc})
            debug_rows.append({"region":r,"t":t,"load_MW":ld,"renewable_MW":rn,"P_buy":P_buy,"P_sell":P_sell,"P_ch":P_ch,"P_dis":P_dis,"SOC":soc})
    pd.DataFrame(debug_rows).to_csv(os.path.join(BASE_DIR,"power_sim_debug.csv"),index=False,encoding="utf-8-sig")
    if total_renew_avail > 1e-6:
        ru = total_renew_use / total_renew_avail
    else:
        ru = 0.0
    return total_cost, total_carbon, ru, sim_res

opt_cost, opt_carbon, renew_util_rate, sim_out = run_power_sim(facility_load_mat)

summary_records = []
for r in regions:
    assign_cnt = len(schedule_df2[schedule_df2["AssignedRegion"]==r])
    gpu_sum = schedule_df2.loc[schedule_df2["AssignedRegion"]==r,"GPU_Demand"].sum()
    avg_u = np.mean(util_result[r])
    peak_u = np.max(util_result[r])
    summary_records.append({"区域":r,"分配任务数":assign_cnt,"GPU总需求":gpu_sum,"平均利用率":round(avg_u,4),"峰值利用率":round(peak_u,4)})
summary_df = pd.DataFrame(summary_records)
summary_df.to_csv(os.path.join(BASE_DIR,"调度汇总表_问题二.csv"),index=False,encoding="utf-8-sig")

ind_df = pd.DataFrame([
    {"指标":"最大完工时间(h)","数值":round(makespan2,2)},
    {"指标":"平均网络时延(ms)","数值":round(avg_lat2,2)},
    {"指标":"基准平均时延(ms)","数值":round(base_avg_latency,2)},
    {"指标":"仿真总运行成本(元)","数值":round(opt_cost,2)},
    {"指标":"仿真总碳排放(tCO2)","数值":round(opt_carbon,2)},
    {"指标":"基准总碳排放(tCO2)","数值":round(C_base,2)},
    {"指标":"新能源利用率","数值":round(renew_util_rate,4)},
    {"指标":"迁移总任务数","数值":len(migrate_df2)},
    {"指标":"东部→西部","数值":e2w},
    {"指标":"西部→东部","数值":w2e},
    {"指标":"东部内部迁移","数值":ein},
    {"指标":"西部内部迁移","数值":win}
])
ind_df.to_csv(os.path.join(BASE_DIR,"指标汇总_问题二.csv"),index=False,encoding="utf-8-sig")

print("\n========两阶段模型 指标汇总========")
print(ind_df.to_string(index=False))

plt.figure(figsize=(12,6))
for idx,r in enumerate(regions):
    plt.plot(time_horizon, util_result[r], label=r, color=ACADEMIC_COLORS[idx], linewidth=1.4, marker=".", markersize=3)
plt.xlabel("时刻(h)")
plt.ylabel("GPU利用率")
plt.title("各区域GPU利用率（问题二，增加新能源匹配惩罚）")
plt.legend(loc="upper right", fontsize=8)
plt.grid(alpha=0.3)
plt.xlim(ARRIVE_START, FINISH_LIMIT)
plt.tight_layout()
plt.savefig(os.path.join(BASE_DIR,"GPU利用率_问题二.png"),dpi=300,bbox_inches="tight")
plt.close()

plt.figure(figsize=(16,7))
region_ypos = {r:i for i,r in enumerate(regions)}
yticks_pos = list(range(len(regions)))
yticks_label = regions
cmap_task = {"RealTimeInference":COLOR_REALTIME,"BatchInference":COLOR_BATCH,"AITraining":COLOR_TRAIN}
for _,row in schedule_df2.iterrows():
    y = region_ypos[row["AssignedRegion"]]
    dur = row["EndHour"] - row["StartHour"]
    c = cmap_task.get(row["TaskType"], "#888888")
    plt.barh(y, dur, left=row["StartHour"], height=0.6, color=c, edgecolor="black", linewidth=0.4, alpha=0.85)
plt.yticks(yticks_pos, yticks_label)
plt.xlim(ARRIVE_START, FINISH_LIMIT)
plt.xlabel("时刻(h)")
plt.ylabel("区域")
plt.title("任务调度甘特图（问题二，增加新能源匹配惩罚）")
leg_items = [
    mpatches.Patch(color=COLOR_REALTIME, label="实时推理"),
    mpatches.Patch(color=COLOR_BATCH, label="批处理推理"),
    mpatches.Patch(color=COLOR_TRAIN, label="AI训练")
]
plt.legend(handles=leg_items, loc="upper right")
plt.grid(axis="x", alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(BASE_DIR,"甘特图_问题二.png"),dpi=300,bbox_inches="tight")
plt.close()

print("\n====输出文件清单====")
print("调度明细表_问题二.csv")
print("调度汇总表_问题二.csv")
print("指标汇总_问题二.csv")
print("power_sim_debug.csv（电力仿真调试）")
print("GPU利用率_问题二.png")
print("甘特图_问题二.png")
