/* Original code-drawn graphics; no external requests or customer data. */
const {createRequire}=require('node:module'),path=require('node:path'),os=require('node:os'),fs=require('node:fs/promises');
const {pathToFileURL}=require('node:url');const root=path.resolve(__dirname,'..');
let sharp;try{sharp=require('sharp');}catch{sharp=require(path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp'));}
(async()=>{
 const {courtSVG}=await import(pathToFileURL(path.join(root,'assets/court/geometry.js')));
 for(const shots of [false,true]){
  const slug=shots?'basketball-shot-chart':'basketball-court-diagram';
  const items=shots?[[5,4,true],[7,2,true],[2,5,false],[13,2,false],[9,9,true],[8,11,false],[10,7,true]].map(([x,y,made],i)=>({id:'sample'+i,type:'shot',number:i+1,x,y,made})):[];
  const court=courtSVG({standard:'nba',view:shots?'half':'full',theme:'wood',units:'ft',dimensions:true,items},{exporting:true});
  const graphic=`<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630"><rect width="1200" height="630" fill="#171e15"/><path d="M0 560H1200" stroke="#46513e"/><g font-family="Arial,sans-serif"><text x="55" y="68" fill="#efa67a" font-size="16" letter-spacing="3">HOOPCUT / FREE COURT TOOLS</text><text x="55" y="230" fill="#f2eee1" font-size="66" font-weight="700" letter-spacing="-3">${shots?'Every shot.':'Your court.'}</text><text x="55" y="303" fill="#f2eee1" font-size="66" font-weight="700" letter-spacing="-3">${shots?'On the map.':'Your plan.'}</text><text x="58" y="357" fill="#b5c3a6" font-size="20">${shots?'Basketball shot chart &amp; tracker':'Interactive basketball court diagram'}</text><text x="58" y="401" fill="#efa67a" font-size="14">${shots?'LOG ATTEMPTS · SEE YOUR SPOTS':'PLACE PLAYERS · PLAN THE CAMERA'}</text><text x="55" y="602" fill="#a8b59b" font-size="13">${shots?'ILLUSTRATED EXAMPLE SHOTS':'NBA / FIBA REFERENCE LAYOUTS'} · NO SIGN-IN</text></g><g transform="translate(${shots?690:510} ${shots?90:142}) scale(${shots?.81:.69})">${court.content}</g></svg>`;
  await fs.mkdir(path.join(root,'assets/court'),{recursive:true});
  await sharp(Buffer.from(graphic)).png().toFile(path.join(root,'assets/court',slug+'-social.png'));
 }
 console.log('Built 2 original court-tool social images.');
})().catch(e=>{console.error(e);process.exitCode=1;});
