import json,numpy as np
from PIL import Image
from scipy import ndimage as ndi
D='/home/user/ddn-project/brand/fonts/match'
im=np.asarray(Image.open('/home/user/ddn-project/reference/frames/In-Conversation-CEO-01-Vertical/f_005.jpg').convert('L'),dtype=np.float32)
reg=im[1380+80:1380+165,200+75:200+810]
m=reg>150
cols=m.sum(0)>0
import itertools
groups=[];x=0
for v,g in itertools.groupby(cols):
    L=len(list(g))
    if v: groups.append((x,x+L))
    x+=L
m=m[:,:groups[8][1]]
lab,n=ndi.label(m); sizes=ndi.sum(m,lab,range(1,n+1)); m=np.isin(lab,[i+1 for i,s in enumerate(sizes) if s>30])
ys,xs=np.where(m); m=m[ys.min():ys.max()+1,xs.min():xs.max()+1]
Image.fromarray((~m*255).astype(np.uint8)).save(D+'/video_ref_ALEX_BOUZA.png')
H,W=m.shape; print('ref cap px',H,'width',W,'w/h',W/H)
C=json.load(open(D+'/cand3_metrics.json'))
res=[]
for key in C:
    f,w,k=key.split('|')
    if k!='v1': continue
    a=1-np.asarray(Image.open(f"{D}/cand3/{f.replace(' ','')}__{w}__v1.png").convert('L'),dtype=np.float32)/255
    a=a[:,:int(C[key]['xs'][9][0]+C[key]['xs'][9][1])+2]; b=a>0.5; ys,xs=np.where(b); b=a[ys.min():ys.max()+1,xs.min():xs.max()+1]
    sc=H/b.shape[0]; z=ndi.zoom(b,sc,order=1)>0.5
    ratio=z.shape[1]/W
    # compare after scaling horizontally to equal width (shape) and raw (spacing)
    zz=np.asarray(Image.fromarray(z.astype(np.uint8)*255).resize((W,H)))>127
    iou=(zz&m).sum()/(zz|m).sum()
    ink=z.sum()/m.sum()*(W/z.shape[1])
    # tracking: chars 12, 11 gaps; font px = 120*sc
    track=(W-z.shape[1])/9/(120*sc)
    res.append((f,int(w),iou,ratio,ink,track))
best={}
for r in res:
    score=(1-r[2])+0.5*abs(np.log(r[4]))
    if r[0] not in best or score<best[r[0]][0]: best[r[0]]=(score,r)
for f,(s,r) in sorted(best.items(),key=lambda x:x[1][0]):
    print(f"{f:16s} w{r[1]} IoU(width-normalised) {r[2]:.3f} natural width/ref {r[3]:.3f} ink {r[4]:.2f} tracking to match {r[5]*1000:+.0f}/1000em")
