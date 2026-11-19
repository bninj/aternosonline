import json,numpy as np
D='/home/user/ddn-project/brand/fonts/match'
d=json.load(open(D+'/scores2.json'));rows=d['rows']
C=json.load(open(D+'/cand2_metrics.json'));R=json.load(open(D+'/ref_metrics.json'));S=json.load(open('strings.json'))
for r in rows: r['score']=(1-r['iou'])*100 + 2*r['chamfer'] + 40*abs(np.log(r['xh_ratio'])) + 20*r['glyph_w']+20*abs(np.log(r['ink']))
out={}
for rw in [400,500,600,700]:
  print(f'\n== Articulat {rw}');best={}
  for r in rows:
    if r['rw']==rw and (r['font'] not in best or r['score']<best[r['font']]['score']): best[r['font']]=r
  for r in sorted(best.values(),key=lambda r:r['score']):
    f,cw=r['font'],r['cw'];ls=[]
    for k,s in S.items():
      if k=='n1': continue
      wc=C[f'{f}|{cw}|{k}']['width']; wr=R[f'articulat-cf|{rw}|{k}']['width']
      ls.append((wr/r['sc']-wc)/len(s)/120)
    r['track_em']=float(np.median(ls))
    print(f"{f:16s} w{cw}  score {r['score']:5.2f} IoU {r['iou']:.3f} chamf {r['chamfer']:.2f} xh {r['xh_ratio']:.3f} setW {r['set_width']:.3f} ink {r['ink']:.3f} size x{r['sc']:.3f} track {r['track_em']*1000:+.0f}/1000em")
  out[rw]=sorted(best.values(),key=lambda r:r['score'])
json.dump({rw:[{k:v for k,v in r.items() if k!='per'} for r in L] for rw,L in out.items()},open(D+'/finetune_summary.json','w'),indent=1)
