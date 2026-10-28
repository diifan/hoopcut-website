#!/usr/bin/env python3
"""Build 15 useful static resource pages and integrate five original guides."""
import csv
import io
import json
import re
from html import escape as H
from pathlib import Path
from xml.etree import ElementTree as ET
from batch_one_content import GUIDES, RESOURCES, DATE
from resource_graphics import graphic, sheet_image, guide_image

ROOT=Path(__file__).resolve().parents[1]
BASE='https://hoopcut.ai'
ASSET=ROOT/'assets/resources'
ASSET.mkdir(parents=True,exist_ok=True)
(ROOT/'templates').mkdir(exist_ok=True)

def data_json(value):
    return json.dumps(value,ensure_ascii=False).replace('<','\\u003c').replace('&','\\u0026')

def video(item):
    s=item.get('slug') or item['keyword'].replace(' ','-')
    steps=item['videoSteps']
    return f'''<figure class="resource-video" id="walkthrough"><div><p class="eyebrow">ILLUSTRATED WALKTHROUGH · 9 SECONDS</p><h2>{H(item.get('short','See the planning approach'))}</h2></div><video controls playsinline muted preload="none" width="1200" height="800" poster="/assets/resources/{s}-poster.jpg" aria-label="Illustrated walkthrough: {H(item['title'],quote=True)}"><source src="/assets/resources/{s}.mp4" type="video/mp4"><track kind="captions" src="/assets/resources/{s}.vtt" srclang="en" label="English" default></video><figcaption>Original illustrated walkthrough using example data. It is not customer footage, an app screen recording or a measured result.</figcaption><details><summary>Read the walkthrough transcript</summary><ol>{''.join('<li>'+H(x)+'</li>' for x in steps)}</ol></details></figure>'''

def workspace(r):
    s=r['slug']
    if r['kind']=='graphic':
        editor='<div class="graphic-fields">'+''.join(f'<label for="field-{i}">{H(label)}<input id="field-{i}" data-field="{i}" value="{H(value,quote=True)}" maxlength="{6 if i==1 and r["layout"]!="certificate" else 72 if i==3 and r["layout"]=="certificate" else 44}"></label>' for i,(label,value) in enumerate(r['fields']))+'<label for="accent">Accent color<select id="accent"><option value="#ad4726">Terracotta</option><option value="#244e41">Forest</option><option value="#334f8a">Court blue</option><option value="#752d40">Burgundy</option></select></label></div>'
        preview='<div id="graphic-preview" class="graphic-preview">'+graphic(r)+'</div>'
        tools='<button type="button" data-export="svg">Download SVG</button><button type="button" data-export="png">Download PNG</button>'
        fallback=f'<a download href="/assets/resources/{s}.svg">Download the original example SVG</a>'
    else:
        editor='<div class="table-wrap"><table id="resource-table"><caption>'+H(r['short'])+' — editable example data</caption><thead><tr>'+''.join('<th scope="col">'+H(c)+'</th>' for c in r['columns'])+'<th scope="col" class="screen-only">Actions</th></tr></thead><tbody>'+''.join('<tr>'+''.join('<td><textarea rows="2" maxlength="500" aria-label="Row '+str(j+1)+': '+H(c,quote=True)+'">'+H(v)+'</textarea></td>' for c,v in zip(r['columns'],row))+'<td class="screen-only"><button type="button" data-remove aria-label="Remove row '+str(j+1)+'">Remove</button></td></tr>' for j,row in enumerate(r['rows']))+'</tbody></table></div>'
        preview='<div class="calculation" id="budget-total" role="status" aria-live="polite"></div>' if r['kind']=='budget' else ''
        tools='<button type="button" id="add-row">Add row</button><button type="button" data-export="csv">Download CSV</button>'
        fallback=f'<a download href="/assets/resources/{s}.csv">Download the original example CSV</a>'
    return f'''<section id="workspace" class="workspace"><header><div><p class="eyebrow">MAKE IT YOURS</p><h2>{H(r['short'])}</h2></div><span>Browser editor · no sign-in</span></header><p class="editor-note">Start with the fictional example and replace the details. Edits stay in this page and are lost on refresh; download a copy to keep your work.</p><div class="editor {('graphic-editor' if r['kind']=='graphic' else 'sheet-editor')}">{editor}{preview}</div><div class="toolbar js-tools" hidden>{tools}<button type="button" id="print-resource">Print</button><button type="button" id="reset-resource">Reset example</button></div><p id="editor-status" role="status" aria-live="polite"></p><div class="fallback-download">{fallback}<span> · Unedited sample; replace fictional details before use.</span></div><noscript><p>The live editor needs JavaScript. You can still read the guide and download the editable original above.</p></noscript></section>'''

def render_resources():
    from build_blog import head,navigation,footer
    for r in RESOURCES:
        s=r['slug'];url=BASE+'/templates/'+s
        svg=graphic(r) if r['kind']=='graphic' else sheet_image(r)
        (ASSET/(s+'.svg')).write_text(svg)
        if r['kind']!='graphic':
            with (ASSET/(s+'.csv')).open('w',newline='') as f:
                w=csv.writer(f,lineterminator='\n');w.writerow(r['columns']);w.writerows(r['rows'])
        graph=[{'@type':'WebPage','@id':url+'#page','url':url,'name':r['title'],'description':r['description'],'inLanguage':'en','image':BASE+'/assets/resources/'+s+'.jpg','dateModified':DATE,'author':{'@type':'Organization','name':'Hoopcut','url':BASE+'/'},'mainEntity':{'@type':'CreativeWork','name':r['title'],'description':'Original editable planning resource with fictional example data.','isAccessibleForFree':True}}, {'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'Home','item':BASE+'/'},{'@type':'ListItem','position':2,'name':'Tools','item':BASE+'/tools'},{'@type':'ListItem','position':3,'name':r['short'],'item':url}]}]
        steps=''.join(f'<section id="use-{i}"><p class="eyebrow">STEP {i:02d}</p><h2>{H(t)}</h2><p>{H(p)}</p></section>' for i,(t,p) in enumerate(r['steps'],1))
        sources=''.join('<li><a href="'+H(u,quote=True)+'">'+H(t)+'</a></li>' for t,u in r.get('sources',[]))
        sources=f'<section id="sources"><h2>Source notes</h2><ul>{sources}</ul><p>The template, example data and workflow are original editorial resources. Local organization rules in a source are not universal requirements.</p></section>' if sources else ''
        links=''.join('<a href="'+H(u,quote=True)+'">'+H(t)+' <span aria-hidden="true">↗</span></a>' for t,u in r['links'])
        config={k:r[k] for k in ('slug','kind','rows','columns','fields') if k in r}
        markup=head(r['title']+' | Hoopcut',r['description'],url,graph,'/assets/resources/'+s+'.jpg',r['short']+' with fictional example details')
        markup=markup.replace('</head>','<link rel="stylesheet" href="/assets/resources/resources.css"><script src="/assets/resources/editor.js" defer></script></head>')
        markup+=navigation()+f'''<main id="main" class="resource-page"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a><span aria-hidden="true">/</span><a href="/tools">Tools</a><span aria-hidden="true">/</span><span aria-current="page">{H(r['short'])}</span></nav><header class="resource-hero"><div><p class="eyebrow">THE HOOPCUT TOOLKIT / {H(r['category'])}</p><h1>{H(r['title'])}</h1><p class="lede">{H(r['intro'])}</p><a class="jump-button" href="#workspace">{'Personalize the design' if r['kind']=='graphic' else 'Edit the worksheet'} <span aria-hidden="true">↓</span></a></div><img src="/assets/resources/{s}.jpg" width="1200" height="800" alt="{H(r['short'],quote=True)} preview with fictional example data" fetchpriority="high" decoding="async"></header><nav class="resource-anchor-nav" aria-label="On this page"><a href="#workspace">Editor & downloads</a><a href="#use-1">How to use it</a><a href="#walkthrough">Video walkthrough</a><a href="#questions">Questions</a></nav>{workspace(r)}<div class="resource-reading"><article id="resource-guide">{steps}<section id="example"><h2>Read the example</h2><p>{H(r['example'])}</p></section><aside class="resource-caution"><h2>One thing to check</h2><p>{H(r['mistake'])}</p></aside>{video(r)}<section id="questions"><h2>Practical questions</h2>{''.join('<h3>'+H(q)+'</h3><p>'+H(a)+'</p>' for q,a in r['faq'])}<h3>Are these additional Hoopcut app features?</h3><p>These are free browser planning and design resources. Hoopcut’s app focuses on basketball auto clipping and Shot Tracer. The editor does not upload video or publish to a social account.</p></section>{sources}<p class="byline">Original resource by Hoopcut · Updated <time datetime="{DATE}">October 27, 2026</time></p></article><aside class="resource-related"><p class="eyebrow">NEXT IN YOUR WORKFLOW</p>{links}<a href="/tools">Browse all editable resources →</a></aside></div></main>'''+footer()+f'<script id="resource-data" type="application/json">{data_json(config)}</script></body></html>'
        if r['kind']=='graphic':
            w,h={'cover':(1080,1920),'poster':(1200,1500),'recruiting':(1200,675),'table-card':(1200,800),'memory':(1000,1400),'certificate':(1200,800)}[r['layout']]
            markup=markup.replace('class="resource-page"',f'class="resource-page graphic-resource graphic-{r["layout"]}"')
            markup=markup.replace(f'<img src="/assets/resources/{s}.jpg" width="1200" height="800"',f'<img src="/assets/resources/{s}-preview.jpg" width="{w}" height="{h}"')
        (ROOT/'templates'/(s+'.html')).write_text(markup)

def integrate_guides():
    articles=json.loads((ROOT/'content/blog/articles.json').read_text())
    # Only replace this batch's own records; preserve existing editorial content.
    batch_keywords={a['keyword'] for a in GUIDES}
    articles=[a for a in articles if a['keyword'] not in batch_keywords]
    seo_titles=['How to Film Basketball Games: Camera Setup | Hoopcut','How to Record Basketball Practice Alone | Hoopcut','Basketball Senior Night Poster Ideas & Layouts | Hoopcut','Basketball Senior Night Gift Ideas & Budget | Hoopcut','Basketball Senior Night Table Ideas & Layout | Hoopcut']
    for i,a in enumerate(GUIDES):
        a=dict(a);s=a['keyword'].replace(' ','-')
        a.update(seoTitle=seo_titles[i],datePublished=DATE,dateModified=DATE,reference='the workflow',checklistTitle='Before you begin',
                 productNote='Hoopcut focuses on basketball auto clipping and Shot Tracer on iPhone. The browser resources linked here are separate planning aids, not additional app capabilities.')
        a['visual']={'image':'/assets/resources/'+s+'.jpg','alt':a['title']+' — original illustrated planning diagram','caption':'Original planning illustration, not a customer photo, venue survey or measured product result.','overviewTitle':'A PRACTICAL STARTING POINT','tiles':[[h,p.split('. ')[0]+'.'] for h,p in a['sections'][:3]]}
        (ASSET/(s+'.svg')).write_text(guide_image(a,i))
        articles.append(a)
    (ROOT/'content/blog/articles.json').write_text(json.dumps(articles,ensure_ascii=False,indent=2)+'\n')
    from build_blog import build
    # Module reads the authored JSON after it has been saved.
    build()
    for i,a in enumerate(GUIDES):
        s=a['keyword'].replace(' ','-');f=ROOT/'blog'/(s+'.html');source=f.read_text()
        item=dict(a,videoSteps=[x[0] for x in a['sections'][:3]])
        source=source.replace('<section id="checklist">',video(item)+'<section id="checklist">')
        source=source.replace('</head>','<link rel="stylesheet" href="/assets/resources/resources.css"></head>')
        f.write_text(source)

def resource_cards():
    selected=[r for r in RESOURCES if r['slug'] in ['basketball-clip-log','basketball-reel-cover','basketball-senior-night-poster']]
    return '<section class="topic-section" id="templates"><div class="section-label"><h2>Put the guide into practice.</h2><a href="/tools">Explore all 15 tools →</a></div><p>Ready to make something? Open a free tool to plan your clips or personalize a player graphic.</p><div class="cards">'+''.join(f'<article class="card"><img class="card-cover" src="/assets/resources/{r["slug"]}.jpg" loading="lazy" decoding="async" width="1200" height="800" alt="{H(r["short"],quote=True)} example"><p class="eyebrow">FREE BASKETBALL TOOL</p><h3><a href="/templates/{r["slug"]}">{H(r["short"])}</a></h3><p>{H(r["description"])}</p></article>' for r in selected)+'</div></section>'

def build():
    integrate_guides()
    render_resources()
    f=ROOT/'blog/index.html';src=f.read_text().replace('</main>',resource_cards()+'</main>');f.write_text(src)
    from tools_hub import build_tools,integrate_site
    build_tools()
    integrate_site()
    tree=ET.parse(ROOT/'sitemap.xml');root=tree.getroot();ns='{http://www.sitemaps.org/schemas/sitemap/0.9}'
    urls={x.text for x in root.findall('{*}url/{*}loc')}
    for path in ['/tools']+['/templates/'+r['slug'] for r in RESOURCES]:
        url=BASE+path
        if url not in urls:
            node=ET.SubElement(root,ns+'url');ET.SubElement(node,ns+'loc').text=url
    changed={BASE+'/blog/'+a['keyword'].replace(' ','-') for a in GUIDES}|{BASE+'/templates/'+r['slug'] for r in RESOURCES}|{BASE+'/',BASE+'/blog',BASE+'/tools'}
    for node in root:
        if node.find(ns+'loc').text in changed:
            stamp=node.find(ns+'lastmod')
            if stamp is None:stamp=ET.SubElement(node,ns+'lastmod')
            stamp.text=DATE
    ET.register_namespace('',ns[1:-1]);tree.write(ROOT/'sitemap.xml',encoding='utf-8',xml_declaration=True)
    (ROOT/'content/blog/batch-one-resources.json').write_text(json.dumps({'date':DATE,'status':'local review only','resources':RESOURCES},ensure_ascii=False,indent=2)+'\n')
    review_items=[{'url':'/blog/'+a['keyword'].replace(' ','-'),'title':a['title'],'slug':a['keyword'].replace(' ','-'),'category':'专项指南'} for a in GUIDES]+[{'url':'/templates/'+r['slug'],'title':r['title'],'slug':r['slug'],'category':'图形模板 · SVG / PNG' if r['kind']=='graphic' else '编辑表格 · CSV / 打印'} for r in RESOURCES]
    review='<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>首批 20 页 · 本地审核</title><link rel="stylesheet" href="/assets/blog/blog.css"></head><body><main style="padding-top:50px;padding-bottom:60px"><p class="eyebrow">LOCAL REVIEW / BATCH 01</p><h1>首批 20 个新页面</h1><p class="lede">5 篇专项指南 + 15 个可编辑资源页。仅供本地审核，尚未提交 GitHub、部署或提交 GSC。</p><p>图片为原创图示和模板设计；视频为带字幕的图解步骤，不冒充用户素材或 App 实录。模板示例使用虚构信息，编辑后可下载或打印。</p><p><a href="/tools">查看正式资源入口 →</a> · <a href="/">查看首页 →</a></p><div class="cards">'+''.join('<article class="card"><img class="card-cover" loading="lazy" width="1200" height="800" alt="'+H(x['title'],quote=True)+'" src="/assets/resources/'+x['slug']+'.jpg"><p class="eyebrow">'+str(i).zfill(2)+' / '+x['category']+'</p><h2 style="font-size:23px"><a href="'+x['url']+'">'+H(x['title'])+'</a></h2><p>'+x['url']+'</p></article>' for i,x in enumerate(review_items,1))+'</div></main></body></html>'
    (ROOT/'reports').mkdir(exist_ok=True)
    (ROOT/'reports/batch-one-review.html').write_text(review)
    designs='<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>图形模板 · 本地视觉审核</title><link rel="stylesheet" href="/assets/blog/blog.css"><style>.design-grid .card{padding:20px}.design-grid img{width:100%;height:380px;object-fit:contain;background:#141a17;border-radius:6px;margin-bottom:20px}.design-grid h2{font-size:23px}.design-grid p{margin-bottom:15px}</style></head><body><main style="padding-top:45px;padding-bottom:60px"><p class="eyebrow">HOOPCUT / LOCAL DESIGN REVIEW</p><h1>六类图形模板 · 新版</h1><p class="lede">按使用场景重新设计排版、字体和色块。点击进入实际编辑页，修改姓名、号码或配色后可下载、打印。仅本地预览。</p><div class="cards design-grid">'+''.join('<article class="card"><img width="1200" height="800" loading="lazy" alt="'+H(r['short'],quote=True)+'新版设计" src="/assets/resources/'+r['slug']+'-preview.jpg"><h2><a href="/templates/'+r['slug']+'?design=3">'+H(r['title'])+'</a></h2><p>可编辑 · SVG / PNG · 打印</p></article>' for r in RESOURCES if r['kind']=='graphic')+'</div><p><a href="/reports/batch-one-review">返回首批 20 页审核目录 →</a></p></main></body></html>'
    (ROOT/'reports/graphic-templates-review.html').write_text(designs)
    # This final pass is part of every complete build, so future content changes
    # cannot silently remove access, schema, media or analytics improvements.
    import subprocess
    import shutil
    node=shutil.which('node') or str(Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node')
    subprocess.run([node,str(ROOT/'scripts/optimize_media.cjs')],check=True)
    from polish_site import build as polish
    polish()
    print('Built first batch: 5 new guides + 15 distinct editable resource pages. No publishing action.')

if __name__=='__main__': build()
