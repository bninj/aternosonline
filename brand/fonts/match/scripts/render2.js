const { chromium } = require('/opt/node-tools/node_modules/playwright');
const fs=require('fs');
const OUT='/home/user/ddn-project/brand/fonts/match';
const STR=JSON.parse(fs.readFileSync('strings.json'));
const W=[];for(let w=340;w<=760;w+=20)W.push(w);
const G=["Inter Tight","Inter","Figtree","Plus Jakarta Sans","Manrope","Albert Sans","Outfit","Urbanist","Onest","Geist","Instrument Sans","Hanken Grotesk","DM Sans","Public Sans","Schibsted Grotesk","Work Sans","Red Hat Display","Red Hat Text","Golos Text","Rethink Sans","Funnel Sans","Host Grotesk","Wix Madefor Display","Archivo","Be Vietnam Pro","Sora","Mona Sans","Hubot Sans","Poppins","Lexend","Karla","Gantari","Readex Pro","Arimo"];
const FS={"General Sans":"general-sans","Satoshi":"satoshi","Switzer":"switzer","Supreme":"supreme","Cabinet Grotesk":"cabinet-grotesk","Author":"author","Synonym":"synonym"};
async function shoot(p,fam,dir,tag,res){
  for(const w of W){
    const ok=await p.evaluate(async([fam,w])=>{try{await document.fonts.load(`${w} 120px "${fam}"`)}catch(e){};return [...document.fonts].some(f=>f.family.replace(/"/g,'')==fam&&f.status=='loaded'&&(f.weight==String(w)||(f.weight.includes(' ')&&+f.weight.split(' ')[0]<=w&&+f.weight.split(' ')[1]>=w)))},[fam,w]);
    if(!ok){continue}
    for(const [k,s] of Object.entries(STR)){
      const m=await p.evaluate(([fam,w,s])=>{let d=document.getElementById('ov');if(!d){d=document.createElement('div');d.id='ov';document.body.appendChild(d)}
        d.style.cssText=`position:fixed;left:0;top:0;z-index:2147483647;background:#fff;color:#000;font-family:"${fam}";font-weight:${w};font-size:120px;line-height:180px;letter-spacing:0;padding:0 30px;white-space:nowrap;font-synthesis:none;font-feature-settings:normal;text-transform:none;-webkit-font-smoothing:antialiased;font-kerning:normal;width:max-content`;
        d.textContent=s;const t=d.firstChild;const xs=[];for(let i=0;i<s.length;i++){const r=document.createRange();r.setStart(t,i);r.setEnd(t,i+1);const b=r.getBoundingClientRect();xs.push([b.left,b.width])}
        return {width:d.getBoundingClientRect().width-60,xs}},[fam,w,s]);
      await p.locator('#ov').screenshot({path:`${OUT}/${dir}/${tag}__${w}__${k}.png`});
      res[`${fam}|${w}|${k}`]=m;
    }
  }
}
(async()=>{const b=await chromium.launch({executablePath:'/usr/bin/google-chrome'});
 const ctx=await b.newContext({viewport:{width:6000,height:400}});
 const res={};
 if(process.argv[2]!='cand'){
  const p=await ctx.newPage();await p.goto('https://www.ddn.com/',{waitUntil:'networkidle',timeout:90000});
  await p.evaluate(()=>document.fonts.ready);
  await shoot(p,'articulat-cf','ref','ref',res);
  fs.writeFileSync(OUT+'/ref_metrics.json',JSON.stringify(res));
 } else {
  const p=await ctx.newPage();
  const VF={"Inter Tight":"intertight_InterTight[wght].ttf","Manrope":"manrope_Manrope[wght].ttf","Instrument Sans":"instrumentsans_InstrumentSans[wdth,wght].ttf","Inter":"inter_Inter[opsz,wght].ttf","Onest":"onest_Onest[wght].ttf","Funnel Sans":"funnelsans_FunnelSans[wght].ttf","Mona Sans":"monasans_MonaSans[wdth,wght].ttf","Geist":"geist_Geist[wght].ttf"};
  const DL='/tmp/claude-0/-home-user/dc066354-8ace-5f9c-97bb-fc22fd7a3463/scratchpad/dl/';
  let css=Object.entries(VF).map(([f,fn])=>`@font-face{font-family:"${f}";src:url("data:font/ttf;base64,${fs.readFileSync(DL+fn).toString('base64')}");font-weight:100 900}`).join('');
  await p.setContent(`<html><head><style>${css}</style></head><body></body></html>`);
  for(const f of Object.keys(VF)){const tag=f.replace(/ /g,'');await shoot(p,f,'cand2',tag,res);console.log(f,Object.keys(res).length)}
  fs.writeFileSync(OUT+'/cand2_metrics.json',JSON.stringify(res));
  if(0){let links=G.map(f=>`<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=${f.replace(/ /g,'+')}:wght@400;500;600;700&display=block">`).join('');
  links+=Object.values(FS).map(s=>`<link rel="stylesheet" href="https://api.fontshare.com/v2/css?f[]=${s}@400,500,600,700&display=block">`).join('');
  await p.setContent(`<html><head>${links}</head><body></body></html>`,{waitUntil:'networkidle'});
  for(const f of [...G,...Object.keys(FS)]){const tag=f.replace(/ /g,'');await shoot(p,f,'cand2',tag,res);console.log(f,Object.keys(res).length)}
  fs.writeFileSync(OUT+'/cand2_metrics.json',JSON.stringify(res));}
 }
 await b.close()})();
