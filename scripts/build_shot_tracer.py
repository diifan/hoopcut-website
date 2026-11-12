#!/usr/bin/env python3
"""Generate approved tracer landing pages from one shared, functional tool shell."""
import html
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://hoopcut.ai'
PAGE_SIZE = 24
LINKS = [
 ('/blog/how-to-add-shot-tracer-to-basketball-video', 'Step-by-step shot tracer guide', 'Prepare footage and review the traced shot.'),
 ('/demo/shot-tracer', 'Explore the basketball tracer demo', 'See a demonstration before selecting your own video.'),
 ('/videos/basketball-shot-tracer-example', 'Watch a basketball shot tracer example', 'Inspect an existing example and the context around its ball flight.'),
 ('/tools/basketball-shot-chart', 'Log makes and misses on a shot chart', 'Record shooting results separately from the visual effect.')
]
H = html.escape

def route(p): return '/shot-tracer' + ('/' + p['slug'] if p['slug'] else '')
def directory_path(number): return '/shot-tracer/scenarios' + (f'/page-{number}' if number > 1 else '')
def load_pages(root=ROOT):
    pages=json.loads((root/'content/shot-tracer/pages.json').read_text())
    for file in sorted((root/'content/shot-tracer/batches').glob('*/*.json')):
        batch=json.loads(file.read_text())
        if not isinstance(batch,list):raise ValueError(f'Expected a page array in {file.name}')
        pages.extend(batch)
    validate(pages)
    return pages

def batch_preview_slugs(root,name):
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',name):raise ValueError('Invalid preview batch name')
    file=root/'content/shot-tracer/batch-manifests'/f'{name}.json'
    if not file.is_file():raise ValueError('Unknown preview batch: '+name)
    manifest=json.loads(file.read_text())
    return manifest['previewSlugs']

def load_link_taxonomy(root=ROOT):
    file=root/'content/shot-tracer/internal-link-taxonomy.json'
    if not file.exists():return {'categories':[], 'pages':{}, 'featured':[]}
    data=json.loads(file.read_text())
    ids=[c['id'] for c in data['categories']]
    if len(ids)!=len(set(ids)) or any(not re.fullmatch(r'[a-z]+(?:-[a-z]+)*',s) for s in ids):
        raise ValueError('Invalid workflow category IDs')
    if any(p['category'] not in ids for p in data['pages'].values()):raise ValueError('Unknown workflow category')
    return data

def category_path(category):return '/shot-tracer/scenarios/'+category['id']

def category_catalog(pages,taxonomy):
    mapping=taxonomy['pages']
    result=[]
    for category in taxonomy['categories']:
        members=[p for p in pages if p['slug'] and p['status']=='approved' and mapping.get(p['slug'],{}).get('category')==category['id']]
        if members:result.append(dict(category,pages=members))
    return result

def related_pages(p,pages,taxonomy=None):
    taxonomy=taxonomy or load_link_taxonomy()
    by_slug={x['slug']:x for x in pages if x['slug']}
    if not p['slug']:return [by_slug[s] for s in taxonomy['featured'] if s in by_slug][:4]
    group=taxonomy['pages'].get(p['slug'],{}).get('relatedGroup')
    if not group:return []
    peers=sorted(s for s in by_slug if taxonomy['pages'].get(s,{}).get('relatedGroup')==group)
    # A circular neighborhood distributes relevant links instead of repeatedly
    # recommending the first three records. Unclassified pages get no fallback.
    position=peers.index(p['slug'])
    ordered=peers[position+1:]+peers[:position]
    return [by_slug[s] for s in ordered[:3]]

def category_navigation(categories,current=None):
    if not categories:return ''
    items=[('/shot-tracer/scenarios','All workflows',None)]+[(category_path(c),c['label'],c['id']) for c in categories]
    return '<nav class="workflow-categories" aria-label="Workflow topics">'+''.join('<a href="'+url+'"'+(' aria-current="page"' if current==key else '')+'>'+H(label)+'</a>' for url,label,key in items)+'</nav>'

def pagination(number,total,position):
    if total<=1:return ''
    numbers=list(range(1,total+1)) if total<=9 else sorted({1,total,*range(max(1,number-2),min(total,number+2)+1)})
    parts=[]
    if number>1:parts.append(f'<a class="page-direction" href="{directory_path(number-1)}" rel="prev">← Previous</a>')
    previous=0
    for n in numbers:
        if n>previous+1:parts.append('<span class="page-gap" aria-hidden="true">…</span>')
        parts.append(f'<a href="{directory_path(n)}" aria-label="Workflow page {n}"'+(' aria-current="page"' if n==number else '')+f'>{n}</a>')
        previous=n
    if number<total:parts.append(f'<a class="page-direction" href="{directory_path(number+1)}" rel="next">Next →</a>')
    return '<nav class="workflow-pagination" aria-label="Workflow pages '+position+'">'+''.join(parts)+'</nav>'

def validate(pages):
    for key in ('slug','intent','title','description'):
        values=[p[key].strip().casefold() for p in pages]
        if len(values)!=len(set(values)): raise ValueError(f'Duplicate {key}')
    hubs=[p for p in pages if not p['slug']]
    if len(hubs)!=1 or hubs[0]['status']!='approved': raise ValueError('One approved hub required')
    for p in pages:
        if p['slug'] and (not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',p['slug']) or p['slug']=='scenarios'): raise ValueError('Invalid or reserved slug')
        if p['status'] not in ('draft','approved'): raise ValueError('Unknown status')
        if not p.get('sections') or not p.get('faq'): raise ValueError('Missing editorial content')
        if p['status']=='approved' and p['slug']:
            for field in ('demandEvidence','exampleEvidence','reviewedBy'):
                if not p.get(field): raise ValueError(f"{p['slug']}: missing {field}")
            if p['exampleEvidence'].get('url') not in [e[0] for e in p.get('examples',[])]: raise ValueError('Evidence must be displayed')
        for url,_,_ in p.get('examples',[]):
            parsed=urlsplit(url)
            if not (url.startswith('/') and not url.startswith('//') or parsed.scheme=='https' and parsed.netloc): raise ValueError('Unsafe example URL')
        for source in p.get('sources',[]):
            parsed=urlsplit(source['url'])
            if parsed.scheme!='https' or not parsed.netloc: raise ValueError('Unsafe source URL')
        if p.get('keyword') and len(p.get('workflowSteps',[]))!=3:
            raise ValueError('Keyword pages require the same three workflow steps')

def metadata(title,description,path,crumbs):
    result=f'<meta name="description" content="{H(description,quote=True)}"><meta name="robots" content="index,follow"><link rel="canonical" href="{BASE+path}">'
    for key,value in [('og:type','website'),('og:url',BASE+path),('og:title',title),('og:description',description),('og:image',BASE+'/assets/icon.png'),('twitter:card','summary'),('twitter:title',title),('twitter:description',description),('twitter:image',BASE+'/assets/icon.png')]:
        result+=f'<meta {"property" if key.startswith("og:") else "name"}="{key}" content="{H(value,quote=True)}">'
    graph={'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':i,'name':name,'item':BASE+url} for i,(name,url) in enumerate(crumbs,1)]}
    return result+'<script type="application/ld+json">'+json.dumps(graph).replace('<','\\u003c')+'</script><link rel="stylesheet" href="/assets/tracer-seo.css">'

def breadcrumb(crumbs):
    return '<nav class="tracer-breadcrumb" aria-label="Breadcrumb">'+' / '.join(f'<a href="{url}">{H(name)}</a>' if i<len(crumbs)-1 else f'<span aria-current="page">{H(name)}</span>' for i,(name,url) in enumerate(crumbs))+'</nav>'

def cards(links):
    return '<ul class="related-grid">'+''.join(f'<li><a href="{H(url,quote=True)}">{H(label)}</a><p>{H(desc)}</p></li>' for url,label,desc in links)+'</ul>'

def keyword_navigation(p):
    items=[
        ('tracer-tool','Add a tracer','Add a tracer to your basketball video','<path d="M12 16V4m-4 4 4-4 4 4M4 15v5h16v-5"/>'),
        ('tracer-sample','See the effect','See the shot tracer effect','<rect x="3" y="4" width="18" height="16" rx="3"/><path d="m10 8 6 4-6 4Z"/>'),
        ('keyword-guide','Video guide',p.get('label','Basketball video')+' guide','<path d="M12 6v15M3 3h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5v16h-5a4 4 0 0 0-4 2 4 4 0 0 0-4-2H3Z"/>'),
        ('keyword-questions','Questions','Basketball shot tracer questions','<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 4 2c-1.5 1-1.5 1-1.5 2m0 3h.01"/>')
    ]
    links=[]
    for i,(target,label,description,paths) in enumerate(items):
        current=' aria-current="location"' if i==0 else ''
        links.append('<a href="#'+target+'" aria-label="'+H(description,quote=True)+'"'+current+'><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'+paths+'</svg><span>'+H(label)+'</span></a>')
    return '<nav class="keyword-jumps" aria-label="On this page">'+''.join(links)+'</nav>'

def render(p,pages,shell,taxonomy=None):
    taxonomy=taxonomy or load_link_taxonomy()
    categories=category_catalog(pages,taxonomy)
    crumbs=[('Home','/'),('Basketball shot tracer','/shot-tracer')]
    if p['slug']:
        crumbs.append(('Workflows','/shot-tracer/scenarios'))
        category=next((c for c in categories if p in c['pages']),None)
        if category:crumbs.append((category['label'],category_path(category)))
        crumbs.append((p.get('label',p['heading']),route(p)))
    content='<div class="tracer-content"'+(' id="keyword-guide"' if p.get('keyword') else '')+'>'
    for sec in p['sections']:
        content+='<section><h2>'+H(sec['heading'])+'</h2>'
        if sec.get('text'):content+='<p>'+H(sec['text'])+'</p>'
        for sub in sec.get('subsections',[]):
            content+='<div class="keyword-subsection"><h3>'+H(sub['heading'])+'</h3><p>'+H(sub['text'])+'</p></div>'
        if sec.get('steps'):content+='<ol>'+''.join('<li>'+H(x)+'</li>' for x in sec['steps'])+'</ol>'
        content+='</section>'
    if p.get('examples'):content+='<section><h2>'+H(p.get('examplesHeading','Examples for this workflow'))+'</h2>'+cards(p['examples'])+'</section>'
    content+='<section'+(' id="keyword-questions"' if p.get('keyword') else '')+'><h2>'+H(p.get('faqHeading','Basketball shot tracer questions'))+'</h2>'+''.join('<details><summary>'+H(q)+'</summary><p>'+H(a)+'</p></details>' for q,a in p['faq'])+'</section>'
    if p.get('sources'):
        content+='<section class="keyword-sources"><h2>Sources & further reading</h2><ul>'+''.join('<li><a href="'+H(s['url'],quote=True)+'">'+H(s['title'])+'</a></li>' for s in p['sources'])+'</ul></section>'
    if p.get('appCTA'):
        c=p['appCTA'];content+='<section class="keyword-app"><div><p class="tracer-kicker">YOUR NEXT SHOT</p><h2>'+H(c['heading'])+'</h2><p>'+H(c['text'])+'</p></div><a class="primary" data-keyword-app href="{{APP_URL}}">Download HoopCut <span aria-hidden="true">↗</span></a></section>'
    related=related_pages(p,pages,taxonomy)
    content+='<section><h2>Keep working on your basketball video</h2>'+cards(LINKS+[(route(x),x['heading'],x['intro']) for x in related])
    if any(x['slug'] for x in pages):content+='<p><a href="/shot-tracer/scenarios">Browse all shot tracer workflows</a></p>'
    if p['slug'] and category:content+='<p><a href="'+category_path(category)+'">Explore '+H(category['label'].lower())+' workflows</a></p>'
    content+='<p><a href="#tracer-tool">Add a tracer to your video</a></p></section></div>'
    intro='<section class="intro">'+('<p class="keyword-eyebrow">HOOPCUT / BASKETBALL VIDEO TOOLS</p>' if p.get('keyword') else '')+'<h1>'+H(p['heading'])+'</h1><p>'+H(p['intro'])+'</p>'
    if p.get('heroDetail'):intro+='<p class="keyword-intro-detail">'+H(p['heroDetail'])+'</p>'
    if p.get('note'):intro+='<p class="keyword-note">'+H(p['note'])+'</p>'
    if not p['slug'] and any(x['slug'] for x in pages):intro+='<p><a class="workflow-hub-entry" href="/shot-tracer/scenarios">Find a workflow for your basketball footage →</a></p>'
    intro+='</section>'
    if p.get('keyword'):
        intro+=keyword_navigation(p)
        shell=shell.replace('<body>','<body class="keyword-landing">')
        shell=shell.replace('href="/shot-tracer" aria-current="page"','href="/shot-tracer" aria-current="location"')
        shell=shell.replace('</head>','<link rel="stylesheet" href="/assets/tracer-keywords.css"><script defer src="/assets/tracer-keyword-nav.js"></script></head>')
        if p.get('toolHeading'):
            shell=shell.replace('<div class="workspace" id="tracer-tool">','<h2 class="keyword-tool-heading">'+H(p['toolHeading'])+'</h2><div class="workspace" id="tracer-tool">',1)
        shell=shell.replace('<h2 id="tracer-steps-title">Three simple steps.</h2>','<h2 id="tracer-steps-title">'+H(p.get('workflowHeading','Three simple steps.'))+'</h2>')
        # Keep the actual upload/editor markup and processing script unchanged.
        # Only the surrounding content is configured for each search intent.
        for old,new in zip([
            ('Upload your video','Choose a basketball clip. Trim to 30 seconds if needed.'),
            ('Preview your tracer','Choose your hoop when prompted, then preview an effect.'),
            ('Export &amp; share','Export Firework for free and share your shot.')
        ],p['workflowSteps']):
            shell=shell.replace('<h3>'+old[0]+'</h3><p>'+old[1]+'</p>','<h3>'+H(new['title'])+'</h3><p>'+H(new['text'])+'</p>')
        sample=re.search(r'<section class="tracer-sample".*?</section>',shell,re.S)
        if not sample:raise ValueError('Shared sample module missing')
        sample=sample[0].replace('Watch a sample video.',H(p.get('sampleHeading','See the ball trail in action.'))).replace('A prepared HoopCut example with the ball trail already added.','A prepared HoopCut clip demonstrating the shot trail effect.')
        shell=re.sub(r'<section class="tracer-sample".*?</section>','',shell,flags=re.S)
        shell=shell.replace('<section class="tracer-walkthrough"',sample+'<section class="tracer-walkthrough"',1)
    meta=metadata(p['title'],p['description'],route(p),crumbs)
    if p['status']=='draft':meta=meta.replace('content="index,follow"','content="noindex,follow"')
    if p.get('keyword'):
        graph={'@context':'https://schema.org','@type':'WebPage','@id':BASE+route(p)+'#page','url':BASE+route(p),'name':p['title'],'description':p['description'],'inLanguage':'en','mainEntity':{'@id':BASE+'/shot-tracer#tool'}}
        meta+='<script type="application/ld+json">'+json.dumps(graph).replace('<','\\u003c')+'</script>'
    values={'TITLE':'<title>'+H(p['title'])+'</title>','INTRO':intro,'META':meta,'BREADCRUMB':breadcrumb(crumbs),'CONTENT':content}
    for key,value in values.items():
        token='{{'+key+'}}'
        if shell.count(token)!=1:raise ValueError(f'Template needs one {token}')
        shell=shell.replace(token,value)
    return shell

def directory(number,pages,shell,taxonomy=None,category=None):
    taxonomy=taxonomy or load_link_taxonomy()
    categories=category_catalog(pages,taxonomy)
    path=directory_path(number);title='Basketball Shot Tracer Workflows'+(f' – Page {number}' if number>1 else '')+' | HoopCut'
    desc=f'Browse basketball shot tracer workflows, page {number}: choose footage and review the effect for each type of shot.'
    crumbs=[('Home','/'),('Shot tracer','/shot-tracer'),('Workflows',directory_path(1))]
    if number>1:crumbs.append((f'Page {number}',path))
    total=(len(pages)+PAGE_SIZE-1)//PAGE_SIZE
    selection=pages[(number-1)*PAGE_SIZE:number*PAGE_SIZE]
    heading='Basketball shot tracer workflows'+(f' — page {number}' if number>1 else '')
    introduction='Start with your footage and what you want to do next. Browse training, game video, scouting and other workflows, then use the same shot tracer with your own clip.'
    if category:
        path=category_path(category);title=category['label']+' — Shot Tracer Workflows | HoopCut'
        desc=category['description'];heading=category['label'];introduction=desc
        crumbs=[('Home','/'),('Shot tracer','/shot-tracer'),('Workflows',directory_path(1)),(category['label'],path)]
        selection=category['pages']
    content='<div class="tracer-content workflow-library"><div class="workflow-intro"><p class="workflow-kicker">FIND YOUR WORKFLOW</p><h1>'+H(heading)+'</h1><p>'+H(introduction)+'</p><a class="workflow-upload" href="/shot-tracer#tracer-tool">Already have a clip? Add a shot tracer ↗</a></div>'
    content+=category_navigation(categories,category['id'] if category else None)
    count=f'{len(selection)} workflows in this topic' if category else f'{len(pages)} workflows · Page {number} of {total}'
    content+='<p class="workflow-count">'+count+'</p>'
    if not category:content+=pagination(number,total,'top')
    content+=cards([(route(p),p.get('label',p['heading']),p['intro']) for p in selection])
    if not category:content+=pagination(number,total,'bottom')
    content+='</div>'
    header=re.search(r'<header>.*?</header>',shell,re.S)[0];footer=re.search(r'<footer>.*?</footer>',shell,re.S)[0]
    meta=metadata(title,desc,path,crumbs)
    if any(p['status']=='draft' for p in pages):meta=meta.replace('content="index,follow"','content="noindex,follow"')
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+H(title)+'</title>'+meta+'<link rel="stylesheet" href="/assets/shot-tracer-tool.css"><link rel="stylesheet" href="/assets/tracer-directory.css"></head><body>'+header+'<main>'+breadcrumb(crumbs)+content+footer+'</main></body></html>'

def apply_contextual_links(root,visible):
    file=root/'content/shot-tracer/contextual-links.json'
    if not file.exists():return
    targets={route(p) for p in visible}
    for placement in json.loads(file.read_text()):
        source=placement['source']
        if not re.fullmatch(r'/(?:blog|homecourt|tools|templates)/[a-z0-9-]+',source):raise ValueError('Invalid contextual source')
        output=root/(source.lstrip('/')+'.html')
        if not output.exists():continue
        items=[x for x in placement['items'] if x['target'] in targets]
        start='<!-- TRACER CONTEXT START -->';end='<!-- TRACER CONTEXT END -->'
        html_source=re.sub(re.escape(start)+'.*?'+re.escape(end),'',output.read_text(),flags=re.S)
        if items:
            block=start+'<section class="tracer-context" aria-label="Related video workflows" style="max-width:1100px;margin:32px auto;padding:24px;border-top:1px solid #34382e"><h2>'+H(placement['heading'])+'</h2>'
            for item in items:block+='<p>'+H(item['before'])+'<a href="'+H(item['target'],quote=True)+'">'+H(item['anchor'])+'</a>'+H(item['after'])+'</p>'
            block+='</section>'+end
            # Keep related advice before the main article footer when present.
            match=re.search(r'<footer\b|</main>',html_source)
            if not match:raise ValueError('Missing insertion point for '+source)
            html_source=html_source[:match.start()]+block+html_source[match.start():]
        output.write_text(html_source)

def add_tool_link(source):
    if 'id="shot-tracer-upload-link"' in source:return source
    if source.count('</main>')!=1:raise ValueError('Expected one main for tool entry')
    return source.replace('</main>','<section id="shot-tracer-upload-link" style="max-width:960px;margin:32px auto;padding:24px"><h2><a href="/shot-tracer">Add a shot tracer to your own basketball video</a></h2><p>Upload your clip, choose up to 30 seconds, preview the ball trail and export the free Firework effect.</p></section></main>')

def build(root=ROOT,preview_slugs=(),preview_batch=None):
    pages=load_pages(root)
    if preview_batch:preview_slugs=[*preview_slugs,*batch_preview_slugs(root,preview_batch)]
    approved=[p for p in pages if p['status']=='approved']
    unknown=set(preview_slugs)-{p['slug'] for p in pages if p['slug']}
    if unknown:raise ValueError('Unknown preview slugs: '+', '.join(sorted(unknown)))
    visible=[p for p in pages if p['status']=='approved' or p['slug'] in preview_slugs]
    scenes=[p for p in visible if p['slug']]
    taxonomy=load_link_taxonomy(root)
    shell=(root/'content/shot-tracer/tool.html').read_text()
    # Read the product destination centrally, never per keyword.
    config=root/'content/site-config.json'
    app_url=json.loads(config.read_text())['app']['appStoreUrl'] if config.exists() else 'https://apps.apple.com/us/app/hoopcut-basketball-highlights/id6824860341'
    outputs={route(p):render(p,visible,shell,taxonomy).replace('{{APP_URL}}',H(app_url,quote=True)) for p in visible}
    for n in range(1,(len(scenes)+PAGE_SIZE-1)//PAGE_SIZE+1):outputs[directory_path(n)]=directory(n,scenes,shell,taxonomy)
    for category in category_catalog(scenes,taxonomy):outputs[category_path(category)]=directory(1,scenes,shell,taxonomy,category)
    # This namespace is owned by this generator. Remove obsolete generated routes only.
    for old in (root/'shot-tracer').rglob('*.html'):
        if '/'+str(old.relative_to(root).with_suffix('')) not in outputs:old.unlink()
    for path,source in outputs.items():
        file=root/(path.lstrip('/')+'.html');file.parent.mkdir(parents=True,exist_ok=True);file.write_text(source.rstrip()+'\n')
    for name in ['tools.html','demo/shot-tracer.html','blog/how-to-add-shot-tracer-to-basketball-video.html']:
        file=root/name
        if file.exists():file.write_text(add_tool_link(file.read_text()))
    tree=ET.parse(root/'sitemap.xml');ns='{http://www.sitemaps.org/schemas/sitemap/0.9}';xml=tree.getroot()
    for node in list(xml):
        url=node.findtext(ns+'loc','')
        if url==BASE+'/shot-tracer' or url.startswith(BASE+'/shot-tracer/'):xml.remove(node)
    # Local draft previews must never enter the production sitemap.
    approved_scenes=[p for p in approved if p['slug']]
    sitemap_paths=[route(p) for p in approved]+[directory_path(n) for n in range(1,(len(approved_scenes)+PAGE_SIZE-1)//PAGE_SIZE+1)]
    sitemap_paths += [category_path(c) for c in category_catalog(approved_scenes,taxonomy)]
    for path in sitemap_paths:ET.SubElement(ET.SubElement(xml,ns+'url'),ns+'loc').text=BASE+path
    ET.register_namespace('',ns[1:-1]);tree.write(root/'sitemap.xml',encoding='utf-8',xml_declaration=True)
    apply_contextual_links(root,approved)
    if (root/'index.html').exists():
        import sys
        sys.path.insert(0,str(ROOT/'scripts'))
        from tracer_home_entry import apply_home_entry
        apply_home_entry(root)
    print(f'Built {len(approved)} approved tracer pages, {len(visible)-len(approved)} local draft previews; sitemap contains approved pages only.')
    return set(outputs)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--preview-slugs',nargs='*',default=[],help='Explicit local draft previews; never added to the sitemap')
    parser.add_argument('--preview-batch',help='Local preview manifest name; excludes deferred terms and production sitemap')
    args=parser.parse_args()
    build(preview_slugs=args.preview_slugs,preview_batch=args.preview_batch)
