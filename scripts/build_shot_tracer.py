#!/usr/bin/env python3
"""Generate approved tracer landing pages from one shared, functional tool shell."""
import html
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

def render(p,pages,shell):
    crumbs=[('Home','/'),('Basketball shot tracer','/shot-tracer')]
    if p['slug']:crumbs.append((p['heading'],route(p)))
    content='<div class="tracer-content">'
    for sec in p['sections']:
        content+='<section><h2>'+H(sec['heading'])+'</h2>'
        if sec.get('text'):content+='<p>'+H(sec['text'])+'</p>'
        if sec.get('steps'):content+='<ol>'+''.join('<li>'+H(x)+'</li>' for x in sec['steps'])+'</ol>'
        content+='</section>'
    if p.get('examples'):content+='<section><h2>Examples for this workflow</h2>'+cards(p['examples'])+'</section>'
    content+='<section><h2>Basketball shot tracer questions</h2>'+''.join('<details><summary>'+H(q)+'</summary><p>'+H(a)+'</p></details>' for q,a in p['faq'])+'</section>'
    related=[x for x in pages if x['slug'] and x['slug']!=p['slug']][:3]
    content+='<section><h2>Keep working on your basketball video</h2>'+cards(LINKS+[(route(x),x['heading'],x['intro']) for x in related])
    if any(x['slug'] for x in pages):content+='<p><a href="/shot-tracer/scenarios">Browse all shot tracer workflows</a></p>'
    content+='<p><a href="#tracer-tool">Add a tracer to your video</a></p></section></div>'
    values={'TITLE':'<title>'+H(p['title'])+'</title>','INTRO':'<section class="intro"><h1>'+H(p['heading'])+'</h1><p>'+H(p['intro'])+'</p></section>','META':metadata(p['title'],p['description'],route(p),crumbs),'BREADCRUMB':breadcrumb(crumbs),'CONTENT':content}
    for key,value in values.items():
        token='{{'+key+'}}'
        if shell.count(token)!=1:raise ValueError(f'Template needs one {token}')
        shell=shell.replace(token,value)
    return shell

def directory(number,pages,shell):
    path=directory_path(number);title=f'Basketball Shot Tracer Workflows – Page {number} | HoopCut'
    desc=f'Browse basketball shot tracer workflows, page {number}: choose footage and review the effect for each type of shot.'
    crumbs=[('Home','/'),('Shot tracer','/shot-tracer'),('Workflows',directory_path(1))]
    if number>1:crumbs.append((f'Page {number}',path))
    total=(len(pages)+PAGE_SIZE-1)//PAGE_SIZE
    content='<div class="tracer-content"><h1>Basketball shot tracer workflows'+(f' – page {number}' if number>1 else '')+'</h1><p>Choose a workflow for your footage. Each page includes preparation advice and examples.</p>'+cards([(route(p),p['heading'],p['intro']) for p in pages[(number-1)*PAGE_SIZE:number*PAGE_SIZE]])+'<nav aria-label="Workflow pages">'
    if number>1:content+=f'<a href="{directory_path(number-1)}">Previous page</a> · '
    content+=f'Page {number} of {total}'
    if number<total:content+=f' · <a href="{directory_path(number+1)}">Next page</a>'
    content+='</nav></div>'
    header=re.search(r'<header>.*?</header>',shell,re.S)[0];footer=re.search(r'<footer>.*?</footer>',shell,re.S)[0]
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+H(title)+'</title>'+metadata(title,desc,path,crumbs)+'<link rel="stylesheet" href="/assets/shot-tracer-tool.css"></head><body>'+header+'<main>'+breadcrumb(crumbs)+content+footer+'</main></body></html>'

def add_tool_link(source):
    if 'id="shot-tracer-upload-link"' in source:return source
    if source.count('</main>')!=1:raise ValueError('Expected one main for tool entry')
    return source.replace('</main>','<section id="shot-tracer-upload-link" style="max-width:960px;margin:32px auto;padding:24px"><h2><a href="/shot-tracer">Add a shot tracer to your own basketball video</a></h2><p>Upload your clip, choose up to 30 seconds, preview the ball trail and export the free Firework effect.</p></section></main>')

def build(root=ROOT):
    pages=json.loads((root/'content/shot-tracer/pages.json').read_text());validate(pages)
    approved=[p for p in pages if p['status']=='approved'];scenes=[p for p in approved if p['slug']]
    shell=(root/'content/shot-tracer/tool.html').read_text()
    outputs={route(p):render(p,approved,shell) for p in approved}
    for n in range(1,(len(scenes)+PAGE_SIZE-1)//PAGE_SIZE+1):outputs[directory_path(n)]=directory(n,scenes,shell)
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
    for path in outputs:ET.SubElement(ET.SubElement(xml,ns+'url'),ns+'loc').text=BASE+path
    ET.register_namespace('',ns[1:-1]);tree.write(root/'sitemap.xml',encoding='utf-8',xml_declaration=True)
    print(f'Built {len(approved)} approved tracer pages, {len(outputs)-len(approved)} directory pages; drafts excluded.')
    return set(outputs)

if __name__=='__main__':build()
