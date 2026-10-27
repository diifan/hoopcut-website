/* Render original SVG diagrams as lightweight JPEG covers and captioned MP4 walkthroughs. */
const fs=require('fs');
const path=require('path');
const cp=require('child_process');
const os=require('os');
let sharp;
try { sharp=require('sharp'); }
catch { sharp=require(path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp')); }
const root=path.resolve(__dirname,'..');
const dir=path.join(root,'assets/resources');
const resources=JSON.parse(fs.readFileSync(path.join(root,'content/blog/batch-one-resources.json'))).resources;
const articleKeywords=['how to film basketball games','record basketball practice alone','basketball senior night poster ideas','basketball senior night gift ideas','basketball senior night table ideas'];
const guides=JSON.parse(fs.readFileSync(path.join(root,'content/blog/articles.json'))).filter(x=>articleKeywords.includes(x.keyword));
const items=[...resources,...guides.map(a=>({slug:a.keyword.replaceAll(' ','-'),short:a.title.split(':')[0],videoSteps:a.sections.slice(0,3).map(x=>x[0])}))];
const esc=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
function wrap(s,max=43){const lines=[];let line='';for(const word of s.split(' ')){if((line+' '+word).trim().length>max){lines.push(line);line=word;}else line=(line+' '+word).trim();}if(line)lines.push(line);return lines;}
(async()=>{
 const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'hoopcut-walkthrough-'));
 const manifest=[];
 for(const item of items){
  const source=path.join(dir,item.slug+'.svg');
  const darkLayouts=['cover','poster','recruiting'];
  const cover=await sharp(source).resize(1200,800,{fit:'contain',background:darkLayouts.includes(item.layout)?'#141a17':'#f1eddf'}).jpeg({quality:83,mozjpeg:true}).toBuffer();
  fs.writeFileSync(path.join(dir,item.slug+'.jpg'),cover);
  if(item.kind==='graphic')await sharp(source).jpeg({quality:87,mozjpeg:true}).toFile(path.join(dir,item.slug+'-preview.jpg'));
  const illustration=await sharp(source).resize(1000,570,{fit:'contain',background:darkLayouts.includes(item.layout)?'#141a17':'#f1eddf'}).png().toBuffer();
  for(let phase=0;phase<3;phase++){
   const labels=item.videoSteps;
   let overlay=`<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800"><g font-family="Arial,Helvetica,sans-serif"><text x="40" y="39" fill="#ffb88d" font-size="15">HOOPCUT / ILLUSTRATED WALKTHROUGH / EXAMPLE DATA</text><text x="40" y="79" fill="#f4eddf" font-size="27">${esc(item.short.slice(0,70))}</text>`;
   labels.forEach((label,i)=>{
    const x=40+i*390;
    overlay+=`<rect x="${x}" y="690" width="370" height="90" rx="7" fill="${i===phase?'#f1eddf':'#293322'}"/><text x="${x+16}" y="716" fill="${i===phase?'#ad4726':'#b6c3a8'}" font-size="14">0${i+1}${i===phase?' / CURRENT STEP':''}</text>`;
    wrap(label,33).slice(0,2).forEach((line,j)=>overlay+=`<text x="${x+16}" y="${743+j*21}" font-size="17" fill="${i===phase?'#242d26':'#ced7c1'}">${esc(line)}</text>`);
   });
   overlay+='</g></svg>';
   const filename=path.join(tmp,`frame-${phase+1}.jpg`);
   await sharp({create:{width:1200,height:800,channels:3,background:'#11170e'}}).composite([{input:illustration,left:100,top:103},{input:Buffer.from(overlay),left:0,top:0}]).jpeg({quality:85}).toFile(filename);
   if(phase===0)fs.copyFileSync(filename,path.join(dir,item.slug+'-poster.jpg'));
  }
  cp.execFileSync('/opt/homebrew/bin/ffmpeg',['-y','-loglevel','error','-framerate','1/3','-start_number','1','-i',path.join(tmp,'frame-%d.jpg'),'-t','9','-c:v','libx264','-preset','fast','-crf','26','-pix_fmt','yuv420p','-r','24','-movflags','+faststart',path.join(dir,item.slug+'.mp4')]);
  const stamp=n=>'00:00:'+String(n).padStart(2,'0')+'.000';
  const vtt='WEBVTT\n\n'+item.videoSteps.map((text,i)=>`${stamp(i*3)} --> ${stamp((i+1)*3)}\nStep ${i+1}: ${text}`).join('\n\n')+'\n';
  fs.writeFileSync(path.join(dir,item.slug+'.vtt'),vtt);
  manifest.push({slug:item.slug,kind:'original SVG-based illustrated walkthrough',durationSeconds:9,source:'assets/resources/'+item.slug+'.svg',video:'assets/resources/'+item.slug+'.mp4',captionTrack:'assets/resources/'+item.slug+'.vtt',disclosure:'Illustrated example; not customer footage, app recording or a measured result.'});
  console.log('Rendered:',item.slug);
 }
 fs.rmSync(tmp,{recursive:true,force:true});
 fs.writeFileSync(path.join(root,'content/blog/batch-one-media-manifest.json'),JSON.stringify(manifest,null,2)+'\n');
})();
