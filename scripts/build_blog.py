#!/usr/bin/env python3
"""Build static, crawlable editorial guides and diagnostic keyword metrics.

Coverage = non-overlapping exact phrase matches * words in phrase / article words.
Only visible article text is counted: metadata, navigation and related links are excluded.
No keyword density target is enforced.
"""
import csv
import html
import json
import math
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-10-23"
BASE = "https://hoopcut.ai"
ARTICLES = json.loads((ROOT / "content/blog/articles.json").read_text())
H = html.escape


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def tokens(text):
    return re.findall(r"[a-z0-9]+(?:['’][a-z0-9]+)?", text.lower())


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def metrics(markup, keyword):
    parser = Text()
    parser.feed(markup)
    words = tokens(" ".join(parser.parts))
    key = tokens(keyword)
    count = 0
    i = 0
    while i <= len(words) - len(key):
        if words[i:i + len(key)] == key:
            count += 1
            i += len(key)
        else:
            i += 1
    return dict(words=len(words), exact_matches=count,
                keyword_words=len(key), coverage_percent=round(count * len(key) / len(words) * 100, 3),
                occurrences_per_100_words=round(count / len(words) * 100, 3))


def copy(text, item, selected, cursor):
    def replace(match):
        if match[1] == "k":
            return H(item["keyword"])
        index = cursor[0]
        cursor[0] += 1
        if index in selected:
            phrase = ('“'+item['keyword']+'”') if item['keyword'].endswith(' free') else 'the '+item['keyword']
        else:
            phrase = item['reference']
        return H(phrase)
    result = re.sub(r"\{(k|ref)\}", replace, text)
    # Pronoun fallbacks must not create doubled determiners.
    result = re.sub(r"\b([Aa]n?|[Tt]he) the\b", r"\1", result)
    return result


def article_markup(item, selected=frozenset(), checklist_key=False, worksheet_key=False):
    cursor = [0]
    c = lambda text: copy(text, item, selected, cursor)
    sections = []
    for index, (heading, paragraph) in enumerate(item["sections"], 1):
        sections.append(f'<section id="step-{index}"><h2>{H(heading)}</h2><p>{c(paragraph)}</p></section>')
    checklist_title = item["keyword"].capitalize() + ": final checks" if checklist_key else "Before you export"
    table_title = item["keyword"].capitalize() + ": a working checklist" if worksheet_key else item["tableTitle"]
    sources = [("Hoopcut product overview", BASE + "/")] + item.get("sources", [])
    sources_markup = "".join(f'<li><a href="{H(url, quote=True)}">{H(label)}</a></li>' for label, url in sources)
    return f'''<article class="post" id="article-content">
<header class="post-heading"><p class="eyebrow">{H(item['category'])}</p><h1>{H(item['title'])}</h1>
<p class="lede">{H(item['summary'])}</p><p class="byline">By Hoopcut · <time datetime="{DATE}">October 23, 2026</time></p></header>
<p>{c(item['lead'])}</p>
{''.join(sections)}
<section id="checklist"><h2>{H(checklist_title)}</h2><ul class="checklist">{''.join('<li>'+H(x)+'</li>' for x in item['checklist'])}</ul></section>
<section id="worksheet"><h2>{H(table_title)}</h2><div class="table-wrap"><table><thead><tr><th scope="col">Check</th><th scope="col">What to look for</th></tr></thead><tbody>{''.join('<tr><th scope="row">'+H(a)+'</th><td>'+H(b)+'</td></tr>' for a,b in item['rows'])}</tbody></table></div></section>
<section id="questions"><h2>Practical questions</h2>{''.join('<h3>'+c(q)+'</h3><p>'+c(a)+'</p>' for q,a in item['faq'])}</section>
<aside class="product-note"><h2>Where Hoopcut fits</h2><p>Hoopcut is currently in TestFlight testing. It focuses on basketball editing on iPhone. Confirm access, pricing and export options before planning a project. <a href="/">Explore Hoopcut</a>.</p></aside>
<section id="sources" class="sources"><h2>Sources and further reading</h2><ul>{sources_markup}</ul><p>Workflows and checklists are editorial guidance. External product information is not a claim of hands-on comparative testing.</p></section>
</article>'''


def resolve_article(item):
    # Natural editorial copy; keyword metrics are diagnostic only.
    markup = article_markup(item)
    return markup, metrics(markup, item['keyword'])


def navigation(active='blog'):
    return f'''<a class="skip" href="#main">Skip to content</a><header class="blog-header"><a class="brand" href="/" aria-label="Hoopcut home"><img src="/assets/blog/brand-icon.png" width="102" height="102" alt=""><span>HoopCut</span></a><nav aria-label="Main navigation"><a href="/">Product</a><a href="/blog"{' aria-current="page"' if active=='index' else ''}>Blog</a><a href="/privacy">Privacy</a></nav></header>'''


def footer():
    return '<footer class="blog-footer"><a class="brand" href="/">HoopCut</a><p>More time on the court. Less time editing.</p><nav aria-label="Footer"><a href="/blog">All guides</a><a href="/terms">Terms</a><a href="/privacy">Privacy</a><a href="mailto:hello@goswie.com">Contact</a></nav><small>© 2026 SWINK AI INC.</small></footer>'


def head(title, description, url, graph):
    title = H(title, quote=True)
    description = H(description, quote=True)
    schema_json = json.dumps({'@context':'https://schema.org','@graph':graph}, ensure_ascii=False).replace('</','<\\/')
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><meta name="description" content="{description}"><link rel="canonical" href="{url}">
<link rel="icon" href="/assets/blog/brand-icon.png"><link rel="stylesheet" href="/assets/blog/blog.css">
<meta property="og:type" content="{'article' if '/blog/' in url else 'website'}"><meta property="og:site_name" content="Hoopcut"><meta property="og:title" content="{title}"><meta property="og:description" content="{description}"><meta property="og:url" content="{url}"><meta property="og:image" content="{BASE}/assets/blog/court.webp"><meta property="og:image:alt" content="Basketball court action">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{title}"><meta name="twitter:description" content="{description}"><meta name="twitter:image" content="{BASE}/assets/blog/court.webp">
<script type="application/ld+json">{schema_json}</script></head><body>'''


def cards(items, stats):
    return '<div class="cards">' + ''.join(f'''<article class="card"><p class="eyebrow">{H(a['category'])}</p><h3><a href="/blog/{slug(a['keyword'])}">{H(a['title'])}</a></h3><p>{H(a['summary'])}</p><span>{max(1, math.ceil(stats[a['keyword']]['words']/200))} min read <span aria-hidden="true">↗</span></span></article>''' for a in items) + '</div>'


def build():
    (ROOT/'blog').mkdir(exist_ok=True)
    active = {slug(a['keyword'])+'.html' for a in ARTICLES} | {'index.html'}
    for draft in (ROOT/'blog').glob('*.html'):
        if draft.name not in active:
            draft.unlink()
    all_stats = {}
    resolved = {}
    for item in ARTICLES:
        markup, stat = resolve_article(item)
        all_stats[item['keyword']] = stat
        resolved[item['keyword']] = markup
    for item in ARTICLES:
        path = '/blog/' + slug(item['keyword'])
        url = BASE + path
        stat = all_stats[item['keyword']]
        same = [x for x in ARTICLES if x != item and x['category'] == item['category']]
        others = [x for x in ARTICLES if x != item and x not in same]
        related = (same + others)[:3]
        toc = ''.join(f'<a href="#step-{i}">{H(heading)}</a>' for i,(heading,_) in enumerate(item['sections'],1))
        graph = [
            {'@type':'BlogPosting','@id':url+'#article','headline':item['title'],'description':item['summary'],'url':url,'mainEntityOfPage':{'@type':'WebPage','@id':url},'datePublished':DATE+'T12:00:00+08:00','dateModified':DATE+'T12:00:00+08:00','author':{'@type':'Organization','name':'Hoopcut','url':BASE+'/'},'publisher':{'@type':'Organization','name':'Hoopcut','url':BASE+'/'},'inLanguage':'en','wordCount':stat['words'],'image':BASE+'/assets/blog/court.webp','isPartOf':{'@type':'Blog','@id':BASE+'/blog#blog','url':BASE+'/blog','name':'Hoopcut Blog'}},
            {'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'Home','item':BASE+'/'},{'@type':'ListItem','position':2,'name':'Blog','item':BASE+'/blog'},{'@type':'ListItem','position':3,'name':item['title'],'item':url}]}
        ]
        document = head(item['title']+' | Hoopcut Blog',item['summary'],url,graph)+navigation()+f'''<main id="main"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a><span aria-hidden="true">/</span><a href="/blog">Blog</a><span aria-hidden="true">/</span><span>{H(item['category'])}</span></nav><div class="reading-layout">{resolved[item['keyword']]}<aside class="on-this-page"><p class="eyebrow">ON THIS PAGE</p><nav aria-label="On this page">{toc}<a href="#checklist">Final checks</a><a href="#questions">Practical questions</a><a href="#sources">Sources</a></nav><a class="product-link" href="/">Explore Hoopcut <span aria-hidden="true">↗</span></a></aside></div><section class="related" aria-labelledby="related-title"><p class="eyebrow">KEEP READING</p><h2 id="related-title">More from the court.</h2>{cards(related,all_stats)}<a class="all-guides" href="/blog">Browse all basketball editing guides →</a></section></main>'''+footer()+'</body></html>'
        (ROOT/'blog'/(slug(item['keyword'])+'.html')).write_text(document)
    categories = list(dict.fromkeys(x['category'] for x in ARTICLES))
    index_url = BASE + '/blog'
    index_graph=[{'@type':'Blog','@id':index_url+'#blog','url':index_url,'name':'Hoopcut Blog','description':'Practical basketball video editing guides, review checklists and Shot Tracer workflows.','inLanguage':'en'},{'@type':'ItemList','itemListElement':[{'@type':'ListItem','position':i,'url':BASE+'/blog/'+slug(a['keyword']),'name':a['title']} for i,a in enumerate(ARTICLES,1)]}]
    sections=''.join(f'<section class="topic-section" id="{slug(cat)}"><div class="section-label"><h2>{H(cat)}</h2><span>{sum(x["category"]==cat for x in ARTICLES):02d} guides</span></div>{cards([x for x in ARTICLES if x["category"]==cat],all_stats)}</section>' for cat in categories)
    index=head('Basketball Editing Guides & Shot Tracer Tutorials | Hoopcut Blog','Practical basketball editing guides: review AI clips, create iPhone highlight reels, add Shot Tracer effects and prepare videos for your audience.',index_url,index_graph)+navigation('index')+f'''<main id="main" class="blog-index"><section class="index-hero"><div><p class="eyebrow">THE HOOPCUT PLAYBOOK</p><h1>Better footage.<br><span>Better highlights.</span></h1><p class="lede">Practical guides for the moments worth keeping. Learn to select the play, shape the edit and share a reel that makes sense.</p><p class="index-meta">{len(ARTICLES)} focused guides · Editing, AI, iPhone & Shot Tracer</p></div><img src="/assets/blog/court.webp" width="1280" height="720" alt="Basketball players in action on an outdoor court" fetchpriority="high"></section><nav class="topic-nav" aria-label="Browse topics">{''.join('<a href="#'+slug(cat)+'">'+H(cat)+'</a>' for cat in categories)}</nav>{sections}</main>'''+footer()+'</body></html>'
    (ROOT/'blog/index.html').write_text(index)
    # The existing site's cleanUrls/trailingSlash configuration serves these paths.
    sitemap = Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    for path in ['/','/terms','/privacy','/blog'] + ['/blog/'+slug(a['keyword']) for a in ARTICLES]:
        node = SubElement(sitemap,'url')
        SubElement(node,'loc').text = BASE + path
    (ROOT/'sitemap.xml').write_bytes(b'<?xml version="1.0" encoding="UTF-8"?>\n'+tostring(sitemap,encoding='utf-8')+b'\n')
    for filename in ['index.html','terms.html','privacy.html']:
        file = ROOT / filename
        source = file.read_text()
        if 'href="/blog"' not in source:
            anchor='<a href="#faq">FAQ</a>' if filename=='index.html' else '<a href="/#faq">FAQ</a>'
            assert anchor in source
            source=source.replace(anchor,'<a href="/blog">Blog</a>'+anchor,1)
            file.write_text(source)
    report_dir = ROOT.parents[1] / 'outputs'
    report_dir.mkdir(exist_ok=True)
    rows=[dict(keyword=a['keyword'],path='/blog/'+slug(a['keyword']),**all_stats[a['keyword']]) for a in ARTICLES]
    (report_dir/'hoopcut-blog-density.json').write_text(json.dumps({'definition':'exact phrase matches × phrase word count / visible article word count; excludes metadata, navigation and related cards','minimum_percent':None,'articles':rows},indent=2))
    with (report_dir/'hoopcut-blog-density.csv').open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
    print(f'Built {len(ARTICLES)} articles + blog index; sitemap has {len(ARTICLES)+4} URLs.')
    for row in rows:
        print(f"{row['coverage_percent']:6.2f}% {row['words']:3} words {row['exact_matches']:2} matches {row['keyword']}")


if __name__ == '__main__':
    build()
