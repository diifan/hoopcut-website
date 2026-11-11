/* Reference geometry in metres. A planning diagram, not a construction drawing. */
export const COURTS = {
  nba: {name:'NBA',width:15.24,length:28.6512,hoop:1.6002,lane:4.8768,free:5.7912,circle:1.8288,arc:7.239,corner:6.7056,restricted:1.2192},
  fiba:{name:'FIBA',width:15,length:28,hoop:1.575,lane:4.9,free:5.8,circle:1.8,arc:6.75,corner:6.6,restricted:1.3}
};
export const escapeXML = value => String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
export const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
export function localShot(standard,point){
  const c=COURTS[standard];return {x:point.x,y:point.y>c.length/2?c.length-point.y:point.y};
}
export function shotValue(standard,point){
  const c=COURTS[standard],p=localShot(standard,point),dx=Math.abs(p.x-c.width/2),dy=p.y-c.hoop;
  const join=c.hoop+Math.sqrt(c.arc*c.arc-c.corner*c.corner);
  return (p.y<=join?dx>c.corner+.025:Math.hypot(dx,dy)>c.arc+.025)?3:2;
}
export function shotZone(standard,point){
  const c=COURTS[standard],p=localShot(standard,point),dx=p.x-c.width/2;
  if(shotValue(standard,point)===3){
    if(Math.abs(dx)<c.width*.2)return 'Above-break three';
    return dx<0?'Left three':'Right three';
  }
  if(Math.hypot(dx,p.y-c.hoop)<=c.restricted)return 'At the rim';
  return Math.abs(dx)<=c.lane/2&&p.y<=c.free?'Paint':'Mid-range';
}
export function summarize(standard,shots){
  const stats={attempts:shots.length,made:shots.filter(s=>s.made).length,two:{made:0,attempts:0},three:{made:0,attempts:0},zones:{}};
  for(const s of shots){const key=shotValue(standard,s)===3?'three':'two',zone=shotZone(standard,s);stats[key].attempts++;if(s.made)stats[key].made++;stats.zones[zone]??={made:0,attempts:0};stats.zones[zone].attempts++;if(s.made)stats.zones[zone].made++;}
  stats.percentage=stats.attempts?Math.round(100*stats.made/stats.attempts):null;return stats;
}
export function layout(standard,view){
  const c=COURTS[standard],height=view==='full'?c.length:c.length/2,scale=30,pad=43;
  return {court:c,height,viewBox:view==='full'?`0 0 ${height*scale+pad*2} ${c.width*scale+pad*2}`:`0 0 ${c.width*scale+pad*2} ${height*scale+pad*2}`,transform:view==='full'?`translate(${pad+height*scale} ${pad}) rotate(90) scale(${scale})`:`translate(${pad} ${pad+height*scale}) scale(${scale} -${scale})`};
}
export function courtSVG(state,{exporting=false}={}){
  const {court:c,height,viewBox,transform}=layout(state.standard,state.view),light=state.theme!=='ink';
  const paper=light?'#eee8d8':'#202c27',floor=light?'#ddc59f':'#293e33',line=light?'#626651':'#acbfa9',soft=light?'#9e8f7370':'#ffffff10';
  const join=c.hoop+Math.sqrt(c.arc*c.arc-c.corner*c.corner),left=c.width/2-c.corner,right=c.width/2+c.corner;
  function basket(){return `<rect x="${(c.width-c.lane)/2}" y="0" width="${c.lane}" height="${c.free}" fill="${light?'#e5d3b3':'#324d3c'}"/><g fill="none" stroke="${line}" stroke-width=".05"><rect x="${(c.width-c.lane)/2}" y="0" width="${c.lane}" height="${c.free}"/><circle cx="${c.width/2}" cy="${c.free}" r="${c.circle}"/><path d="M ${left} 0 V ${join} A ${c.arc} ${c.arc} 0 0 0 ${right} ${join} V 0"/><path d="M ${c.width/2-c.restricted} ${c.hoop} A ${c.restricted} ${c.restricted} 0 0 0 ${c.width/2+c.restricted} ${c.hoop}"/><path d="M ${c.width/2-.9} ${c.hoop-.375} h 1.8"/><circle cx="${c.width/2}" cy="${c.hoop}" r=".225" stroke="#c66d40" stroke-width=".07"/></g>`;}
  let marks='';
  for(const m of state.items||[]){if(m.y>height+.001)continue;const attrs=`data-point="${escapeXML(m.id)}" tabindex="0" role="button" aria-label="${escapeXML(m.type==='shot'?`Shot ${m.number}, ${m.made?'made':'missed'}, ${shotValue(state.standard,m)} points`:m.type+' '+(m.label||''))}"`;
    if(m.type==='arrow'){if(m.y2>height)continue;marks+=`<path ${attrs} d="M${m.x} ${m.y}L${m.x2} ${m.y2}" stroke="#d96636" stroke-width=".12" stroke-linecap="round" marker-end="url(#court-arrow)" fill="none"/>`;continue;}
    let shape='';
    if(m.type==='shot')shape=m.made?'<circle r=".22" fill="#2f7155" stroke="#f6f3e7" stroke-width=".06"/><circle r=".07" fill="#f6f3e7"/>':'<path d="M-.17 -.17L.17 .17M-.17 .17L.17 -.17" stroke="#b04c2b" stroke-width=".11" stroke-linecap="round"/>';
    if(m.type==='player')shape=`<circle r=".43" fill="#d56438" stroke="#fff1d2" stroke-width=".06"/><g transform="${state.view==='full'?'rotate(-90)':'scale(1 -1)'}"><text text-anchor="middle" dominant-baseline="central" font-size=".38" font-family="Arial,sans-serif" font-weight="700" fill="#fff6e4">${escapeXML(m.label)}</text></g>`;
    if(m.type==='camera')shape='<circle r=".48" fill="#324f62" stroke="#f5ecd9" stroke-width=".06"/><rect x="-.25" y="-.15" width=".38" height=".3" rx=".04" fill="none" stroke="#fff" stroke-width=".05"/><path d="M.13 -.08L.29 -.17V.17L.13 .08Z" fill="#fff"/>';
    if(m.type==='ball')shape='<circle r=".25" fill="#e0803d" stroke="#65482c" stroke-width=".04"/><path d="M-.25 0H.25M0 -.25V.25" stroke="#65482c" stroke-width=".035"/>';
    marks+=`<g ${attrs} transform="translate(${m.x} ${m.y})">${shape}</g>`;
  }
  let labels='';
  if(state.dimensions){const vb=viewBox.split(' ').map(Number),unit=state.units==='m'?'m':'ft',fmt=n=>(state.units==='m'?n:n/.3048).toFixed(state.units==='m'?2:0).replace(/\.00$/,'');
    labels=`<g fill="${line}" font-size="12" font-family="Arial,sans-serif" text-anchor="middle"><text x="${vb[2]/2}" y="23">${fmt(state.view==='full'?height:c.width)} ${unit}</text><text transform="translate(20 ${vb[3]/2}) rotate(-90)">${fmt(state.view==='full'?c.width:height)} ${unit}</text></g>`;}
  const svg=`<defs><pattern id="court-planks" width=".75" height="3.6" patternUnits="userSpaceOnUse"><path d="M0 0V3.6M0 3.6H.75" stroke="${soft}" stroke-width=".012"/></pattern><marker id="court-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#d96636"/></marker></defs><rect width="100%" height="100%" rx="14" fill="${paper}"/>${labels}<g id="court-coordinate" transform="${transform}"><rect width="${c.width}" height="${height}" fill="${floor}"/><rect width="${c.width}" height="${height}" fill="url(#court-planks)"/>${basket()}${state.view==='full'?`<g transform="translate(${c.width} ${c.length}) rotate(180)">${basket()}</g><path d="M0 ${height/2}H${c.width}" stroke="${line}" stroke-width=".05"/><circle cx="${c.width/2}" cy="${height/2}" r="${c.circle}" fill="none" stroke="${line}" stroke-width=".05"/>`:`<path d="M${c.width/2-c.circle} ${height}A${c.circle} ${c.circle} 0 0 1 ${c.width/2+c.circle} ${height}" fill="none" stroke="${line}" stroke-width=".05"/>`}<rect x="0" y="0" width="${c.width}" height="${height}" stroke="${line}" stroke-width=".065" fill="none"/>${marks}${!exporting&&state.cursor?`<circle cx="${state.cursor.x}" cy="${state.cursor.y}" r=".36" stroke="#4a615c" stroke-width=".04" stroke-dasharray=".1 .1" fill="none"/>`:''}</g>`;
  return {viewBox,content:svg};
}
