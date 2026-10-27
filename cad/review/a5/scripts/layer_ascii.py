"""ASCII layer occupancy of an STL at two heights: '#' solid at z, '.' void at z;
'B' solid at z AND void at z-dz (unsupported). Usage: layer_ascii.py part.stl z [dz] [cell]"""
import sys, struct, numpy as np
def load(p):
    b=open(p,'rb').read()
    if b[:5]==b'solid' and b'facet' in b[:300]:
        v=[list(map(float,l.split()[1:4])) for l in b.decode().splitlines() if l.strip().startswith('vertex')]
        return np.array(v).reshape(-1,3,3)
    n=struct.unpack('<I',b[80:84])[0]
    a=np.frombuffer(b[84:84+n*50],dtype=np.dtype([('n','<f4',3),('v','<f4',(3,3)),('a','<u2')]))
    return a['v'].astype(float)
def inside(T,z,xs,ys):
    # ray cast along +x per row: count crossings of segments of the slice
    segs=[]
    for t in T:
        d=t[:,2]-z; s=np.sign(d)
        if s.min()>=0 or s.max()<=0: continue
        pts=[]
        for i in range(3):
            a,b=t[i],t[(i+1)%3]
            if (a[2]-z)*(b[2]-z)<0:
                f=(z-a[2])/(b[2]-a[2]); pts.append(a+f*(b-a))
        if len(pts)==2: segs.append((pts[0][:2],pts[1][:2]))
    S=np.array(segs)
    G=np.zeros((len(ys),len(xs)),bool)
    for j,y in enumerate(ys):
        y0,y1=S[:,0,1],S[:,1,1]
        m=(y0>y)!=(y1>y)
        xc=S[m,0,0]+(y-y0[m])*(S[m,1,0]-S[m,0,0])/(y1[m]-y0[m])
        xc=np.sort(xc)
        G[j]=(np.searchsorted(xc,xs)%2)==1
    return G
T=load(sys.argv[1]); z=float(sys.argv[2]); dz=float(sys.argv[3]) if len(sys.argv)>3 else 0.4
c=float(sys.argv[4]) if len(sys.argv)>4 else 1.0
lo=T.reshape(-1,3).min(0); hi=T.reshape(-1,3).max(0)
xs=np.arange(lo[0]+c/2,hi[0],c); ys=np.arange(lo[1]+c/2,hi[1],c)
A=inside(T,z+0.05,xs,ys); B=inside(T,z-dz,xs,ys)
print(f"x {lo[0]:.1f}..{hi[0]:.1f} y {lo[1]:.1f}..{hi[1]:.1f} cell {c}")
for j in range(len(ys)-1,-1,-1):
    print(f"{ys[j]:7.1f} "+''.join('B' if A[j,i] and not B[j,i] else ('#' if A[j,i] else ('o' if B[j,i] else '.')) for i in range(len(xs))))
