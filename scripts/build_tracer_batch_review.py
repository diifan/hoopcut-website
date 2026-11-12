#!/usr/bin/env python3
"""Local-only batch review; reports/ is excluded from the deployment build."""
import argparse
import html
import json
from pathlib import Path
from build_shot_tracer import ROOT, load_pages

H=html.escape
LABELS={'create':'主题主词','merge':'同义词合并','existing':'现有页面','defer':'暂缓'}

def build_one_keyword_review(manifest,root):
    pages={p['slug']:p for p in load_pages(root)}
    fit_labels={'direct':'功能直接相关','adjacent':'篮球相邻需求','ambiguous':'含义待确认','unrelated':'与功能不相关'}
    new=set(manifest['newSlugs']);data=manifest['source'];cards=[];rows=[]
    for d in manifest['keywords']:
        p=pages[d['targetPath'].rsplit('/',1)[1]]
        fit=d['intentFit'];status='本次新增' if p['slug'] in new else '保留原有页面'
        cards.append('<article class="card" data-fit="'+fit+'" data-keyword="'+H(d['keyword'],quote=True)+'"><p class="tag">'+status+' · '+fit_labels[fit]+'</p><h2><a href="'+d['targetPath']+'">'+H(d['keyword'])+'</a></h2><p>'+H(p['intro'])+'</p><a class="open" href="'+d['targetPath']+'">打开实际页面 ↗</a></article>')
        values=lambda key:' / '.join(sorted({r.get(key,'') for r in d['records']}))
        rows.append('<tr data-fit="'+fit+'" data-keyword="'+H(d['keyword'],quote=True)+'"><th scope="row">'+H(d['keyword'])+'</th><td>'+status+'</td><td>'+fit_labels[fit]+'</td><td>'+H(values('Search Volume'))+'</td><td>'+H(values('Keyword Difficulty'))+'</td><td><a href="'+d['targetPath']+'">'+d['targetPath']+'</a></td></tr>')
    replacements={
        'CARDS':''.join(cards),'ROWS':''.join(rows),'TOTAL':str(len(manifest['previewSlugs'])),
        'NEW':str(len(new)),'RETAINED':str(len(manifest['reusedSlugs'])),
        'SOURCE_ROWS':str(data['rows']),'SOURCE_UNIQUE':str(data['uniqueKeywords']),
        'SOURCE_FILE':H(data['file']),'BATCH':H(manifest['batchId']),
        'SOURCE_DATES':H(' — '.join([data['recordDates'][0],data['recordDates'][-1]])),
        'FIT_OPTIONS':''.join('<option value="'+k+'">'+v+'（'+str(manifest['intentFitCounts'].get(k,0))+'）</option>' for k,v in fit_labels.items())
    }
    document='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>HoopCut · {{TOTAL}} 个关键词独立页面</title><style>
    *{box-sizing:border-box}body{margin:0;background:#10120f;color:#f1f3eb;font:16px/1.6 system-ui}main{max-width:1200px;margin:48px auto;padding:0 24px}a{color:#ffac84;text-underline-offset:4px}h1{font-size:clamp(28px,4vw,44px);line-height:1.2}h2{font-size:22px;line-height:1.35}p{max-width:950px}.muted{color:#b9c0b1}.tag{color:#ffac84;font-size:13px}.stats,.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.stats{margin:28px 0}.stats>div,.card{padding:24px;border:1px solid #414936;border-radius:16px;background:#1a1e17}.stats strong{display:block;font-size:36px}.card{display:flex;flex-direction:column;gap:12px;min-width:0}.card p,.card h2{margin:0;overflow-wrap:anywhere}.card p{font-size:14px;color:#bec5b6}.card .tag{color:#ffac84}.open{margin-top:auto;padding-top:10px;font-weight:650}.filters,.pagination{display:flex;flex-wrap:wrap;align-items:end;gap:14px;margin:24px 0}label{display:flex;flex-direction:column;gap:7px;max-width:100%}input,select,button{font:inherit;color:#f5f6f0;background:#252c20;border:1px solid #5a6650;padding:12px;border-radius:8px;max-width:100%}input{width:340px}button{cursor:pointer}button:disabled{opacity:.4;cursor:default}section{margin-top:40px}.table-wrap{overflow:auto}table{border-collapse:collapse;min-width:920px;width:100%;font-size:13px}th,td{padding:12px;border-bottom:1px solid #3c4535;text-align:left;vertical-align:top}td:last-child{max-width:290px;overflow-wrap:anywhere}thead{background:#242c1f}code{overflow-wrap:anywhere}[hidden]{display:none!important}:focus-visible{outline:3px solid #ffac84;outline-offset:3px}@media(max-width:850px){.cards{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:560px){main{margin-top:28px;padding:0 16px}.stats,.cards{grid-template-columns:1fr}.stats>div{padding:16px}.card{padding:20px}.filters label{width:100%}input,select{width:100%}}
    </style></head><body><main><p class="tag">HOOPCUT · LOCAL REVIEW</p><h1>{{TOTAL}} 个关键词，{{TOTAL}} 个独立页面</h1><p>每个不同关键词各有自己的 URL、标题和文案，共用同一套真实 Tracer 上传、预览和导出交互。同义词也独立建页。</p><p class="muted">仅本地预览，未推送、未上线。草稿为 noindex，不进入生产 sitemap。</p><div class="stats"><div><strong>{{TOTAL}}</strong>独立关键词页面</div><div><strong>{{NEW}}</strong>本次新增</div><div><strong>{{RETAINED}}</strong>保留原有页面</div></div><p class="muted">原表 {{SOURCE_ROWS}} 条排名记录，{{SOURCE_UNIQUE}} 个不同关键词。完全相同关键词的重复排名记录共用同一个地址；没有额外造词。</p><p><a href="#pages">查看实际页面</a> · <a href="#keywords">全部关键词与地址</a> · <a href="/shot-tracer/scenarios">打开页面目录</a></p>
    <section id="pages"><h2>选择一个关键词，打开实际页面</h2><div class="filters"><label>关键词搜索<input id="keyword-search" type="search" placeholder="例如 homecourt、basketball、nba"></label><label>查看需求类型<select id="keyword-fit"><option value="">全部页面</option>{{FIT_OPTIONS}}</select></label></div><p id="result-count" aria-live="polite"></p><div class="pagination"><button id="previous" type="button">上一页</button><span id="page-count"></span><button id="next" type="button">下一页</button></div><div class="cards">{{CARDS}}</div><p id="empty" hidden>没有匹配的关键词，清除搜索或更换筛选。</p></section>
    <section id="keywords"><h2>完整关键词与页面地址</h2><p class="muted">所有词均已生成。类型标记只帮助审核意图是否匹配，不会隐藏或合并地址。下表同步应用上方筛选。</p><div class="table-wrap"><table><thead><tr><th>关键词</th><th>本次处理</th><th>需求类型</th><th>搜索量（原值）</th><th>KD（原值）</th><th>独立地址</th></tr></thead><tbody>{{ROWS}}</tbody></table></div></section>
    <section><h2>数据与审核</h2><p class="muted">{{SOURCE_FILE}}；美国，Semrush 估算数据，记录日期 {{SOURCE_DATES}}。这些数据不是 HoopCut 已获得的自然流量。</p><p class="muted">批次：<code>{{BATCH}}</code></p></section></main><script>
    const search=document.getElementById('keyword-search'),fit=document.getElementById('keyword-fit'),cards=[...document.querySelectorAll('.card')],rows=[...document.querySelectorAll('tbody tr')],previous=document.getElementById('previous'),next=document.getElementById('next');let current=0;const size=24;
    function render(reset=false){if(reset)current=0;const q=search.value.trim().toLowerCase(),match=e=>(!fit.value||fit.value===e.dataset.fit)&&(!q||e.dataset.keyword.toLowerCase().includes(q));const results=cards.filter(match),total=Math.max(1,Math.ceil(results.length/size));current=Math.min(current,total-1);cards.forEach(e=>e.hidden=true);results.slice(current*size,(current+1)*size).forEach(e=>e.hidden=false);rows.forEach(e=>e.hidden=!match(e));document.getElementById('result-count').textContent=`找到 ${results.length} / ${cards.length} 个独立页面`;document.getElementById('page-count').textContent=`第 ${current+1} / ${total} 页`;previous.disabled=current===0;next.disabled=current>=total-1;document.getElementById('empty').hidden=results.length>0}
    search.addEventListener('input',()=>render(true));fit.addEventListener('change',()=>render(true));previous.addEventListener('click',()=>{current--;render();document.getElementById('pages').scrollIntoView()});next.addEventListener('click',()=>{current++;render();document.getElementById('pages').scrollIntoView()});render();
    </script></body></html>'''
    for key,value in replacements.items():document=document.replace('{{'+key+'}}',value)
    destination=root/'reports/tracer-keywords-review.html';destination.parent.mkdir(exist_ok=True);destination.write_text(document)
    return destination

def build_review(batch,root=ROOT):
    manifest=json.loads((root/'content/shot-tracer/batch-manifests'/f'{batch}.json').read_text())
    if manifest.get('strategy')=='one-keyword-one-page':return build_one_keyword_review(manifest,root)
    pages={p['slug']:p for p in load_pages(root)}
    selected=[pages[s] for s in manifest['previewSlugs']]
    new=set(manifest['newSlugs']);data=manifest['source'];decisions=manifest['keywords']
    mapped=sum(x['action']!='defer' for x in decisions)
    blocks=[]
    for p in sorted(selected,key=lambda p:(p['slug'] not in new,p['keyword'])):
        keys=[d['keyword'] for d in decisions if d.get('targetPath')=='/shot-tracer/'+p['slug']]
        blocks.append('<article class="card"><p class="tag">'+('新增' if p['slug'] in new else '保留已审核样式')+' · '+str(len(keys))+' 个映射词</p><h2><a href="/shot-tracer/'+p['slug']+'">'+H(p['heading'])+'</a></h2><p>'+H(p['intro'])+'</p><details><summary>承接关键词</summary><p>'+H(' · '.join(keys))+'</p></details><a class="open" href="/shot-tracer/'+p['slug']+'">打开实际页面 ↗</a></article>')
    rows=[]
    for d in decisions:
        values=lambda key:' / '.join(sorted({r.get(key,'') for r in d['records']}))
        target=d.get('targetPath')
        destination=('<a href="'+H(target,quote=True)+'">'+H(target)+'</a>') if target else '—'
        rows.append('<tr data-action="'+d['action']+'"><th scope="row">'+H(d['keyword'])+'</th><td>'+LABELS[d['action']]+'</td><td>'+H(values('Search Volume'))+'</td><td>'+H(values('Keyword Difficulty'))+'</td><td>'+destination+'</td><td>'+H(d['reason'])+'</td></tr>')
    dates=data['recordDates'];date_range=(dates[0]+' — '+dates[-1]) if dates else '未提供'
    document='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>HoopCut 关键词批量页面 · 本地审核</title><style>
    *{box-sizing:border-box}body{background:#10120f;color:#eff1e9;font:16px/1.65 system-ui;margin:0}main{max-width:1200px;margin:48px auto;padding:0 24px}a{color:#ffac84;text-underline-offset:4px}h1{font-size:clamp(28px,4vw,44px);line-height:1.2}h2{font-size:23px;line-height:1.35}.muted{color:#b7beb0}.tag{color:#ffac84;font-size:13px;letter-spacing:.4px}.stats,.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.stats{margin:28px 0}.stats>div,.card{padding:24px;border:1px solid #3c4335;background:#1a1e17;border-radius:16px}.stats strong{font-size:32px;display:block}.card{display:flex;flex-direction:column;gap:12px}.card p,.card h2{margin:0}.card p{font-size:14px;color:#bec5b6}.card .tag{color:#ffac84}.open{margin-top:auto;padding-top:10px;font-weight:650}.filters{display:flex;gap:12px;flex-wrap:wrap;margin:24px 0}label{display:flex;flex-direction:column;gap:7px}input,select{font:inherit;border:1px solid #5a6350;border-radius:8px;background:#22291d;color:#fff;padding:12px}input{min-width:260px}section{margin-top:44px}.table-wrap{overflow:auto}table{border-collapse:collapse;min-width:950px;width:100%;font-size:13px}td,th{padding:14px 12px;border-bottom:1px solid #3b4234;text-align:left;vertical-align:top}td:nth-child(5){max-width:240px;overflow-wrap:anywhere}th{font-weight:650}thead{background:#252c20}tr[hidden]{display:none}details{font-size:14px}summary{cursor:pointer}code{overflow-wrap:anywhere}a:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #ffac84;outline-offset:3px}@media(max-width:850px){.cards{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:560px){main{padding:0 16px;margin-top:28px}.stats,.cards{grid-template-columns:1fr}.stats{gap:10px}.stats>div{padding:16px}.card{padding:20px}}
    </style></head><body><main><p class="tag">HOOPCUT · LOCAL REVIEW</p><h1>同一个 Tracer 模板，批量承接不同需求</h1><p>'''+str(len(new))+' 个新增主题页 + '+str(len(selected)-len(new))+''' 个已做好的示例页。所有页面共用真实上传、选取片段、预览和导出功能。</p><p class="muted">仅本地草稿，未推送 GitHub、未上线、未提交 GSC。当前生产 sitemap 保持不变，草稿为 noindex。</p><div class="stats"><div><strong>'''+str(data['rows'])+'''</strong>CSV 排名记录</div><div><strong>'''+str(data['uniqueKeywords'])+'''</strong>去重后的独立关键词</div><div><strong>'''+str(mapped)+'''</strong>有承接路径的词</div></div><p class="muted">来源：'''+H(data['file'])+'；美国，Semrush 估算值。关键词记录日期：'+H(date_range)+'''。搜索量与 KD 按原值展示；未汇总重叠搜索量，不代表已获得自然流量。</p><p><a href="#pages">查看实际页面</a> · <a href="#keywords">查看全部关键词去向</a> · <a href="/shot-tracer/scenarios">打开页面目录</a></p><section id="pages"><h2>实际本地页面</h2><div class="cards">'''+''.join(blocks)+'''</div></section><section id="keywords"><h2>全部关键词去向</h2><p>同义词共用页面；现有工具继续承接对应需求。暂缓项保留原词和理由，等待适合的功能、数据或素材。</p><div class="filters"><label>搜索关键词或路径<input id="keyword-search" type="search" placeholder="例如 homecourt、tracer、play"></label><label>处理方式<select id="keyword-action"><option value="">全部</option>'''+''.join('<option value="'+k+'">'+v+'</option>' for k,v in LABELS.items())+'''</select></label></div><p id="result-count" aria-live="polite"></p><div class="table-wrap"><table><thead><tr><th>关键词</th><th>处理方式</th><th>搜索量（原值）</th><th>KD（原值）</th><th>目标页面</th><th>说明</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></div></section><section><h2>核对与发布</h2><p>采用独立TD、单一H1、H2/H3层级、canonical、面包屑和共享工具结构化数据。所有页面的验证记录随本地批次保存。批准具体版本后再推进发布。</p><p class="muted">批次：'''+H(manifest['batchId'])+'''</p></section></main><script>
    const search=document.getElementById('keyword-search'),action=document.getElementById('keyword-action'),rows=[...document.querySelectorAll('tbody tr')];function filter(){const q=search.value.trim().toLowerCase();let count=0;for(const row of rows){row.hidden=!!((action.value&&row.dataset.action!==action.value)||(q&&!row.textContent.toLowerCase().includes(q)));if(!row.hidden)count++}document.getElementById('result-count').textContent=`显示 ${count} / ${rows.length} 个关键词`}search.addEventListener('input',filter);action.addEventListener('change',filter);filter();
    </script></body></html>'''
    destination=root/'reports/tracer-keywords-review.html';destination.parent.mkdir(exist_ok=True);destination.write_text(document)
    return destination

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--batch',required=True);args=parser.parse_args();print(build_review(args.batch))
