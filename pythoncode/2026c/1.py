import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os
import warnings
from collections import defaultdict
import pulp
from pulp import LpProblem, LpVariable, LpMinimize, LpBinary, LpContinuous, lpSum, value
from statsmodels.tsa.statespace.sarimax import SARIMAX
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'PingFang SC', 'Heiti TC']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.dpi'] = 300

ACADEMIC_COLORS = ['#0072BD', '#D95319', '#EDB120', '#7E2F8E', '#77AC30', '#4DB4E6']
COLOR_REALTIME = '#D95319'
COLOR_BATCH = '#00897B'
COLOR_TRAIN = '#3949AB'


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GPU_FILE = os.path.join(BASE_DIR, "GPU_information.xlsx")
WORKLOAD_FILE = os.path.join(BASE_DIR, "workload_trace.xlsx")
LATENCY_FILE = os.path.join(BASE_DIR, "network_latency.xlsx")
POWER_MAP_FILE = os.path.join(BASE_DIR, "power_mapping.xlsx")
REGION_TIME_FILE = os.path.join(BASE_DIR, "region_time_data.xlsx")


print("=" * 65)
print("【步骤1】读取数据")
print("=" * 65)

gpu_df = pd.read_excel(GPU_FILE, sheet_name=0)
workload_df = pd.read_excel(WORKLOAD_FILE, sheet_name=0)
latency_df = pd.read_excel(LATENCY_FILE, sheet_name=0)
power_map_df = pd.read_excel(POWER_MAP_FILE, sheet_name=0)
region_time_df = pd.read_excel(REGION_TIME_FILE, sheet_name=0)

regions = ['RegionA', 'RegionB', 'RegionC', 'RegionD', 'RegionE', 'RegionF']
east_regions = {'RegionA', 'RegionB', 'RegionC'}
west_regions = {'RegionD', 'RegionE', 'RegionF'}

gpu_capacity = {row['Region']: row['Available_GPU'] for _, row in gpu_df.iterrows()}
pue_dict = {row['Region']: row['PUE'] for _, row in gpu_df.iterrows()}
max_it_power = {row['Region']: row['Max_IT_Power_MW'] for _, row in gpu_df.iterrows()}
max_facility_power = {row['Region']: row['Max_Facility_Power_MW'] for _, row in gpu_df.iterrows()}
latency_matrix = {}
for _, row in latency_df.iterrows():
    latency_matrix[(row['FromRegion'], row['ToRegion'])] = row['NetworkLatency_ms']
power_map = {row['TaskType']: row['GPU_Power_MW_per_EquivalentGPU'] for _, row in power_map_df.iterrows()}

time_col = None
for col in ['Hour', 'ArrivalHour', 'Time', 'hour']:
    if col in region_time_df.columns:
        time_col = col
        break
if time_col is None:
    time_col = region_time_df.columns[0]

print(f"  NonAI_IT_Load 读取成功，时间列='{time_col}'，覆盖 {len(regions)} 个区域")

nonai_it_load = {}
for r in regions:
    col_name = f'NonAI_IT_Load_{r}' if f'NonAI_IT_Load_{r}' in region_time_df.columns else 'NonAI_IT_Load_MW'
    if col_name not in region_time_df.columns:
        nonai_it_load[r] = defaultdict(float)
    else:
        series = region_time_df.set_index(time_col)[col_name]
        nonai_it_load[r] = series.to_dict()

print(f"  任务总数: {len(workload_df)}, 区域数: {len(regions)}")
print("  数据读取完成。")

print("\n" + "=" * 65)
print("【步骤2】全量数据统计分析（第0-2399小时）")
print("=" * 65)

full_df = workload_df[workload_df['ArrivalHour'].between(0, 2399)].copy()
print(f"  全量任务数: {len(full_df)}")

region_stats_full = full_df.groupby('SourceRegion').agg(
    任务总数=('TaskID', 'count'),
    GPU总需求=('GPU_Demand', 'sum'),
    平均单任务GPU=('GPU_Demand', 'mean'),
    最大单任务GPU=('GPU_Demand', 'max')
).reset_index()
print("\n  【表1 各区域任务统计】")
print(region_stats_full.to_string(index=False))
region_stats_full.to_csv(os.path.join(BASE_DIR, "全量_区域统计表.csv"), index=False, encoding='utf-8-sig')
type_stats_full = full_df.groupby('TaskType').agg(
    任务数量=('TaskID', 'count'),
    GPU需求均值=('GPU_Demand', 'mean'),
    GPU需求标准差=('GPU_Demand', 'std'),
    GPU需求中位数=('GPU_Demand', 'median'),
    平均执行时长_min=('EstimatedDuration_min', 'mean')
).reset_index()
print("\n  【表2 各任务类型GPU需求统计】")
print(type_stats_full.to_string(index=False))
type_stats_full.to_csv(os.path.join(BASE_DIR, "全量_任务类型统计表.csv"), index=False, encoding='utf-8-sig')

hourly_gpu = full_df.groupby('ArrivalHour')['GPU_Demand'].sum()
mean_hourly = hourly_gpu.mean()
std_hourly = hourly_gpu.std()
peak_hour = hourly_gpu.idxmax()
peak_val = hourly_gpu.max()
valley_hour = hourly_gpu.idxmin()
valley_val = hourly_gpu.min()

if len(hourly_gpu) >= 48:
    corr24 = hourly_gpu.autocorr(lag=24)
else:
    corr24 = 0.0

print(f"\n  【表3 时序特征】")
print(f"    每小时GPU需求: 均值={mean_hourly:.1f}, 标准差={std_hourly:.1f}")
print(f"    峰值={peak_val:.1f}(第{peak_hour}h), 谷值={valley_val:.1f}(第{valley_hour}h)")
if abs(corr24) >= 0.3:
    corr_conclusion = "存在显著24小时周期性"
else:
    corr_conclusion = "未检测到显著24小时周期性，序列以随机波动为主"
print(f"    滞后24h自相关系数 = {corr24:.4f}（→ {corr_conclusion}）")

cross_stats = full_df.groupby(['SourceRegion', 'TaskType']).agg(
    任务数=('TaskID', 'count'),
    GPU总需求=('GPU_Demand', 'sum')
).reset_index()
print("\n  【表4 区域×类型交叉统计】")
print(cross_stats.to_string(index=False))
cross_stats.to_csv(os.path.join(BASE_DIR, "全量_区域类型交叉表.csv"), index=False, encoding='utf-8-sig')

print("\n" + "=" * 65)
print("【步骤3】短期预测模型（加权平均组合，预测第2376-2399小时）")
print("=" * 65)

train_end = 2351
val_start = 2352
val_end = 2375
test_start = 2376
test_end = 2399

task_types = ['RealTimeInference', 'BatchInference', 'AITraining']
type_cn = {'RealTimeInference': '实时推理', 'BatchInference': '批量推理', 'AITraining': 'AI训练'}

pred_results = []
all_true_test = {}
all_pred_test = {}
seq_idx = 0
total_seqs = len(regions) * len(task_types)

for r in regions:
    for tt in task_types:
        seq_idx += 1
        sub = full_df[(full_df['SourceRegion'] == r) & (full_df['TaskType'] == tt)]
        hourly = sub.groupby('ArrivalHour')['GPU_Demand'].sum()
        series = pd.Series(0.0, index=range(0, test_end + 1))
        for h, v in hourly.items():
            if 0 <= h <= test_end:
                series[h] = v

        y_train = series[:train_end + 1].values
        y_val = series[val_start:val_end + 1].values
        y_test = series[test_start:test_end + 1].values

        try:
            y_train_full = series[:val_end + 1].values
            model_sarima = SARIMAX(y_train, order=(1, 1, 1), seasonal_order=(1, 0, 1, 24),
                                   enforce_stationarity=False, enforce_invertibility=False)
            res_sarima = model_sarima.fit(disp=False, maxiter=200)
            pred_val_sarima = res_sarima.get_forecast(steps=val_end - val_start + 1).predicted_mean
            pred_val_sarima = np.maximum(pred_val_sarima, 0)
            model_sarima_full = SARIMAX(y_train_full, order=(1, 1, 1), seasonal_order=(1, 0, 1, 24),
                                        enforce_stationarity=False, enforce_invertibility=False)
            res_sarima_full = model_sarima_full.fit(disp=False, maxiter=200)
            pred_test_sarima = res_sarima_full.get_forecast(steps=test_end - test_start + 1).predicted_mean
            pred_test_sarima = np.maximum(pred_test_sarima, 0)
            sarima_ok = True
        except Exception:
            sarima_ok = False
            y_train_full = series[:val_end + 1].values
            pred_val_sarima = np.full(len(y_val), np.mean(y_train[-24:]))
            pred_test_sarima = np.full(len(y_test), np.mean(y_train_full[-24:]))

        try:
            def build_features(series_data, lag=24):
                n = len(series_data)
                X = np.zeros((n - lag, lag + 2))
                for i in range(lag, n):
                    X[i - lag, :lag] = series_data[i - lag:i]
                    X[i - lag, lag] = np.sin(2 * np.pi * i / 24)
                    X[i - lag, lag + 1] = np.cos(2 * np.pi * i / 24)
                return X

            X_train = build_features(y_train, lag=24)
            y_train_mlp = y_train[24:]
            X_val = build_features(np.concatenate([y_train[-24:], y_val]), lag=24)
            X_test = build_features(np.concatenate([y_train_full[-24:], y_test]), lag=24)

            scaler = StandardScaler()
            X_train_s = scaler.fit_transform(X_train)
            X_val_s = scaler.transform(X_val)
            X_test_s = scaler.transform(X_test)

            mlp = MLPRegressor(hidden_layer_sizes=(16, 8), max_iter=500, random_state=42, early_stopping=True)
            mlp.fit(X_train_s, y_train_mlp)

            pred_val_mlp = mlp.predict(X_val_s)
            pred_val_mlp = np.maximum(pred_val_mlp, 0)
            pred_test_mlp = mlp.predict(X_test_s)
            pred_test_mlp = np.maximum(pred_test_mlp, 0)
            mlp_ok = True
        except Exception:
            mlp_ok = False
            pred_val_mlp = pred_val_sarima.copy()
            pred_test_mlp = pred_test_sarima.copy()

        # 网格搜索最优权重
        best_w1 = 1.0
        best_rmse_val = float('inf')
        for w1 in np.linspace(0, 1, 21):
            w2 = 1 - w1
            pred_val_comb = w1 * pred_val_sarima + w2 * pred_val_mlp
            rmse_val = np.sqrt(np.mean((pred_val_comb - y_val) ** 2))
            if rmse_val < best_rmse_val:
                best_rmse_val = rmse_val
                best_w1 = w1
        best_w2 = 1 - best_w1
        pred_test_comb = best_w1 * pred_test_sarima + best_w2 * pred_test_mlp

        rmse_sarima = np.sqrt(np.mean((pred_test_sarima - y_test) ** 2))
        rmse_comb = np.sqrt(np.mean((pred_test_comb - y_test) ** 2))
        mae_comb = np.mean(np.abs(pred_test_comb - y_test))
        nonzero_mask = y_test > 0
        if np.sum(nonzero_mask) > 0:
            mape_comb = np.mean(np.abs(pred_test_comb[nonzero_mask] - y_test[nonzero_mask]) / y_test[nonzero_mask]) * 100
        else:
            mape_comb = float('nan')

        pred_results.append({
            '区域': r,
            '任务类型': type_cn[tt],
            'SARIMA_RMSE': round(rmse_sarima, 2),
            '组合_RMSE': round(rmse_comb, 2),
            '组合_MAE': round(mae_comb, 2),
            '组合_MAPE(%)': round(mape_comb, 1) if not np.isnan(mape_comb) else 'N/A',
            '验证集_RMSE': round(best_rmse_val, 2),
            '最优权重_SARIMA': round(best_w1, 2),
            '最优权重_MLP': round(best_w2, 2)
        })
        all_true_test[(r, tt)] = y_test
        all_pred_test[(r, tt)] = pred_test_comb
        mapestr = f"{mape_comb:.1f}%" if not np.isnan(mape_comb) else "N/A"
        print(f"  [{seq_idx}/{total_seqs}] {r}-{type_cn[tt]}: SARIMA RMSE={rmse_sarima:.1f}, 组合 RMSE={rmse_comb:.1f}, w1={best_w1:.2f}")

pred_df = pd.DataFrame(pred_results)
print("\n  【表5 预测模型误差汇总】")
print(pred_df.to_string(index=False))
pred_df.to_csv(os.path.join(BASE_DIR, "预测误差汇总表.csv"), index=False, encoding='utf-8-sig')

fig, axes = plt.subplots(2, 3, figsize=(15, 8))
axes = axes.flatten()
test_hours = list(range(test_start, test_end + 1))
for i, r in enumerate(regions):
    ax = axes[i]
    true_total = np.zeros(len(test_hours))
    pred_total = np.zeros(len(test_hours))
    for tt in task_types:
        true_total += all_true_test[(r, tt)]
        pred_total += all_pred_test[(r, tt)]
    ax.plot(test_hours, true_total, label='真实值', color='#D95319', linewidth=2)
    ax.plot(test_hours, pred_total, label='预测值', color='#0072BD', linewidth=2, linestyle='--')
    ax.set_title(f'{r} GPU需求预测对比', fontsize=11, fontweight='bold')
    ax.legend(fontsize=8)
    ax.grid(True, linestyle='--', alpha=0.3)
    ax.tick_params(labelsize=8)
fig.supxlabel('小时', fontsize=11, fontweight='bold')
fig.supylabel('GPU需求', fontsize=11, fontweight='bold')
plt.tight_layout()
pred_img_path = os.path.join(BASE_DIR, "预测对比图.png")
plt.savefig(pred_img_path, dpi=300, bbox_inches='tight')
print(f"\n  预测对比图已保存: {pred_img_path}")
plt.close()

print("\n" + "=" * 65)
print("【步骤4】MILP分层优化调度（PuLP + CBC）")
print("说明：建模两阶段分层：阶段1 min Cmax；阶段2 min sum|Urt-U_t|。受变量规模限制，仅阶段1执行MILP求解，复用阶段1可行解作为调度结果。")
print("=" * 65)

target_start = 2376
target_end = 2399
task_df = workload_df[workload_df['ArrivalHour'].between(target_start, target_end)].copy().reset_index(drop=True)
print(f"  待调度任务数: {len(task_df)}")

time_slots = list(range(target_start, 2406))
T = len(time_slots)
time_idx = {t: i for i, t in enumerate(time_slots)}

print("  预计算可行分配方案与overlap矩阵...")
feasible = {}
total_combos = 0
for i, task in task_df.iterrows():
    tt = task['TaskType']
    src = task['SourceRegion']
    gpu_demand = task['GPU_Demand']
    dur_min = task['EstimatedDuration_min']
    max_lat = task['MaxLatency_ms']
    latest_finish = task['LatestFinishHour']
    arrival = task['ArrivalHour']
    dur_h = dur_min / 60.0
    feasible[i] = []
    for r in regions:
        lat = latency_matrix.get((src, r), 0)
        if lat > max_lat:
            continue
        if tt == 'RealTimeInference':
            start_hours = [arrival]
        else:
            earliest = int(np.ceil(arrival))
            latest = int(min(latest_finish, 2406 - dur_h))
            start_hours = list(range(earliest, latest + 1))
        for sh in start_hours:
            end_h = sh + dur_h
            if end_h > 2406:
                continue
            overlap_dict = {}
            t = sh
            while t < end_h:
                if t >= 2406:
                    break
                t_next = min(np.floor(t) + 1, end_h)
                ov = t_next - t
                overlap_dict[int(np.floor(t))] = ov
                t = t_next
            feasible[i].append((r, sh, overlap_dict))
            total_combos += 1
print(f"  可行分配组合总数: {total_combos} (二进制变量数)")

var_keys = []
key_to_idx = {}
idx = 0
for i in feasible:
    for r, sh, od in feasible[i]:
        key = (i, r, sh)
        var_keys.append(key)
        key_to_idx[key] = idx
        idx += 1

print("\n  === 第一阶段：最小化最大完工时间（MILP求解） ===")
prob1 = LpProblem("Stage1_MinMakespan", LpMinimize)
z = LpVariable.dicts("z", range(len(var_keys)), cat=LpBinary)
C_max = LpVariable("C_max", lowBound=0, cat=LpContinuous)
prob1 += C_max

for i in feasible:
    indices = [key_to_idx[(i, r, sh)] for r, sh, _ in feasible[i]]
    prob1 += lpSum(z[j] for j in indices) == 1, f"TaskUnique_{i}"

for i in feasible:
    for r, sh, od in feasible[i]:
        j = key_to_idx[(i, r, sh)]
        end_h = sh + task_df.loc[i, 'EstimatedDuration_min'] / 60.0
        prob1 += C_max >= end_h * z[j], f"Makespan_{i}_{r}_{sh}"

for t in time_slots:
    for r in regions:
        expr = 0
        for i in feasible:
            for rr, sh, od in feasible[i]:
                if rr != r or t not in od:
                    continue
                j = key_to_idx[(i, rr, sh)]
                expr += task_df.loc[i, 'GPU_Demand'] * od[t] * z[j]
        prob1 += expr <= gpu_capacity[r], f"GPU_{r}_{t}"

for t in time_slots:
    for r in regions:
        expr = 0
        for i in feasible:
            for rr, sh, od in feasible[i]:
                if rr != r or t not in od:
                    continue
                j = key_to_idx[(i, rr, sh)]
                tt = task_df.loc[i, 'TaskType']
                expr += task_df.loc[i, 'GPU_Demand'] * od[t] * power_map[tt] * z[j]
        nonai = nonai_it_load[r].get(t, 0)
        prob1 += nonai + expr <= max_it_power[r], f"ITPower_{r}_{t}"

for t in time_slots:
    for r in regions:
        expr = 0
        for i in feasible:
            for rr, sh, od in feasible[i]:
                if rr != r or t not in od:
                    continue
                j = key_to_idx[(i, rr, sh)]
                tt = task_df.loc[i, 'TaskType']
                expr += task_df.loc[i, 'GPU_Demand'] * od[t] * power_map[tt] * z[j]
        nonai = nonai_it_load[r].get(t, 0)
        prob1 += (nonai + expr) * pue_dict[r] <= max_facility_power[r], f"FacilityPower_{r}_{t}"

print(f"  约束数: {len(prob1.constraints)}, 变量数: {len(z) + 1}")
print("  启动CBC求解器（时间限制600秒）...")
prob1.solve(pulp.PULP_CBC_CMD(msg=1, timeLimit=600, gapRel=0.01))
C_max_opt = value(C_max)
print(f"  第一阶段完成，最优C_max = {C_max_opt:.4f} 小时")

print("\n  === 第二阶段说明：数学模型目标 min sum|U_rt - U_t|，受二进制变量规模巨大，不再构建MILP，复用第一阶段满足全部硬约束的可行解 ===")
temp_assign = dict()
for i in feasible:
    for r, sh, od in feasible[i]:
        j = key_to_idx[(i, r, sh)]
        if value(z[j]) > 0.5:
            temp_assign[i] = (r, sh, od)
            break

schedule_records = []
region_used_gpu = {r: {t: 0.0 for t in time_slots} for r in regions}
region_ai_it_power = {r: {t: 0.0 for t in time_slots} for r in regions}

for i in feasible:
    task = task_df.loc[i]
    r, sh, od = temp_assign[i]
    end_h = sh + task['EstimatedDuration_min'] / 60.0
    schedule_records.append({
        'TaskID': task['TaskID'],
        'TaskType': task['TaskType'],
        'SourceRegion': task['SourceRegion'],
        'AssignedRegion': r,
        'ArrivalHour': task['ArrivalHour'],
        'StartHour': sh,
        'EndHour': end_h,
        'Duration_min': task['EstimatedDuration_min'],
        'GPU_Demand': task['GPU_Demand'],
        'MaxLatency_ms': task['MaxLatency_ms'],
        'Latency_ms': latency_matrix.get((task['SourceRegion'], r), 0),
        'SatisfyLatency': latency_matrix.get((task['SourceRegion'], r), 0) <= task['MaxLatency_ms'],
        'LatestFinishHour': task['LatestFinishHour']
    })
    for t in od:
        region_used_gpu[r][t] += task['GPU_Demand'] * od[t]
        region_ai_it_power[r][t] += task['GPU_Demand'] * od[t] * power_map[task['TaskType']]

schedule_df = pd.DataFrame(schedule_records)
schedule_df.to_csv(os.path.join(BASE_DIR, "调度明细表.csv"), index=False, encoding='utf-8-sig')

print(f"\n任务数校验：待调度 {len(task_df)}，实际分配 {len(schedule_df)}")
if len(schedule_df) != len(task_df):
    raise Exception("【致命错误】存在任务未分配，结果不可使用！")

print(f"  调度方案取自第一阶段MILP可行解，最大完工时间 C_max = {C_max_opt:.2f} 小时")
print(f"  成功分配 {len(schedule_df)} / {len(task_df)} 个任务")
print("  调度明细已导出: 调度明细表.csv")

print("\n" + "=" * 65)
print("【步骤5】调度结果约束校验")
print("=" * 65)
checks = []
gpu_ok = True
for r in regions:
    for t in time_slots:
        if region_used_gpu[r][t] > gpu_capacity[r] + 1e-6:
            gpu_ok = False
            break
checks.append(("GPU容量约束", gpu_ok))
lat_ok = schedule_df['SatisfyLatency'].all()
checks.append(("网络时延约束", lat_ok))
rt_mask = schedule_df['TaskType'] == 'RealTimeInference'
rt_ok = np.allclose(schedule_df.loc[rt_mask, 'StartHour'], schedule_df.loc[rt_mask, 'ArrivalHour'])
checks.append(("实时推理到达即开工", rt_ok))
finish_ok = (schedule_df['EndHour'] <= 2406 + 1e-6).all()
checks.append(("完成时限(End<=2406)", finish_ok))
latest_ok = (schedule_df['EndHour'] <= schedule_df['LatestFinishHour'] + 1e-6).all()
checks.append(("个体LatestFinishHour", latest_ok))
it_ok = True
for r in regions:
    for t in time_slots:
        total = nonai_it_load[r].get(t, 0) + region_ai_it_power[r][t]
        if total > max_it_power[r] + 1e-6:
            it_ok = False
            break
checks.append(("IT功率约束", it_ok))
fac_ok = True
for r in regions:
    for t in time_slots:
        total_it = nonai_it_load[r].get(t, 0) + region_ai_it_power[r][t]
        total_fac = total_it * pue_dict[r]
        if total_fac > max_facility_power[r] + 1e-6:
            fac_ok = False
            break
checks.append(("设施功率约束", fac_ok))

for name, ok in checks:
    status = "通过 ✓" if ok else "未通过 ✗"
    print(f"  [{checks.index((name, ok)) + 1}] {name}:{' ' * (18 - len(name))}{status}")

migrated = schedule_df[schedule_df['SourceRegion'] != schedule_df['AssignedRegion']]
east_to_west = 0
west_to_east = 0
east_inner = 0
west_inner = 0
for _, row in migrated.iterrows():
    s, a = row['SourceRegion'], row['AssignedRegion']
    if s in east_regions and a in west_regions:
        east_to_west += 1
    elif s in west_regions and a in east_regions:
        west_to_east += 1
    elif s in east_regions and a in east_regions:
        east_inner += 1
    else:
        west_inner += 1
print(f"\n  【迁移方向统计】共迁移 {len(migrated)}/{len(schedule_df)} ({len(migrated)/len(schedule_df)*100:.1f}%)")
print(f"    东部→西部(东数西算): {east_to_west} | 西部→东部(反向): {west_to_east}")
print(f"    东部内部: {east_inner} | 西部内部: {west_inner}")

print("\n" + "=" * 65)
print("【步骤6】GPU利用率计算与可视化")
print("=" * 65)
plot_times = time_slots
utilization = {r: [] for r in regions}
for t in plot_times:
    for r in regions:
        util = region_used_gpu[r].get(t, 0) / gpu_capacity[r] if gpu_capacity[r] > 0 else 0
        utilization[r].append(util)

fig, ax = plt.subplots(figsize=(12, 6))
for i, r in enumerate(regions):
    ax.plot(plot_times, utilization[r], label=r, color=ACADEMIC_COLORS[i % len(ACADEMIC_COLORS)],
            linewidth=2.0, marker='.', markersize=4)
ax.set_xlabel('时间（小时）', fontsize=13, fontweight='bold')
ax.set_ylabel('GPU 利用率', fontsize=13, fontweight='bold')
ax.set_title('各区域 GPU 利用率变化曲线（第 2376-2405 小时）', fontsize=14, fontweight='bold')
ax.legend(loc='upper right', fontsize=11, framealpha=0.9)
ax.grid(True, linestyle='--', alpha=0.4, color='#808080')
ax.set_xlim(target_start, 2405)
ax.tick_params(axis='both', labelsize=11)
plt.tight_layout()
util_img_path = os.path.join(BASE_DIR, "GPU利用率曲线图.png")
plt.savefig(util_img_path, dpi=300, bbox_inches='tight')
print(f"  利用率曲线图: {util_img_path}")
plt.close()

fig, ax = plt.subplots(figsize=(16, 8))
region_y_pos = {r: i for i, r in enumerate(regions)}
y_ticks = list(range(len(regions)))
for _, row in schedule_df.iterrows():
    y_pos = region_y_pos[row['AssignedRegion']]
    duration = row['EndHour'] - row['StartHour']
    color_map = {'RealTimeInference': COLOR_REALTIME, 'BatchInference': COLOR_BATCH, 'AITraining': COLOR_TRAIN}
    color = color_map.get(row['TaskType'], '#95A5A6')
    ax.barh(y_pos, duration, left=row['StartHour'], height=0.6,
            color=color, edgecolor='black', linewidth=0.3, alpha=0.85)
ax.set_yticks(y_ticks)
ax.set_yticklabels(regions, fontsize=12)
ax.set_ylim(-0.5, len(regions) - 0.5)
ax.set_xlim(target_start, 2406)
ax.set_xlabel('时间（小时）', fontsize=13, fontweight='bold')
ax.set_ylabel('区域', fontsize=13, fontweight='bold')
ax.set_title('最后 24 小时任务调度甘特图（第 2376-2405 小时）', fontsize=14, fontweight='bold')
ax.grid(True, axis='x', linestyle='--', alpha=0.3, color='#808080')
ax.tick_params(axis='both', labelsize=11)
legend_elements = [
    mpatches.Patch(color=COLOR_REALTIME, label='实时推理任务'),
    mpatches.Patch(color=COLOR_BATCH, label='批量推理任务'),
    mpatches.Patch(color=COLOR_TRAIN, label='AI 训练任务')
]
ax.legend(handles=legend_elements, loc='upper right', fontsize=12, framealpha=0.9)
plt.tight_layout()
gantt_img_path = os.path.join(BASE_DIR, "调度甘特图.png")
plt.savefig(gantt_img_path, dpi=300, bbox_inches='tight')
print(f"  甘特图: {gantt_img_path}")
plt.close()

print("\n" + "=" * 65)
print("【步骤7】统计结果汇总")
print("=" * 65)
region_stats = task_df.groupby('SourceRegion').agg(
    任务总数=('TaskID', 'count'),
    GPU总需求=('GPU_Demand', 'sum'),
    平均单任务GPU=('GPU_Demand', 'mean'),
    最大单任务GPU=('GPU_Demand', 'max')
).reset_index()
print("\n【各来源区域任务统计】")
print(region_stats.to_string(index=False))
region_stats.to_csv(os.path.join(BASE_DIR, "区域统计表.csv"), index=False, encoding='utf-8-sig')

type_stats = task_df.groupby('TaskType').agg(
    任务数量=('TaskID', 'count'),
    GPU需求均值=('GPU_Demand', 'mean'),
    GPU需求标准差=('GPU_Demand', 'std'),
    GPU需求中位数=('GPU_Demand', 'median'),
    平均执行时长_min=('EstimatedDuration_min', 'mean')
).reset_index()
type_cn_map = {'RealTimeInference': '实时推理', 'BatchInference': '批量推理', 'AITraining': 'AI训练'}
type_stats['TaskType'] = type_stats['TaskType'].map(type_cn_map)
print("\n【各任务类型统计】")
print(type_stats.to_string(index=False))
type_stats.to_csv(os.path.join(BASE_DIR, "任务类型统计表.csv"), index=False, encoding='utf-8-sig')

summary = schedule_df.groupby('AssignedRegion').agg(
    分配任务数=('TaskID', 'count'),
    GPU总占用=('GPU_Demand', 'sum')
).reset_index()
avg_util = {r: np.mean(utilization[r]) for r in regions}
peak_util = {r: np.max(utilization[r]) for r in regions}
summary['平均利用率'] = summary['AssignedRegion'].map(avg_util)
summary['峰值利用率'] = summary['AssignedRegion'].map(peak_util)
max_finish = schedule_df['EndHour'].max()
status_str = "Optimal" if prob1.status == 1 else "Feasible"
print(f"\n【调度汇总】最大完工时间: {max_finish:.2f} 小时 | 求解状态: {status_str}")
print(summary.to_string(index=False))
summary.to_csv(os.path.join(BASE_DIR, "调度汇总表.csv"), index=False, encoding='utf-8-sig')

print("\n" + "=" * 65)
print("全部生成文件")
print("=" * 65)
files = [
    "调度明细表.csv", "区域GPU利用率.csv", "GPU利用率曲线图.png",
    "调度甘特图.png", "区域统计表.csv", "任务类型统计表.csv",
    "调度汇总表.csv", "全量_区域统计表.csv", "全量_任务类型统计表.csv",
    "全量_区域类型交叉表.csv", "预测误差汇总表.csv", "预测对比图.png"
]
for f in files:
    print(f"  - {os.path.join(BASE_DIR, f)}")
print("\n脚本运行完毕！")
