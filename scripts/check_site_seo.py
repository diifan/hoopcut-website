#!/usr/bin/env python3
"""Audit all public sitemap pages locally. --http also validates preview responses."""
import argparse
import html
import json
import re
from collections import Counter,deque
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit,unquote
from urllib.request import urlopen,Request
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
BASE='https://hoopcut.ai'
class Page(HTMLParser):
    def __init__(self,source):
        super().__init__();self.tags=[];self.ids=[];self.feed(source)
    def handle_starttag(self,tag,attrs):
        assert len(attrs)==len(dict(attrs)),('duplicate HTML attribute',tag)
        a=dict(attrs);self.tags.append((tag,a))
        if a.get('id'):self.ids.append(a['id'])

def file_for(path):
    p=ROOT/unquote(path).lstrip('/')
    if p.is_dir():return p/'index.html'
    return p if p.is_file() else p.with_suffix('.html')

def check(http=False):
    urls=[x.text for x in ET.parse(ROOT/'sitemap.xml').getroot().findall('{*}url/{*}loc')]
    assert len(urls)==len(set(urls))==39
    records={};titles=set();descriptions=set();adjacency={};incoming=Counter()
    for url in urls:
        assert url.startswith(BASE+'/') and not urlsplit(url).query and not urlsplit(url).fragment
        path=url.removeprefix(BASE);file=file_for(path);source=file.read_text();p=Page(source);records[path]=(file,source,p)
        assert len(p.ids)==len(set(p.ids)),('duplicate ID',path)
        assert sum(t=='h1' for t,a in p.tags)==1,('single H1',path)
        canonical=[a.get('href') for t,a in p.tags if t=='link' and a.get('rel')=='canonical']
        assert canonical==[url],('canonical/sitemap agreement',path)
        title=html.unescape(re.search(r'<title>(.*?)</title>',source,re.S)[1])
        desc=[a.get('content','') for t,a in p.tags if t=='meta' and a.get('name')=='description']
        assert title.strip() and title not in titles,('unique title',path)
        assert len(desc)==1 and desc[0].strip() and desc[0] not in descriptions,('unique description',path)
        titles.add(title);descriptions.add(desc[0])
        assert not any('noindex' in a.get('content','').lower() for t,a in p.tags if t=='meta' and a.get('name')=='robots'),('production noindex',path)
        meta={a.get('property') or a.get('name'):a.get('content') for t,a in p.tags if t=='meta'}
        assert meta.get('og:url')==url,('OG URL',path)
        for key in ['og:title','og:description','og:image','twitter:card','twitter:title','twitter:description','twitter:image']:
            assert meta.get(key),('social metadata',path,key)
        for key in ['og:image','twitter:image']:
            image=urlsplit(meta[key]);assert image.scheme=='https' and image.netloc=='hoopcut.ai' and file_for(image.path).is_file(),('social image',path,key)
        graphs=[]
        for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>',source,re.S):
            data=json.loads(raw);assert data.get('@context')=='https://schema.org';graphs+=data.get('@graph',[data])
        assert graphs,('structured data',path)
        if path.startswith('/blog/') or path.startswith('/templates/') or path in ['/blog','/tools']:
            assert any(x.get('@type')=='BreadcrumbList' for x in graphs),('breadcrumb schema',path)
            assert any(t=='nav' and a.get('aria-label')=='Breadcrumb' for t,a in p.tags),('visible breadcrumb',path)
        for t,a in p.tags:
            if t=='img':assert 'alt' in a and a.get('width') and a.get('height'),('image alt/dimensions',path,a.get('src'))
        nav=re.search(r'<nav[^>]*aria-label="Main navigation"[^>]*>.*?</nav>',source,re.S)
        assert nav and 'href="/tools"' in nav[0] and 'href="/blog"' in nav[0]
        assert 'href="/terms"' not in nav[0] and 'href="/privacy"' not in nav[0],('legal links in main navigation',path)
        footer=re.search(r'<footer\b.*?</footer>',source,re.S)
        assert footer and 'href="/terms"' in footer[0] and 'href="/privacy"' in footer[0],('legal footer',path)
        neighbors=set()
        for t,a in p.tags:
            if t!='a' or not a.get('href'):continue
            u=urlsplit(a['href'])
            if u.scheme or u.netloc:continue
            target=u.path or path
            if BASE+target in urls:neighbors.add(target);incoming[target]+=1
        adjacency[path]=neighbors
        if http:
            with urlopen('http://127.0.0.1:8767'+path,timeout=15) as response:
                assert response.status==200,('HTTP status',path,response.status)
                assert 'noindex' in response.headers.get('X-Robots-Tag',''),('local preview protection',path)
    for path,(file,source,p) in records.items():
        for t,a in p.tags:
            for key in ['href','src','poster']:
                value=a.get(key)
                if not value:continue
                u=urlsplit(value)
                if u.scheme or u.netloc:continue
                dest=file_for(u.path) if u.path.startswith('/') else (file if not u.path else file.parent/unquote(u.path))
                assert dest.exists(),('missing file/link',path,value)
                if u.fragment and u.path in records:assert unquote(u.fragment) in records[u.path][2].ids,('broken anchor',path,value)
    reached={'/'};q=deque(['/'])
    while q:
        for child in adjacency[q.popleft()]-reached:reached.add(child);q.append(child)
    assert reached==set(records),('orphaned page',set(records)-reached)
    robots=(ROOT/'robots.txt').read_text();assert 'Sitemap: '+BASE+'/sitemap.xml' in robots and 'Disallow: /\n' not in robots
    config=json.loads((ROOT/'vercel.json').read_text());assert config.get('cleanUrls') is True and config.get('trailingSlash') is False
    assert 'reports/' in (ROOT/'.vercelignore').read_text()
    report={'status':'pass','pages':len(urls),'uniqueTitles':len(titles),'uniqueDescriptions':len(descriptions),'reachableFromHomepage':len(reached),'source':'production-ready static HTML; localhost responses intentionally noindex','httpPreviewChecked':http,'legalNavigation':'Terms and Privacy in footer only','checks':['canonical/sitemap agreement','single H1','schema and breadcrumbs','OG/Twitter metadata and images','image dimensions/alt','internal links and reachability','robots and clean URLs'],'searchPerformance':'Live indexing, rankings and Core Web Vitals require post-deployment checks; not asserted by this local audit.'}
    (ROOT/'reports/site-seo-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: all 39 sitemap pages; unique metadata, canonical, H1, schema, links/assets, images, homepage reachability, legal footer.'+(' All preview URLs return HTTP 200 and noindex.' if http else ''))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--http',action='store_true');check(parser.parse_args().http)
