import json,numpy as np,sys
from PIL import Image
from scipy import ndimage as ndi
D='/home/user/ddn-project/brand/fonts/match'
R=json.load(open(D+'/ref_metrics.json')); C=json.load(open(D+'/cand2_metrics.json'))
S=json.load(open('strings.json'))
def load(path): return 1-np.asarray(Image.open(path).convert('L'),dtype=np.float32)/255
def img(fam,w,k):
    tag='ref' if fam=='articulat-cf' else fam.replace(' ','')
    return load(f"{D}/{'ref' if tag=='ref' else 'cand2'}/{tag}__{w}__{k}.png")
def colink(a,x0,x1):
    sub=a[:,max(0,int(round(x0))):int(round(x1))]; rows=np.where(sub.max(1)>0.5)[0]; return rows
def metrics(fam,w,M):
    a=img(fam,w,'n1'); xs=M[f'{fam}|{w}|n1']['xs']
    r1=colink(a,xs[0][0],xs[0][0]+xs[0][1]); rx=colink(a,xs[2][0],xs[2][0]+xs[2][1])
    base=r1.max(); cap=base-r1.min()+1; xh=rx.max()-rx.min()+1
    return base,cap,xh
def glyphs(fam,w,k,M,base,scale):
    a=img(fam,w,k); xs=M[f'{fam}|{w}|{k}']['xs']; out=[]
    for ch,(x0,wd) in zip(S[k],xs):
        if ch==' ': out.append(None); continue
        # take advance box widened by 15% each side, then keep components? keep simple
        lo=int(np.floor(x0)); hi=int(np.ceil(x0+wd)); sub=a[:,lo:hi]
        if sub.size==0 or sub.max()<0.5: out.append(None); continue
        cols=np.where(sub.max(0)>0.5)[0]; sub=sub[:,cols.min():cols.max()+1]
        # place with baseline at fixed row, scaled
        z=ndi.zoom(sub,scale,order=1)
        b=int(round(base*scale)); H=200; top=150-b
        canvas=np.zeros((H, z.shape[1]+2),np.float32)
        y0=max(0,top); zs=z[max(0,-top):max(0,-top)+H-y0]
        canvas[y0:y0+zs.shape[0],1:1+z.shape[1]]=zs[:, :]
        out.append(canvas>0.5)
    return out
def pair(A,B):
    w=max(A.shape[1],B.shape[1]); 
    def pad(X):
        p=w-X.shape[1]; return np.pad(X,((0,0),(p//2,p-p//2)))
    A=pad(A);B=pad(B)
    iou=(A&B).sum()/max(1,(A|B).sum())
    eA=A^ndi.binary_erosion(A); eB=B^ndi.binary_erosion(B)
    dA=ndi.distance_transform_edt(~eA); dB=ndi.distance_transform_edt(~eB)
    ch=(dB[eA].mean()+dA[eB].mean())/2 if eA.any() and eB.any() else 50
    return iou,ch
refm={w:metrics('articulat-cf',w,R) for w in [400,500,600,700]}
refg={(w,k):glyphs('articulat-cf',w,k,R,refm[w][0],1.0) for w in refm for k in S}
fams=sorted(set(x.split('|')[0] for x in C))
rows=[]
for f in fams:
  ws=sorted(set(int(x.split('|')[1]) for x in C if x.startswith(f+'|')))
  for cw in ws:
    base,cap,xh=metrics(f,cw,C); 
    for rw in refm:
      rb,rcap,rxh=refm[rw]; sc=rcap/cap
      g=[];chs=[];wr=[];per={}
      widths=[]
      for k in S:
        cg=glyphs(f,cw,k,C,base,sc); 
        for ch,A,B in zip(S[k],refg[(rw,k)],cg):
          if A is None or B is None: continue
          i,c=pair(A,B); g.append(i); chs.append(c); per.setdefault(ch,[]).append(i)
          wr.append(abs(np.log(B.shape[1]/A.shape[1])))
        widths.append(C[f'{f}|{cw}|{k}']['width']*sc/R[f'articulat-cf|{rw}|{k}']['width'])
      inkr=np.mean([B.sum() for k in S for B in glyphs(f,cw,k,C,base,sc) if B is not None])/np.mean([A.sum() for k in S for A in refg[(rw,k)] if A is not None])
      rows.append(dict(font=f,cw=cw,rw=rw,sc=float(sc),iou=float(np.mean(g)),chamfer=float(np.mean(chs)),xh_ratio=(xh/cap)/(rxh/rcap),glyph_w=float(np.mean(wr)),set_width=float(np.mean(widths)),ink=float(inkr),per={k:float(np.mean(v)) for k,v in per.items()}))
  print(f,file=sys.stderr)
json.dump(dict(rows=rows,refm={k:[int(x) for x in v] for k,v in refm.items()}),open(D+'/scores2.json','w'))
