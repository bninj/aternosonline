import json,numpy as np
d=json.load(open('/home/user/ddn-project/brand/fonts/match/scores.json'));rows=d['rows'];print('ref metrics base,cap,xh',d['refm'])
for r in rows: r['score']=(1-r['iou'])*100 + 2*r['chamfer'] + 40*abs(np.log(r['xh_ratio'])) + 20*r['glyph_w']+20*abs(np.log(r['ink']))
for rw in [400,500,600,700]:
  best={}
  for r in rows:
    if r['rw']==rw and (r['font'] not in best or r['score']<best[r['font']]['score']): best[r['font']]=r
  print(f'\n== ref weight {rw}')
  print('font                 cw  score  IoU   chamf xh/ref  gw    setW  ink')
  for r in sorted(best.values(),key=lambda r:r['score'])[:14]:
    print(f"{r['font']:20s} {r['cw']} {r['score']:6.2f} {r['iou']:.3f} {r['chamfer']:.2f} {r['xh_ratio']:.3f} {r['glyph_w']:.3f} {r['set_width']:.3f} {r['ink']:.3f}")
print('\n== family mean of best score over 4 weights (and weight map)')
fam={}
for r in rows:
  k=(r['font'],r['rw']); 
  if k not in fam or r['score']<fam[k]['score']: fam[k]=r
agg={}
for (f,rw),r in fam.items(): agg.setdefault(f,[]).append((rw,r['cw'],r['score'],r['iou']))
for f,v in sorted(agg.items(),key=lambda kv:np.mean([x[2] for x in kv[1]]))[:15]:
  print(f"{f:20s} mean {np.mean([x[2] for x in v]):5.2f} iou {np.mean([x[3] for x in v]):.3f} map", {x[0]:x[1] for x in sorted(v)})
print('\n== distinctive glyph IoU (best weight match, ref 400 & 700)')
G=list("agtyRGDWAe1086")
for rw in [400,700]:
  print('ref',rw, ' '.join(f'{c:>5s}' for c in G))
  for f in ['Funnel Sans','Inter Tight','Inter','Onest','Mona Sans','Manrope','DM Sans','Instrument Sans','General Sans','Satoshi','Switzer','Figtree','Plus Jakarta Sans','Geist']:
    r=fam[(f,rw)]; print(f"{f[:14]:14s}{r['cw']}", ' '.join(f"{r['per'].get(c,float('nan')):5.2f}" for c in G))
