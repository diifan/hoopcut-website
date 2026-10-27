#!/usr/bin/env python3
"""Validate the authored pages, density contract, public links and SEO metadata."""
import itertools
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree

from build_blog import ROOT, ARTICLES, metrics, slug, tokens


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.ids = []
        self.article_depth = 0
        self.article_text = []

    def handle_starttag(self, tag, attrs):
        assert len(attrs) == len(dict(attrs)), ('duplicate attributes', tag, attrs)
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if attrs.get('id'):
            self.ids.append(attrs['id'])
        if tag == 'article' and attrs.get('id') == 'article-content':
            self.article_depth = 1

    def handle_endtag(self, tag):
        if tag == 'article' and self.article_depth:
            self.article_depth = 0

    def handle_data(self, text):
        if self.article_depth:
            self.article_text.append(text)


def resolve(path):
    file = ROOT / unquote(path).lstrip('/')
    if path in ['', '/']:
        return ROOT / 'index.html'
    if file.is_dir():
        return file / 'index.html'
    if file.is_file():
        return file
    return file.with_suffix('.html')


pages = {}
titles = set()
descriptions = set()
article_words = {}
for file in [ROOT/'index.html', ROOT/'terms.html', ROOT/'privacy.html', *sorted((ROOT/'blog').glob('*.html'))]:
    source = file.read_text()
    page = Page()
    page.feed(source)
    pages[file] = page
    assert len(page.ids) == len(set(page.ids)), ('duplicate ids',file)
    assert sum(t == 'h1' for t,a in page.tags) == 1, ('H1',file)
    canonicals = [a['href'] for t,a in page.tags if t=='link' and a.get('rel')=='canonical']
    assert len(canonicals) == 1, ('canonical',file)
    if file.parent.name != 'blog':
        assert any(t=='a' and a.get('href')=='/blog' for t,a in page.tags), ('blog navigation',file)
        continue
    title = re.search(r'<title>(.*?)</title>',source)[1]
    desc = [a['content'] for t,a in page.tags if t=='meta' and a.get('name')=='description']
    assert len(desc)==1 and title not in titles and desc[0] not in descriptions, ('metadata uniqueness',file)
    titles.add(title);descriptions.add(desc[0])
    assert not any('noindex' in a.get('content','').lower() for t,a in page.tags if t=='meta' and a.get('name')=='robots')
    assert [a['content'] for t,a in page.tags if t=='meta' and a.get('property')=='og:url']==canonicals
    for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>',source):
        data=json.loads(raw)
        assert data.get('@context')=='https://schema.org'
        if file.name!='index.html':
            node=next(x for x in data['@graph'] if x['@type']=='BlogPosting')
            assert node['url']==canonicals[0] and node['mainEntityOfPage']['@id']==canonicals[0]
    assert not re.search(r'\{(?:k|ref)\}',source), ('unresolved editorial placeholder',file)

for file,page in pages.items():
    for tag,attrs in page.tags:
        for attribute in ('href','src','poster'):
            value=attrs.get(attribute)
            if not value:
                continue
            u=urlsplit(value)
            if u.scheme or u.netloc:
                if tag=='a' and attrs.get('target')=='_blank':
                    assert 'noopener' in attrs.get('rel',''), ('external link',file,value)
                continue
            # All new blog resources are root-relative; existing root-page assets are relative.
            path=u.path
            destination=resolve(path) if path.startswith('/') else (resolve(path) if path else file)
            assert destination.exists(), ('missing local target',file,value,destination)
            if u.fragment and destination in pages:
                assert u.fragment in pages[destination].ids, ('missing anchor',file,value)

for item in ARTICLES:
    file=ROOT/'blog'/(slug(item['keyword'])+'.html')
    page=pages[file]
    # Only the article is passed to the density function, not metadata or navigation.
    stat=metrics(' '.join(page.article_text),item['keyword'])
    assert stat['exact_matches'] < 15, ('review excessive exact phrase repetition',item['keyword'],stat)
    assert stat['words']>=350, ('insufficient useful body length',file,stat)
    article_words[item['keyword']]=tokens(' '.join(page.article_text).replace(item['keyword'],'subject'))

def shingles(words):
    return {tuple(words[i:i+5]) for i in range(len(words)-4)}

similarity=[]
for a,b in itertools.combinations(article_words,2):
    sa,sb=shingles(article_words[a]),shingles(article_words[b])
    similarity.append((len(sa&sb)/len(sa|sb),a,b))
worst=max(similarity)
assert worst[0]<0.5, ('near-duplicate article bodies',worst)
urls=[x.text for x in ElementTree.parse(ROOT/'sitemap.xml').getroot().findall('{*}url/{*}loc')]
resource_count = len(list((ROOT/'templates').glob('*.html')))
assert len(urls)==len(ARTICLES)+6+resource_count+int((ROOT/'tools.html').exists()) and len(urls)==len(set(urls))
assert all('https://hoopcut.ai/blog/'+slug(x['keyword']) in urls for x in ARTICLES)
assert all('https://hoopcut.ai/demo/'+x in urls for x in ['auto-clipping','shot-tracer'])
assert 'Sitemap: https://hoopcut.ai/sitemap.xml' in (ROOT/'robots.txt').read_text()
print('PASS: consolidated guides, sitemap, canonical/schema/metadata, links/anchors, 350+ article words; no minimum keyword density.')
print('Highest five-word-shingle Jaccard similarity:',round(worst[0],3),worst[1:])
