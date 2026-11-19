import json,numpy as np,sys
from PIL import Image,ImageDraw,ImageFont
D='/home/user/ddn-project/brand/fonts/match'
d=json.load(open(D+'/scores.json'));refm={int(k):v for k,v in d['refm'].items()}
C=json.load(open(D+'/cand2_metrics.json'))
exec(open('score_c2.py').read().split('refm=')[0].split("R=json")[0])
R=json.load(open(D+'/ref_metrics.json'))
S=json.load(open('strings.json'))
def ld(p): return 1-np.asarray(Image.open(p).convert('L'),dtype=np.float32)/255
def capmet(fam,w,M):
    tag='ref' if fam=='articulat-cf' else fam.replace(' ','')
    a=ld(f"{D}/{'ref' if tag=='ref' else 'cand2'}/{tag}__{w}__n1.png"); xs=M[f'{fam}|{w}|n1']['xs']
    sub=a[:,int(xs[0][0]):int(xs[0][0]+xs[0][1])]; r=np.where(sub.max(1)>0.5)[0]; return r.max(), r.max()-r.min()+1
def line(fam,w,k,M,rb,rcap,track=0.0):
    tag='ref' if fam=='articulat-cf' else fam.replace(' ','')
    a=ld(f"{D}/{'ref' if tag=='ref' else 'cand2'}/{tag}__{w}__{k}.png")
    b,cap=capmet(fam,w,M); sc=rcap/cap
    im=Image.fromarray((a*255).astype(np.uint8)).resize((int(a.shape[1]*sc),int(a.shape[0]*sc)),Image.LANCZOS)
    out=np.zeros((170,3600),np.float32); z=np.asarray(im,dtype=np.float32)/255
    off=rb-int(round(b*sc)); 
    y0=max(0,off); z=z[max(0,-off):]; h=min(170-y0,z.shape[0]); w2=min(3600,z.shape[1])
    out[y0:y0+h,:w2]=z[:h,:w2]; return out
def make(k,rw,cands,fn):
    rb,rcap=capmet('articulat-cf',rw,R); ref=line('articulat-cf',rw,k,R,rb,rcap)
    W=int(max(np.where(ref.max(0)>0.3)[0]))+60
    rowsimg=[]; labels=[]
    for f,cw in cands:
        c=line(f,cw,k,C,rb,rcap)
        rgb=np.ones((170,3600,3),np.float32)
        rgb[...,0]-=c; rgb[...,1]-=np.maximum(ref,c)*1; rgb[...,2]-=ref   # ref=red? ref ink removes blue+green -> red; cand removes red+green -> blue; both -> black
        rgb=np.clip(rgb,0,1)
        rowsimg.append(rgb[:,:W]); labels.append(f'{f} {cw}  (red=Articulat {rw}, blue=candidate, black=overlap)')
    H=len(rowsimg)*200+60; sheet=Image.new('RGB',(W,H),'white'); dr=ImageDraw.Draw(sheet)
    fnt=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',22) 
    dr.text((10,10),f'Articulat CF {rw} ("{S[k]}") vs candidates, normalised to cap height',fill='black',font=fnt)
    for i,(r,l) in enumerate(zip(rowsimg,labels)):
        dr.text((10,50+i*200),l,fill=(80,80,80),font=fnt); sheet.paste(Image.fromarray((r*255).astype(np.uint8)),(0,70+i*200))
    sheet.save(fn); print(fn, sheet.size)
import ast
k=sys.argv[1]; rw=int(sys.argv[2]); cands=ast.literal_eval(sys.argv[3]); make(k,rw,cands,sys.argv[4])
