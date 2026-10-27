#!/usr/bin/env python3
"""Release-readiness checks for the local twenty-page batch; never publishes."""
import hashlib
import json
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit,unquote
from xml.etree import ElementTree as ET
from batch_one_content import GUIDES,RESOURCES

ROOT=Path(__file__).resolve().parents[1]
class Page(HTMLParser):
    def __init__(self,source):
        super().__init__();self.tags=[];self.ids=set();self.text=[];self.feed(source)
    def handle_starttag(self,t,attrs):
        assert len(attrs)==len(dict(attrs)),('duplicate attributes',t)
        a=dict(attrs);self.tags.append((t,a))
        if a.get('id'):
            assert a['id'] not in self.ids,('duplicate ID',a['id']);self.ids.add(a['id'])
    def handle_data(self,data):self.text.append(data)
def resolve(path):
    p=ROOT/unquote(path).lstrip('/')
    if p.is_dir():return p/'index.html'
    return p if p.is_file() else p.with_suffix('.html')

files=[ROOT/'index.html',ROOT/'terms.html',ROOT/'privacy.html',ROOT/'tools.html',*ROOT.glob('blog/*.html'),*ROOT.glob('templates/*.html'),*ROOT.glob('demo/*.html')]
pages={f:Page(f.read_text()) for f in files}
new_paths=['/blog/'+a['keyword'].replace(' ','-') for a in GUIDES]+['/templates/'+a['slug'] for a in RESOURCES]
assert len(new_paths)==20 and len(set(new_paths))==20
plan_file=ROOT.parent/'seo/2026-10-27-100-page-plan.json'
if plan_file.exists():
    plan=json.loads(plan_file.read_text())
    assert set(new_paths)==set(plan['firstBatchURLs'])
titles=set();descriptions=set();report=[]
for path in new_paths:
    f=resolve(path);source=f.read_text();p=pages[f];url='https://hoopcut.ai'+path
    assert sum(t=='h1' for t,a in p.tags)==1,('H1',path)
    canonical=[a['href'] for t,a in p.tags if t=='link' and a.get('rel')=='canonical']
    assert canonical==[url],('canonical',path)
    title=re.search(r'<title>(.*?)</title>',source)[1]
    desc=[a['content'] for t,a in p.tags if t=='meta' and a.get('name')=='description']
    assert len(desc)==1 and desc[0] not in descriptions and title not in titles,('unique metadata',path)
    titles.add(title);descriptions.add(desc[0])
    assert len(title)<80 and 80<len(desc[0])<180,('metadata length',path,len(title),len(desc[0]))
    assert not any('noindex' in a.get('content','').lower() for t,a in p.tags if t=='meta' and a.get('name')=='robots')
    assert [a['content'] for t,a in p.tags if t=='meta' and a.get('property')=='og:url']==[url]
    graphs=[json.loads(x)['@graph'] for x in re.findall(r'<script type="application/ld\+json">(.*?)</script>',source)]
    assert any(x['@type']=='BreadcrumbList' for g in graphs for x in g),('breadcrumb schema',path)
    assert any(t=='nav' and a.get('aria-label')=='Breadcrumb' for t,a in p.tags)
    videos=[a for t,a in p.tags if t=='video'];tracks=[a for t,a in p.tags if t=='track']
    assert len(videos)==1 and len(tracks)==1,('video/captions',path)
    assert videos[0].get('preload')=='none' and 'autoplay' not in videos[0]
    assert any(t=='details' for t,a in p.tags),('video transcript',path)
    for t,a in p.tags:
        if t=='img':assert 'alt' in a and 'width' in a and 'height' in a,('image dimensions',path)
    report.append({'path':path,'title':title,'description':desc[0],'titleLength':len(title),'descriptionLength':len(desc[0])})

for f,p in pages.items():
    for t,a in p.tags:
        for attr in ['href','src','poster']:
            value=a.get(attr)
            if not value:continue
            u=urlsplit(value)
            if u.scheme or u.netloc:continue
            target=resolve(u.path) if u.path.startswith('/') else (f if not u.path else f.parent/u.path)
            if not target.exists() and not u.path.startswith('/'):target=resolve(u.path)
            assert target.exists(),('broken link',str(f),value)
            if u.fragment and target in pages:assert unquote(u.fragment) in pages[target].ids,('broken anchor',str(f),value)

urls=[x.text for x in ET.parse(ROOT/'sitemap.xml').getroot().findall('{*}url/{*}loc')]
assert len(urls)==39==len(set(urls))
assert 'https://hoopcut.ai/tools' in urls
assert all('https://hoopcut.ai'+p in urls for p in new_paths)
prior=subprocess.check_output(['git','show','HEAD:sitemap.xml'],cwd=ROOT).decode()
old_urls=[x.text for x in ET.fromstring(prior).findall('{*}url/{*}loc')]
assert set(old_urls).issubset(urls), 'Existing sitemap URLs dropped'
before=subprocess.check_output(['git','show','HEAD:index.html'],cwd=ROOT).decode()
after=(ROOT/'index.html').read_text()
# Preserve the original review block and hero while adding an authorized Tools entry.
review_pattern=r'<section class="reviews extra-section".*?</section>'
assert re.search(review_pattern,after,re.S)[0]==re.search(review_pattern,before,re.S)[0]
assert re.search(r'<section class="hero".*?</section>',after,re.S)[0]==re.search(r'<section class="hero".*?</section>',before,re.S)[0]
assert after.count('id="tools"')==1 and after.count('href="/assets/tools/home-tools.css"')==1
hub=pages[ROOT/'tools.html']
assert sum(t=='h1' for t,a in hub.tags)==1
assert sum(t=='article' and 'data-tool' in a for t,a in hub.tags)==15
for f,p in pages.items():
    nav=re.search(r'<nav[^>]*aria-label="Main navigation"[^>]*>.*?</nav>',f.read_text(),re.S)
    assert nav and 'href="/tools"' in nav[0] and 'href="/blog"' in nav[0],('Tools/Blog navigation',f)
for f in ROOT.glob('templates/*.html'):
    assert '"name": "Tools", "item": "https://hoopcut.ai/tools"' in f.read_text(),('Tools breadcrumb',f)
plain_home=re.sub('<[^>]+>',' ',after)
plain_home=re.sub(r'\s+',' ',plain_home)
for phrase in ['Wait, it’s already','Got my evening','My friend watched']:assert phrase in plain_home
assert len(list((ROOT/'assets/resources').glob('*.mp4')))==20
for p in (ROOT/'assets/resources').glob('*.mp4'):
    probe=json.loads(subprocess.check_output(['/opt/homebrew/bin/ffprobe','-v','quiet','-show_format','-show_streams','-of','json',str(p)]))
    assert abs(float(probe['format']['duration'])-9)<.1
    assert probe['streams'][0]['codec_name']=='h264'
reportdir=ROOT/'reports';reportdir.mkdir(exist_ok=True)
(reportdir/'batch-one-static.json').write_text(json.dumps({'status':'pass','newPages':20,'additionalToolsDirectory':1,'sitemapURLs':39,'homepage':'Tools navigation and section added; hero/reviews unchanged','metadata':report},indent=2)+'\n')
print('PASS: 20 planned pages + Tools hub; unique metadata; schema/breadcrumbs; links/anchors; media; 39 sitemap URLs; homepage hero/reviews unchanged.')
