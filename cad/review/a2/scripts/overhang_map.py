# Locate downward facets steeper than 45 deg from vertical (i.e. normal z < -cos45) per printed part in print orientation.
# Usage: cad py overhang_map.py <stl_dir>
import sys, os, numpy as np
from collections import defaultdict
def read_stl(p):
    import struct
    with open(p,'rb') as f:
        f.read(80); n=struct.unpack('<I',f.read(4))[0]
        a=np.frombuffer(f.read(n*50),dtype=np.dtype([('n','<3f4'),('v','<9f4'),('a','<u2')]))
    return a['v'].reshape(-1,3,3)
d=sys.argv[1]
for fn in sorted(os.listdir(d)):
    if not fn.endswith('.stl'): continue
    if fn.endswith('_L.stl') or '_L_' in fn: continue
    V=read_stl(os.path.join(d,fn)).astype(float)
    e1=V[:,1]-V[:,0]; e2=V[:,2]-V[:,0]; n=np.cross(e1,e2); A=np.linalg.norm(n,axis=1)/2; n=n/np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-12)
    zmin=V[:,:,2].min()
    c=V.mean(axis=1)
    m=(n[:,2]< -np.cos(np.radians(45))-1e-3)&(c[:,2]>zmin+0.3)
    print(f'== {fn}: overhang>45 off-bed {A[m].sum():.0f} mm2 (steeper than 60 from vertical: {A[m&(n[:,2]<-np.cos(np.radians(30)))].sum():.0f} mm2; flat ceilings n_z<-0.98: {A[m&(n[:,2]<-0.98)].sum():.0f} mm2)  bbox {V.reshape(-1,3).min(0).round(1)} {V.reshape(-1,3).max(0).round(1)}')
    # cluster on a 6 mm grid
    g=defaultdict(float); zs=defaultdict(list)
    for ci,ai,nz in zip(c[m],A[m],n[m][:,2]):
        k=tuple((ci//6).astype(int)); g[k]+=ai; zs[k].append(nz)
    for k,a in sorted(g.items(),key=lambda t:-t[1])[:12]:
        if a<3: break
        print(f'   cell~({k[0]*6+3},{k[1]*6+3},{k[2]*6+3}) area {a:.0f} mm2  mean slope from vertical {np.degrees(np.arccos(-np.mean(zs[k]))):.0f}->{90-np.degrees(np.arccos(-np.mean(zs[k]))):.0f} deg from horizontal')
