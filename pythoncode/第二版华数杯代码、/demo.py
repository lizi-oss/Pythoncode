import numpy as np
from collections import deque
from numba import jit

L_CUBE = 10000
HALF_L = 5000
rA = 30
hA = 5000
VA = np.pi * (rA ** 2) * hA
D_CONDUCT = 1.8

OFFSETS = np.array([
    [-L_CUBE, -L_CUBE, -L_CUBE],[-L_CUBE, -L_CUBE, 0],[-L_CUBE, -L_CUBE, L_CUBE],
    [-L_CUBE, 0, -L_CUBE],[-L_CUBE,0,0],[-L_CUBE,0,L_CUBE],
    [-L_CUBE,L_CUBE,-L_CUBE],[-L_CUBE,L_CUBE,0],[-L_CUBE,L_CUBE,L_CUBE],
    [0,-L_CUBE,-L_CUBE],[0,-L_CUBE,0],[0,-L_CUBE,L_CUBE],
    [0,0,-L_CUBE],[0,0,0],[0,0,L_CUBE],
    [0,L_CUBE,-L_CUBE],[0,L_CUBE,0],[0,L_CUBE,L_CUBE],
    [L_CUBE,-L_CUBE,-L_CUBE],[L_CUBE,-L_CUBE,0],[L_CUBE,-L_CUBE,L_CUBE],
    [L_CUBE,0,-L_CUBE],[L_CUBE,0,0],[L_CUBE,0,L_CUBE],
    [L_CUBE,L_CUBE,-L_CUBE],[L_CUBE,L_CUBE,0],[L_CUBE,L_CUBE,L_CUBE]
], dtype=np.float64)

@jit(nopython=True, fastmath=True, cache=False)
def seg_dist(p0, p1, q0, q1):
    a = p1 - p0
    b = q1 - q0
    c = q0 - p0
    a_dot_a = np.dot(a, a)
    b_dot_b = np.dot(b, b)
    a_dot_b = np.dot(a, b)
    a_dot_c = np.dot(a, c)
    b_dot_c = np.dot(b, c)
    denom = a_dot_a * b_dot_b - a_dot_b ** 2
    if denom < 1e-12:
        t0, t1 = 0.0, 0.0
    else:
        t0 = (a_dot_c * b_dot_b - b_dot_c * a_dot_b) / denom
        t1 = (a_dot_c * a_dot_b - b_dot_c * a_dot_a) / denom
    t0 = max(0.0, min(1.0, t0))
    t1 = max(0.0, min(1.0, t1))
    p = p0 + t0 * a
    q = q0 + t1 * b
    return np.linalg.norm(p - q)

@jit(nopython=True, fastmath=True, cache=False)
def calc_pair_surf_dist(p0i, p1i, p0j, p1j):
    min_seg_d = 1e12
    for k in range(OFFSETS.shape[0]):
        shift = OFFSETS[k]
        d = seg_dist(p0i, p1i, p0j+shift, p1j+shift)
        if d < min_seg_d:
            min_seg_d = d
    return min_seg_d - 2 * rA

@jit(nopython=True, fastmath=True, cache=False)
def seg_plane_raw_dist(p0, p1):
    x0, x1 = p0[0], p1[0]
    x_min = min(x0, x1)
    x_max = max(x0, x1)
    L_plane = -HALF_L
    R_plane = HALF_L
    dL = min(abs(x0-L_plane), abs(x1-L_plane)) - rA
    dR = min(abs(x0-R_plane), abs(x1-R_plane)) - rA
    if L_plane >= x_min -1e-9 and L_plane <= x_max +1e-9:
        dL = -rA
    if R_plane >= x_min -1e-9 and R_plane <= x_max +1e-9:
        dR = -rA
    return dL, dR

@jit(nopython=True, fastmath=True, cache=False)
def seg_plane_min_dist(p0, p1):
    minL = 1e12
    minR = 1e12
    for k in range(OFFSETS.shape[0]):
        shift = OFFSETS[k]
        dl, dr = seg_plane_raw_dist(p0+shift, p1+shift)
        if dl < minL:
            minL = dl
        if dr < minR:
            minR = dr
    return minL, minR

def gen_one_cyl():
    while True:
        p0 = np.random.uniform(-HALF_L, HALF_L, size=3)
        vec = np.random.randn(3)
        vec = vec / np.linalg.norm(vec)
        p1 = p0 + vec * hA
        return p0,p1

def gen_cyl_array(N):
    arr = np.zeros((N,2,3), dtype=np.float64)
    for i in range(N):
        p0,p1 = gen_one_cyl()
        arr[i,0,:]=p0
        arr[i,1,:]=p1
    return arr

def build_adjacency(seg_arr,N):
    adj=[[] for _ in range(N)]
    for i in range(N):
        p0i,p1i=seg_arr[i,0,:],seg_arr[i,1,:]
        for j in range(i+1,N):
            p0j,p1j=seg_arr[j,0,:],seg_arr[j,1,:]
            sd=calc_pair_surf_dist(p0i,p1i,p0j,p1j)
            if sd <= D_CONDUCT:
                adj[i].append(j)
                adj[j].append(i)
    return adj

def single_simulation(N):
    seg_arr=gen_cyl_array(N)
    n=N
    S=n
    T=n+1
    adj_all=[[] for _ in range(n+2)]
    for idx in range(n):
        p0,p1=seg_arr[idx,0,:],seg_arr[idx,1,:]
        dl,dr=seg_plane_min_dist(p0,p1)
        if dl <= D_CONDUCT:
            adj_all[S].append(idx)
            adj_all[idx].append(S)
        if dr <= D_CONDUCT:
            adj_all[T].append(idx)
            adj_all[idx].append(T)
    inner_adj=build_adjacency(seg_arr,n)
    for i in range(n):
        adj_all[i].extend(inner_adj[i])
    from collections import deque
    vis=[False]*(n+2)
    q=deque([S])
    vis[S]=True
    while q:
        u=q.popleft()
        if u==T:
            return True
        for v in adj_all[u]:
            if not vis[v]:
                vis[v]=True
                q.append(v)
    return False

if __name__ == "__main__":
    import time
    print("开始单次仿真 N=500 ...")
    t0=time.time()
    res = single_simulation(500)
    t1=time.time()
    print(f"单次仿真结束，结果={res},耗时={t1-t0:.2f} s")