import sys,ast,json,numpy as np
from PIL import Image,ImageDraw,ImageFont
exec(open('sheet_c2.py').read().split('def make')[0])
def stack(k,rw,cands,fn,scale=0.5):
    rb,rcap=capmet('articulat-cf',rw,R); ref=line('articulat-cf',rw,k,R,rb,rcap)
    W=int(max(np.where(ref.max(0)>0.3)[0]))+40
    for f,cw in cands:
        c=line(f,cw,k,C,rb,rcap); W=max(W,int(max(np.where(c.max(0)>0.3)[0]))+40)
    fnt=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',26)
    rows=[('ARTICULAT CF %d (reference, ddn.com)'%rw,ref)]+[(f'{f} {cw}',line(f,cw,k,C,rb,rcap)) for f,cw in cands]
    sh=Image.new('L',(W+420,len(rows)*130+10),255);dr=ImageDraw.Draw(sh)
    for i,(l,a) in enumerate(rows):
        im=Image.fromarray(((1-a[20:150,:W])*255).astype(np.uint8)); sh.paste(im,(420,i*130+5)); dr.text((10,i*130+60),l,fill=0,font=fnt)
        if i==0: dr.line([(0,i*130+132),(W+420,i*130+132)],fill=128,width=2)
    sh=sh.resize((int(sh.width*scale),int(sh.height*scale)),Image.LANCZOS); sh.save(fn); print(fn,sh.size)
stack(sys.argv[1],int(sys.argv[2]),ast.literal_eval(sys.argv[3]),sys.argv[4],float(sys.argv[5]) if len(sys.argv)>5 else 0.5)
