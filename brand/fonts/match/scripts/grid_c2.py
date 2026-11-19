import sys,ast,json,numpy as np
from PIL import Image,ImageDraw,ImageFont
src=open('score_c2.py').read().split('refm={w:')[0]; exec(src)
want=[('a','h2'),('g','p2'),('t','h2'),('y','h4'),('R','h2'),('G','h2'),('W','h1'),('e','h2'),('s','h2'),('f','p2'),('r','h2'),('1','n1'),('0','n1'),('8','p2'),('x','n1'),('’','h1'),('.','h4'),('c','h4'),('m','h4'),('D','h1')]
def find(k,ch): return S[k].index(ch)
def get(f,w,M):
    base,cap,xh=metrics(f,w,M); 
    return base,cap
rw=int(sys.argv[1]); cands=ast.literal_eval(sys.argv[2]); fn=sys.argv[3]
rb,rcap=get('articulat-cf',rw,R)
rows=[('Articulat CF %d'%rw,{k:glyphs('articulat-cf',rw,k,R,rb,1.0) for k in set(k for _,k in want)})]
for f,cw in cands:
    b,cap=get(f,cw,C); rows.append((f'{f} {cw}',{k:glyphs(f,cw,k,C,b,rcap/cap) for k in set(k for _,k in want)}))
cell=120; fnt=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
sh=Image.new('L',(220+cell*len(want),len(rows)*cell+10),255);dr=ImageDraw.Draw(sh)
for i,(lab,G) in enumerate(rows):
    dr.text((5,i*cell+50),lab,fill=0,font=fnt)
    for j,(ch,k) in enumerate(want):
        A=G[k][find(k,ch)]
        if A is None: continue
        A=A[40:170]; im=Image.fromarray(((~A)*255).astype(np.uint8)).resize((int(A.shape[1]*0.85),int(A.shape[0]*0.85)))
        sh.paste(im,(220+j*cell+(cell-im.width)//2,i*cell))
    dr.line([(0,(i+1)*cell),(sh.width,(i+1)*cell)],fill=200)
sh.save(fn);print(fn,sh.size)
