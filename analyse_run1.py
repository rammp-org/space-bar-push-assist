import csv,sys,statistics as st
sys.path.insert(0,"/Users/alxchunlin/code-stuff/alex-style-guide/matplotlib")
import alex_style as ax, matplotlib.pyplot as plt
R=[list(map(float,r)) for r in csv.reader(open('run.csv'))]
t0=R[0][0]; T=[r[0]-t0 for r in R]; L=[r[1] for r in R]; F=[r[2] for r in R]; raw=[r[12] for r in R]; hw=[r[16] for r in R]
dt=st.median([b-a for a,b in zip(T,T[1:])])
# own baseline: EMA while idle; hysteresis on/off as % of baseline
ON,OFF,TAU=8.0,4.0,10.0
base=st.median(raw[:50]); touched=False; B=[];D=[];S=[]
for x in raw:
    d=x-base; p=100*d/base
    if not touched and p>ON: touched=True
    elif touched and p<OFF: touched=False
    if not touched: base+= (x-base)*min(1,dt/TAU)
    B.append(base); D.append(x-base); S.append(touched)
# tare on the rolling average before the touch, output gated by touch
W,GAP=int(1.0/dt),int(0.2/dt)
out=[];tare=0;ev=[]
for i,s in enumerate(S):
    if s and (i==0 or not S[i-1]):
        seg=F[max(0,i-GAP-W):max(1,i-GAP)]; tare=sum(seg)/len(seg); ev.append([i,tare])
    if not s and i and S[i-1]: ev[-1].append(i)
    out.append(F[i]-tare if s else 0.0)
print(f"dt {dt*1000:.0f} ms, {len(ev)} touches; idle noise {st.pstdev(D[:250]):.1f} counts, baseline {B[0]:.0f}")
print(" #  on_s  dur_s  delta_pk  tare_N  push_N  pull_N  resid_fw_N  resid_gated  lead_s")
rows=[]
for k,e in enumerate(ev):
    i,tr=e[0],e[1]; j=e[2] if len(e)>2 else len(S)-1
    seg=F[i:j]; dpk=max(D[i:j]); 
    post=F[j+3:j+3+int(1/dt)] if j+3<len(F) else []
    lead=next((T[m]-T[i] for m in range(i,j) if abs(F[m]-tr)>2),float('nan'))
    rows.append((k+1,T[i],T[j]-T[i],dpk,tr,max(seg)-tr,min(seg)-tr,(sum(post)/len(post)) if post else float('nan'),0.0,lead))
    print("%2d %6.1f %5.1f %8.0f %7.1f %7.1f %7.1f %10.1f %11.1f %6.2f"%rows[-1])
# hands-off residual: all idle samples after first touch
idle=[F[i] for i in range(len(S)) if not S[i] and T[i]>T[ev[0][0]]]
print(f"hands-off after first touch: firmware right_N mean {st.mean(idle):.1f} N, max {max(idle):.1f} N; gated output 0.0 N")
print("hardware active flag on for", f"{100*sum(hw)/len(hw):.0f}% of samples")
ax.use("dark"); C=ax.PALETTE["dark"]
fig,(a1,a2,a3)=plt.subplots(3,1,figsize=(10,9.5),sharex=False)
a1.plot(T,[100*d/b for d,b in zip(D,B)],color="#2f62e8",lw=1.8,label="Touch signal")
for v,lab in ((ON,f"on {ON:.0f} %"),(OFF,f"off {OFF:.0f} %")): a1.axhline(v,color=C["warning"],ls=(0,(4,3)),lw=1); a1.text(1,v+0.4,lab,fontsize=8,color=C["muted"])
a1.set_xlabel("Time, s"); a1.set_ylabel("Above baseline, %"); ax.title(a1,"Touch on the right handle", f"{len(ev)} touches; baseline {B[0]:.0f} counts, idle noise {st.pstdev(D[:250]):.1f} counts")
a2.plot(T,F,color="#e03a2f",lw=1.6,label="Firmware now (zero tracking)"); a2.plot(T,out,color="#0f9a66",lw=1.8,label="Touch tare + switch")
a2.axhline(0,color=C["muted"],lw=0.8)
a2.set_xlabel("Time, s"); a2.set_ylabel("Right handle force, N"); ax.title(a2,"Right handle force","Hands off reads 0 N when gated by touch")
a2.legend(loc="lower right",bbox_to_anchor=(1,1.0),frameon=False,ncol=2,fontsize=9)
i0=max(0,ev[0][0]-int(4/dt)); i1=min(len(T)-1,ev[1][0]+int(1/dt))
a3.plot(T[i0:i1],F[i0:i1],color="#e03a2f",lw=1.8,label="Firmware now"); a3.plot(T[i0:i1],out[i0:i1],color="#0f9a66",lw=2,label="Touch tare + switch")
for e in ev[:2]:
    a3.axvspan(T[e[0]],T[e[2]],color=C["muted"],alpha=0.12,lw=0)
a3.axhline(0,color=C["muted"],lw=0.8); a3.set_xlabel("Time, s"); a3.set_ylabel("Right handle force, N"); ax.title(a3,"First touch, close up","Shaded: touched. Tare = mean of the 1 s ending 0.2 s before the touch")
a3.legend(loc="lower right",bbox_to_anchor=(1,1.0),frameon=False,ncol=2,fontsize=9)
fig.tight_layout(); ax.save(fig,"touch_tare.png")
