/* Build responsive WebP and complete, lighter reels. Originals are retained. */
const fs = require('fs'), path = require('path'), os = require('os'), crypto = require('crypto');
const {execFileSync} = require('child_process');
const sharp = require(path.join(os.homedir(), '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp'));
const root = path.resolve(__dirname, '..');
const dest = path.join(root, 'assets/optimized');
const manifestFile = path.join(root, 'content/seo-media.json');
fs.mkdirSync(dest, {recursive: true});
const previous = fs.existsSync(manifestFile) ? JSON.parse(fs.readFileSync(manifestFile)) : {images:{}, videos:{}};
const originals = new Map();
for (const [src, info] of Object.entries(previous.images)) {
  for (const v of info.variants) originals.set(v.url, src);
  if (info.favicon) originals.set(info.favicon, src);
}
const files = ['index.html','terms.html','privacy.html','tools.html', ...['blog','templates','demo'].flatMap(d=>fs.readdirSync(path.join(root,d)).filter(f=>f.endsWith('.html')).map(f=>d+'/'+f))];
const sources = new Set(['/assets/icon.png', '/assets/game-jump-shot.png']);
for (const key of ['all','blue','red','black']) sources.add('/assets/video/players/'+key+'.jpg');
for (const f of files) {
  for (const m of fs.readFileSync(path.join(root,f),'utf8').matchAll(/(?:src|poster|href)="([^"]+\.(?:png|jpe?g|webp))(?:\?[^"]*)?"/gi)) {
    const url = new URL(m[1], 'https://hoopcut.ai/');
    if (url.hostname !== 'hoopcut.ai') continue;
    sources.add(originals.get(url.pathname) || url.pathname);
  }
}
const digest = b => crypto.createHash('sha256').update(b).digest('hex').slice(0,12);
const exists = url => fs.existsSync(path.join(root, url));
const output = {version:1, images:{}, videos:{}};
async function image(src) {
  const input = path.join(root, src);
  if (!fs.existsSync(input)) throw Error('Missing source '+src);
  const hash = digest(Buffer.concat([fs.readFileSync(input), Buffer.from('webp-q80-v1')]));
  const old = previous.images[src];
  const faviconNeeded = src === '/assets/icon.png';
  if (old?.sourceHash === hash && old.variants.every(v=>exists(v.url)) && (!faviconNeeded || (old.favicon && exists(old.favicon)))) {output.images[src]=old;return;}
  const meta = await sharp(input).metadata();
  const icon = /(?:icon|brand-icon)\./.test(src);
  const widths = icon ? [48,96,192] : [320,640,960,1280];
  const sizes = [...new Set(widths.map(w=>Math.min(w, meta.width)))].sort((a,b)=>a-b);
  const variants = [];
  for (const width of sizes) {
    const bytes = await sharp(input).rotate().resize({width,withoutEnlargement:true}).webp({quality:80,effort:5}).toBuffer();
    const url='/assets/optimized/'+path.parse(src).name+'-'+width+'.'+digest(bytes)+'.webp';
    fs.writeFileSync(path.join(root,url),bytes); variants.push({url,width,bytes:bytes.length});
  }
  output.images[src]={sourceHash:hash,originalBytes:fs.statSync(input).size,width:meta.width,height:meta.height,variants};
  if (faviconNeeded) {
    const png = await sharp(input).resize(48,48).png({palette:true}).toBuffer();
    const url='/assets/optimized/favicon.'+digest(png)+'.png';
    fs.writeFileSync(path.join(root,url),png); output.images[src].favicon=url;
  }
}
async function main() {
  for (const src of sources) await image(src);
  for (const key of ['all','blue','red','black']) {
    const input=path.join(root,'assets/video/players',key+'.mp4');
    const hash=digest(Buffer.concat([fs.readFileSync(input),Buffer.from('h264-crf27-30fps-v1')]));
    const old=previous.videos[key];
    if(old?.sourceHash===hash && Object.values(old.variants).every(v=>exists(v.url))){output.videos[key]=old;continue;}
    const variants={};
    for (const [label,width] of [['desktop',960],['mobile',640]]) {
      const tmp=path.join(dest,key+'-'+label+'.next.mp4');
      execFileSync('/opt/homebrew/bin/ffmpeg',['-y','-v','error','-i',input,'-vf',`scale=${width}:-2:flags=lanczos,setsar=1`,'-an','-c:v','libx264','-preset','medium','-crf','27','-pix_fmt','yuv420p','-threads','4','-movflags','+faststart',tmp]);
      const data=fs.readFileSync(tmp),url=`/assets/optimized/reel-${key}-${width}.${digest(data)}.mp4`;
      fs.renameSync(tmp,path.join(root,url));variants[label]={url,width,bytes:data.length};
    }
    output.videos[key]={sourceHash:hash,originalBytes:fs.statSync(input).size,variants};
    console.log(key,JSON.stringify(variants));
  }
  fs.writeFileSync(manifestFile,JSON.stringify(output,null,2)+'\n');
  console.log(`Prepared ${Object.keys(output.images).length} responsive images and four complete reels.`);
}
main().catch(e=>{console.error(e);process.exit(1);});
