#!/usr/bin/env python3
"""Data-driven HomeCourt resource family + contextual existing-page updates.
No publishing, live account access, invented demand or site-wide brand stuffing.
"""
import csv,hashlib,json,re,subprocess
from html import escape as H
from pathlib import Path
from xml.etree import ElementTree as ET
from build_blog import head,navigation,footer
ROOT=Path(__file__).resolve().parents[1]
BASE='https://hoopcut.ai'
DATE='2026-11-11'
DATA=json.loads((ROOT/'content/homecourt/pages.json').read_text())
PAGES=DATA['pages'];SOURCES=DATA['sources'];BY_SLUG={p['slug']:p for p in PAGES}
MAP=json.loads((ROOT/'content/homecourt/existing-pages.json').read_text())
CATEGORIES={'Choose your workflow':'choose','Set up & troubleshoot':'setup','Video & sharing':'video','Practice & records':'practice'}

def js(v):return json.dumps(v,ensure_ascii=False).replace('<','\\u003c')
def link(label,url):return '<a href="'+H(url,quote=True)+'">'+H(label)+'</a>'
def pathfile(path):return ROOT/('index.html' if path=='/' else 'blog/index.html' if path=='/blog' else path.lstrip('/')+'.html')
def crumbs(title=None):
 parts=[('Home','/'),('HomeCourt guides','/homecourt')]
 if title:parts.append((title,None))
 return '<nav class="breadcrumbs" aria-label="Breadcrumb">'+'<span aria-hidden="true">/</span>'.join(link(t,u) if u and (title or u!='/homecourt') else '<span aria-current="page">'+H(t)+'</span>' for t,u in parts)+'</nav>'
def breadcrumb(path,title):
 items=[('Home',BASE+'/'),('HomeCourt guides',BASE+'/homecourt')]
 if path!='/homecourt':items.append((title,BASE+path))
 return {'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':i,'name':t,'item':u} for i,(t,u) in enumerate(items,1)]}
def shell(title,desc,path,graph,body,slug='index'):
 css=hashlib.sha256((ROOT/'assets/homecourt/homecourt.css').read_bytes()).hexdigest()[:10]
 digest=hashlib.sha256((ROOT/'assets/homecourt/homecourt.js').read_bytes()).hexdigest()[:10]
 settings=json.loads((ROOT/'content/site-config.json').read_text())['analytics']
 top=head(title+' | Hoopcut',desc,BASE+path,graph,'/assets/homecourt/'+slug+'-social.png','Hoopcut independent HomeCourt guide: '+title)
 top=top.replace('</head>','<meta name="robots" content="index,follow,max-image-preview:large"><link rel="stylesheet" href="/assets/homecourt/homecourt.css?v='+css+'"><script id="site-settings" type="application/json">'+js({'analytics':settings})+'</script><script src="/assets/site-events.js" defer></script><script src="/assets/homecourt/homecourt.js?v='+digest+'" defer></script></head>').replace('<body>','<body class="hc-page">')
 return '<!-- GENERATED HOMECOURT RESOURCE: edit content/homecourt/pages.json -->'+top+navigation()+'<main id="main">'+body+'</main>'+footer()+'</body></html>'
def card(p,i=1):
 return '<article class="hc-card" data-hc-card data-category="'+H(p['category'])+'"><span class="hc-index">'+str(i).zfill(2)+' / '+H(p['category'].upper())+'</span><h3>'+link(p['title'],'/homecourt/'+p['slug'])+'</h3><p>'+H(p['description'])+'</p><a class="hc-card-link" href="/homecourt/'+p['slug']+'">'+('Choose your next step' if p['widget']=='decision' else 'Use the cost calculator' if p['widget']=='cost' else 'Read guide & use checklist')+' ↗</a></article>'
def checklist(p):
 return '<section class="hc-widget" id="hc-checklist" aria-labelledby="hc-check-title"><p class="hc-eyebrow">TAKE IT TO PRACTICE</p><h2 id="hc-check-title">Your next-step checklist.</h2><div class="hc-check-list">'+''.join('<label class="hc-check"><input type="checkbox" data-hc-check><span>'+H(t)+'</span></label>' for t in p['checklist'])+'</div><output id="hc-progress" aria-live="polite">0 of '+str(len(p['checklist']))+' checks complete</output><p class="hc-small" id="hc-storage">Checklist progress saves in this browser when storage is available.</p><div class="hc-actions"><button id="hc-download" type="button" class="primary">Download checklist ↓</button><button type="button" id="hc-reset">Reset checks</button></div><noscript><p>Read or print this checklist. Saving and downloading progress require JavaScript.</p></noscript></section>'
def choices(p):
 if not p['choices']:return ''
 return '<section class="hc-widget" id="choose" aria-labelledby="hc-choice-title"><p class="hc-eyebrow">START WITH YOUR SITUATION</p><h2 id="hc-choice-title">What do you need to do?</h2><div class="hc-choices">'+''.join('<details><summary>'+H(c['label'])+'</summary><p>'+H(c['answer'])+'</p>'+link(c['link']+' ↗',c['url'])+'</details>' for c in p['choices'])+'</div><p class="hc-small">These options guide your next check. They do not inspect your account or diagnose a recording automatically.</p></section>'
def cost():
 return '''<section class="hc-widget" id="hc-cost" aria-labelledby="hc-cost-title"><p class="hc-eyebrow">USE YOUR ACTUAL OFFER</p><h2 id="hc-cost-title">Cost per practice session.</h2><p>Enter the total charge for one billing period. Use the same currency throughout. No assumed HomeCourt price is prefilled.</p><div class="hc-calculator"><label for="hc-price">Price per billing period<input id="hc-price" type="number" min="0" max="1000000" step="0.01" inputmode="decimal" placeholder="Enter your price"></label><label for="hc-months">Billing period<select id="hc-months"><option value="1">1 month</option><option value="3">3 months</option><option value="12">12 months</option></select></label><label for="hc-sessions">Expected sessions each month<input id="hc-sessions" type="number" min="1" max="10000" step="1" inputmode="numeric" placeholder="Enter session count"></label></div><output id="hc-cost-result" aria-live="polite">Enter your price and sessions to calculate.</output><p class="hc-small">Formula: price ÷ months in the billing period ÷ expected sessions per month. This calculator does not collect payment details or check a subscription.</p><noscript><p>Use the formula above; interactive calculation requires JavaScript.</p></noscript></section>'''
def table(p):
 t=p.get('table')
 if not t:return ''
 return '<section id="comparison"><h2>'+H(t.get('heading','Compare the job, not just the label.'))+'</h2><div class="hc-table-wrap" role="region" aria-label="Workflow comparison" tabindex="0"><table><thead><tr>'+''.join('<th scope="col">'+H(x)+'</th>' for x in t['headers'])+'</tr></thead><tbody>'+''.join('<tr>'+''.join(('<th scope="row">' if i==0 else '<td>')+H(x)+('</th>' if i==0 else '</td>') for i,x in enumerate(row))+'</tr>' for row in t['rows'])+'</tbody></table></div></section>'
def source_html(p):
 return '<section class="hc-sources" id="sources"><h2>Sources & scope.</h2><p>Prepared by Hoopcut from public documentation, reviewed November 11, 2026. We have not tested these instructions inside a signed-in HomeCourt account. Official documents may describe older app menus; follow the current controls and confirm account-specific details with the provider.</p><ul>'+''.join('<li>'+link(SOURCES[s]['title'],SOURCES[s]['url'])+'<span>'+H(SOURCES[s]['note'])+'</span></li>' for s in p['sources'])+'</ul><p class="hc-small">Independent guide by Hoopcut. Not affiliated with or endorsed by HomeCourt. HomeCourt account, billing and recovery requests must go to the relevant provider.</p></section>'
def page(p):
 path='/homecourt/'+p['slug'];url=BASE+path
 graph=[{'@type':'Article','@id':url+'#article','url':url,'headline':p['title'],'description':p['description'],'inLanguage':'en','dateModified':DATE,'author':{'@type':'Organization','name':'Hoopcut','url':BASE+'/'},'publisher':{'@type':'Organization','name':'Hoopcut','url':BASE+'/'},'image':BASE+'/assets/homecourt/'+p['slug']+'-social.png','citation':[SOURCES[s]['url'] for s in p['sources']]},breadcrumb(path,p['title'])]
 hero='<header class="hc-hero"><div><p class="hc-eyebrow">HOMECOURT FIELD GUIDE / '+H(p['category'])+'</p><h1>'+H(p['title'])+'</h1><p class="hc-intro">'+H(p['intro'])+'</p><a class="hc-button primary" href="#'+('choose' if p['widget']=='decision' else 'hc-cost' if p['widget']=='cost' else 'hc-checklist')+'">'+('Find your next step' if p['widget']=='decision' else 'Calculate your cost' if p['widget']=='cost' else 'Use the checklist')+' ↓</a><p class="hc-byline">By Hoopcut · Reviewed <time datetime="'+DATE+'">Nov 11, 2026</time><br>Independent guide · Official references below</p></div><figure><img src="/assets/homecourt/'+CATEGORIES[p['category']]+'.svg" width="640" height="480" alt="'+H({'choose':'Workflow routes for training, basketball records and video editing','setup':'Illustrated basketball camera framing plan; not an app screenshot','video':'Workflow from source recording to selected clips and a shareable edit','practice':'Illustrated practice record; sample markers are not real results'}[CATEGORIES[p['category']]])+'" fetchpriority="high"><figcaption>Original Hoopcut illustration · '+('Example markers, not player results' if p['category']=='Practice & records' else 'Workflow reference, not an app screenshot')+'</figcaption></figure></header>'
 answer='<section class="hc-answer" id="quick-answer"><h2>The quick answer</h2><p>'+H(p['answer'])+'</p></section>'
 sections=''.join('<section id="step-'+str(i)+'"><h2>'+H(s['heading'])+'</h2><p>'+H(s['body'])+'</p></section>' for i,s in enumerate(p['sections'],1))
 store=json.loads((ROOT/'content/site-config.json').read_text())['app']['appStoreUrl']
 sidebar='<aside class="hc-aside"><div class="hc-aside-section"><h2>In this guide</h2><nav aria-label="On this page"><a href="#quick-answer">Quick answer</a>'+''.join(link(s['heading'],'#step-'+str(i)) for i,s in enumerate(p['sections'],1))+'<a href="#hc-checklist">Your checklist</a><a href="#sources">Sources & scope</a></nav></div><div class="hc-aside-section"><h2>Make the next move</h2><p>'+H(p['cta']['label'])+'.</p><a class="hc-button primary" href="'+H(p['cta']['url'])+'">Open resource ↗</a></div><div class="hc-aside-section"><h2>Keep your moments</h2><p>Hoopcut on iPhone provides basketball auto clipping and Shot Tracer. Browser worksheets and shot charts are separate tools.</p><a href="'+H(store)+'" data-app-access="app-store">Explore Hoopcut on the App Store ↗</a></div></aside>'
 related='<section class="hc-related"><p class="hc-eyebrow">KEEP MOVING</p><h2>Related HomeCourt guides.</h2><div class="hc-grid">'+''.join(card(BY_SLUG[s],i) for i,s in enumerate(p['related'],1))+'</div><p>'+link('Browse all HomeCourt guides →','/homecourt')+'</p></section>'
 return shell(p['title'],p['description'],path,graph,crumbs(p['title'])+hero+'<div class="hc-layout"><article class="hc-article">'+answer+choices(p)+(cost() if p['widget']=='cost' else '')+table(p)+sections+checklist(p)+source_html(p)+'</article>'+sidebar+'</div>'+related,p['slug'])
def hub():
 title='HomeCourt Guides, Alternatives & Basketball Workflows';desc='Independent HomeCourt guides for camera setup, video exports, shot records and alternatives. Find an answer, use a checklist and choose your next basketball tool.'
 graph=[{'@type':'CollectionPage','@id':BASE+'/homecourt#page','url':BASE+'/homecourt','name':title,'description':desc,'inLanguage':'en'},breadcrumb('/homecourt',title),{'@type':'ItemList','numberOfItems':len(PAGES),'itemListElement':[{'@type':'ListItem','position':i,'name':p['title'],'url':BASE+'/homecourt/'+p['slug']} for i,p in enumerate(PAGES,1)]}]
 hero='''<header class="hc-hero"><div><p class="hc-eyebrow">THE HOOPCUT FIELD GUIDE</p><h1>Your next move<br>with HomeCourt.</h1><p class="hc-intro">Set up the session. Keep the record. Make something worth sharing. Practical answers for the basketball task in front of you.</p><a class="hc-button primary" href="#guides">Find your guide ↓</a><a class="hc-button" href="/homecourt/alternatives">Compare your options ↗</a><p class="hc-byline">Independent resources by Hoopcut.<br>Not affiliated with or endorsed by HomeCourt.</p></div><figure><img src="/assets/homecourt/choose.svg" width="640" height="480" alt="Three basketball workflow routes: train, keep a record and create a video" fetchpriority="high"><figcaption>Choose the result you want to leave the court with.</figcaption></figure></header><div class="hc-feature-strip"><span>OFFICIAL SOURCE REFERENCES</span><span>USEFUL CHECKLISTS</span><span>FREE BROWSER RESOURCES</span></div>'''
 grid='<section id="guides"><div class="hc-hub-intro"><div><p class="hc-eyebrow">FIND YOUR STARTING POINT</p><h2>One question. A useful next step.</h2></div><label class="hc-search" for="hc-search">Search the guides<input id="hc-search" type="search" placeholder="Try video, Android, camera…" autocomplete="off"></label></div><div class="hc-filters" aria-label="Filter guides"><button type="button" data-category-filter="all" aria-pressed="true">All guides</button>'+''.join('<button type="button" data-category-filter="'+H(c)+'" aria-pressed="false">'+H(c)+'</button>' for c in CATEGORIES)+'</div><p class="hc-result-count" id="hc-count" aria-live="polite">'+str(len(PAGES))+' guides</p><div class="hc-grid">'+''.join(card(p,i) for i,p in enumerate(PAGES,1))+'</div><p id="hc-empty" hidden>No matching guides. Try a shorter phrase or choose All guides.</p></section>'
 notice='<section class="hc-sources"><h2>Training, records and highlights are different jobs.</h2><p>HomeCourt publishes basketball training and camera-analysis features. Hoopcut focuses on auto clipping and Shot Tracer for iPhone. Our browser tools help with planning and manual records. Each guide identifies the task it can help with and links to the relevant source or tool.</p><p class="hc-notice">Sources reviewed November 11, 2026. Public documentation is not a signed-in product test, and older instructions may differ from the app on your device. For account changes or billing, use the provider’s official support. No customer results or comparative performance scores are implied.</p><p>'+link('HomeCourt official help center','https://help.homecourt.ai/hc/en-us')+' · '+link('Hoopcut browser tools','/tools')+'</p></section>'
 return shell(title,desc,'/homecourt',graph,crumbs()+hero+grid+notice)
def integrate():
 for item in MAP:
  f=pathfile(item['path']);assert f.is_file(),f
  text=f.read_text();text=re.sub(r'<!-- HOMECOURT CONTEXT START -->.*?<!-- HOMECOURT CONTEXT END -->','',text,flags=re.S)
  block='<!-- HOMECOURT CONTEXT START --><section class="hc-context" id="homecourt-context" aria-labelledby="homecourt-context-title"><h2 id="homecourt-context-title">'+H(item['heading'])+'</h2><p>'+H(item['text'])+'</p><ul>'+''.join('<li>'+link(t+' ↗',u)+'</li>' for t,u in item['links'])+'</ul></section><!-- HOMECOURT CONTEXT END -->'
  if item['path']=='/':
   assert '<div class="end">' in text;text=text.replace('<div class="end">',block+'<div class="end">',1)
  elif item['path'].startswith('/blog/'):
   assert '</article>' in text;text=text.replace('</article>',block+'</article>',1)
  else:
   assert '</main>' in text;text=text.replace('</main>',block+'</main>',1)
  text=re.sub(r'<link[^>]+href="/assets/(?:homecourt/homecourt|static/homecourt\.[a-f0-9]+)\.css[^"]*"[^>]*>','',text)
  digest=hashlib.sha256((ROOT/'assets/homecourt/homecourt.css').read_bytes()).hexdigest()[:10]
  text=text.replace('</head>','<link rel="stylesheet" href="/assets/homecourt/homecourt.css?v='+digest+'"></head>',1)
  f.write_text(text)

def reports():
 out=ROOT/'reports/homecourt';out.mkdir(parents=True,exist_ok=True)
 rows=[]
 for p in PAGES:
  for i,q in enumerate(p['keywords']):rows.append({'query':q,'intent_cluster':p['slug'],'target_url':BASE+'/homecourt/'+p['slug'],'role':'primary' if i==0 else 'same-intent variant','evidence':'official documentation / public search candidate','volume':'unknown','kd':'unknown','market':'US English target; not geo-controlled rank data'})
 for m in MAP:
  rows.append({'query':m['heading'],'intent_cluster':'existing-page-context','target_url':BASE+m['path'],'role':'contextual update; primary topic unchanged','evidence':'existing relevant workflow','volume':'unknown','kd':'unknown','market':'US English target'})
 for name,values in [('keyword-map.csv',rows),('existing-page-map.csv',[{'path':m['path'],'heading':m['heading'],'targets':' | '.join(u for _,u in m['links'])} for m in MAP])]:
  with (out/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(values[0]));w.writeheader();w.writerows(values)
 record={'date':DATE,'new_pages':len(PAGES)+1,'new_guides':len(PAGES),'existing_pages_updated':len(MAP),'candidate_queries':sum(len(p['keywords']) for p in PAGES),'sources':SOURCES,'public_research_limitations':['No Semrush CSV or measured volume/KD','No new GSC performance query export in this run','Search results not controlled US Google ranking observations','Official help includes historical instructions; no authenticated HomeCourt UI test'],'excluded':['Homecourt home cleaning brand','NBA Street Homecourt game','Unverified claims that HomeCourt is discontinued','Unverified pricing and device minima','Automatic account sync or migration claims'],'merged':['free alternatives / apps like HomeCourt → alternatives','wrong shot outcome / wrong location → edit-shot-chart','missing videos / playback failure → video-not-loading'],'actions':[{'url':'/homecourt/'+p['slug'],'intent':p['keywords'][0],'template':p['widget'],'evidence':p['sources']} for p in PAGES]}
 (out/'research.json').write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n')
 body='<main id="main"><p class="hc-eyebrow">LOCAL REVIEW / HC-HOMECOURT-2026-11-11-01</p><h1>HomeCourt 流量专题 · 本地审核</h1><p>15 个独立需求指南 + 1 个专题中心，12 个已有页面加入相关内容。另包含已完成、未上线的球场图和投篮记录工具。原始工作区未修改。</p><p>55 个候选查询表达，搜索量与 KD 均未知；官方需求说明不等于已验证搜索量。本次没有推送、部署或提交索引。</p><p>'+link('打开完整专题中心 →','/homecourt')+' · '+link('查看首页 →','/')+'</p><div class="hc-table-wrap"><table><thead><tr><th>页面与需求</th><th>交互 / 模板</th><th>公开依据</th></tr></thead><tbody>'+''.join('<tr><td>'+link(p['title'],'/homecourt/'+p['slug'])+'<br><code>'+H(', '.join(p['keywords']))+'</code></td><td>'+H(p['widget'])+' + 本地清单下载</td><td>'+', '.join(link(SOURCES[s]['title'],SOURCES[s]['url']) for s in p['sources'])+'</td></tr>' for p in PAGES)+'</tbody></table></div><h2>现有页面改动</h2><ul>'+''.join('<li>'+link(m['path'],m['path']+'#homecourt-context')+' — '+H(m['heading'])+'</li>' for m in MAP)+'</ul><h2>数据与边界</h2><p>旧资料中的设备要求有不一致，未硬写当前最低系统版本；价格页标注美国 App Store 公开价格与核查日期，计算器不预填报价。排查步骤是公开依据与原创建议，不声称实测修复成功。没有评论或虚构评分。仅保留通过证据检查的不同需求，不做同义页面。</p><p>发布后才按匹配窗口观察 HomeCourt 查询点击、专题落地页点击、发现/抓取/收录；当前没有增长结果。浏览器清单只保存在本机，下载文件不是训练数据。站点分析开关保持原有关闭状态。</p></main>'
 (out/'review.html').write_text('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>HomeCourt 本地审核</title><link rel="stylesheet" href="/assets/blog/blog.css"><link rel="stylesheet" href="/assets/homecourt/homecourt.css"></head><body class="hc-page hc-review">'+body+'</body></html>')

def build():
 assert len(BY_SLUG)==len(PAGES)
 aliases=[re.sub(r'\s+',' ',q.lower().replace('home court','homecourt')).strip() for p in PAGES for q in p['keywords']]
 assert len(aliases)==len(set(aliases)), 'Duplicate keyword aliases: merge the intent rather than generate competing pages'
 assert len({p['title'] for p in PAGES})==len(PAGES)
 assert len({p['description'] for p in PAGES})==len(PAGES)
 for p in PAGES:
  assert p['sources'] and p['keywords'] and len(p['sections'])>=3
  assert set(p['sources']).issubset(SOURCES)
  assert set(p['related']).issubset(BY_SLUG)
 (ROOT/'homecourt').mkdir(exist_ok=True)
 for old in (ROOT/'homecourt').glob('*.html'):
  if old.stem not in BY_SLUG:
   assert 'GENERATED HOMECOURT RESOURCE' in old.read_text(), 'Refusing to remove an unowned page: '+str(old)
   old.unlink()
 subprocess.run(['node',str(ROOT/'scripts/build_homecourt_media.cjs')],check=True)
 for p in PAGES:(ROOT/'homecourt'/(p['slug']+'.html')).write_text(page(p))
 (ROOT/'homecourt.html').write_text(hub());integrate()
 tree=ET.parse(ROOT/'sitemap.xml');root=tree.getroot();ns='{http://www.sitemaps.org/schemas/sitemap/0.9}'
 allowed={BASE+'/homecourt'}|{BASE+'/homecourt/'+p['slug'] for p in PAGES}
 for node in list(root):
  loc=node.findtext(ns+'loc') or ''
  if loc.startswith(BASE+'/homecourt/') and loc not in allowed:root.remove(node)
 paths=['/homecourt']+['/homecourt/'+p['slug'] for p in PAGES]+[m['path'] for m in MAP]
 for path in paths:
  node=next((n for n in root if n.findtext(ns+'loc')==BASE+path),None)
  if node is None:node=ET.SubElement(root,ns+'url');ET.SubElement(node,ns+'loc').text=BASE+path
  stamp=node.find(ns+'lastmod')
  if stamp is None:stamp=ET.SubElement(node,ns+'lastmod')
  stamp.text=max(stamp.text or '',DATE)
 ET.register_namespace('',ns[1:-1]);tree.write(ROOT/'sitemap.xml',encoding='utf-8',xml_declaration=True)
 reports();print(f'HomeCourt build: {len(PAGES)} guides + hub; {len(MAP)} contextual updates. No publishing.')
if __name__=='__main__':build()
