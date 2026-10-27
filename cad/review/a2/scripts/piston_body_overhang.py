# Overhang (>45 deg from vertical) on the piston's O33 sliding body vs the O22.2 spigot, print orientation.
import sys, struct, numpy as np
def read(p):
    with open(p,'rb') as f:
        f.read(80); n=struct.unpack('<I',f.read(4))[0]
        a=np.frombuffer(f.read(n*50),dtype=np.dtype([('n','<3f4'),('v','<9f4'),('a','<u2')]))
    return a['v'].reshape(-1,3,3).astype(float)
V=read(sys.argv[1]); c=V.mean(1); n=np.cross(V[:,1]-V[:,0],V[:,2]-V[:,0]); A=np.linalg.norm(n,axis=1)/2; n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-12)
ax_z=15.3  # axis height above bed (flat 1.2 mm off R16.5)
r=np.hypot(c[:,0],c[:,2]-ax_z)
oh=(n[:,2]<-0.7072)&(c[:,2]>0.3)
for name,lo,hi in (('body O33 (sliding surface)',15.5,17),('spigot O22.2',10.5,11.5)):
    m=oh&(r>lo)&(r<hi)
    print(f'{name}: {A[m].sum():.0f} mm2 steeper than 45 deg, y {c[m][:,1].min():.0f}..{c[m][:,1].max():.0f}, z {c[m][:,2].min():.1f}..{c[m][:,2].max():.1f}' if m.any() else name+': 0')
