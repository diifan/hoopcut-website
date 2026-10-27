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
from datetime import date
from blog_visuals import cover, overview, video_block, caption_groups as render_caption_groups
from html.parser import HTMLParser
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring, parse

ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-10-23"
BASE = "https://hoopcut.ai"
SEO_TITLES = {
    'how to make a basketball highlight video':'How to Make a Basketball Highlight Video | Hoopcut',
    'how to make basketball highlights on iphone':'Basketball Highlights on iPhone: A Step-by-Step Guide | Hoopcut',
    'ai basketball highlight maker':'AI Basketball Highlight Maker: Clip Review Guide | Hoopcut',
    'how to add shot tracer to basketball video':'How to Add Shot Tracer to Basketball Video | Hoopcut',
    'how to make a basketball recruiting video':'How to Make a Basketball Recruiting Video | Hoopcut',
    'how long should a basketball highlight video be':'How Long Should a Basketball Highlight Video Be? | Hoopcut',
    'basketball highlight video examples':'Basketball Highlight Video Examples & Storyboards | Hoopcut',
    'how to make basketball highlights for instagram':'How to Make Basketball Highlights for Instagram | Hoopcut',
    'basketball senior night ideas':'Basketball Senior Night Ideas & Tribute Planning | Hoopcut',
    'basketball captions for instagram':'60 Basketball Captions for Instagram | Hoopcut',
    'basketball media day ideas':'Basketball Media Day Ideas, Photos & Shot List | Hoopcut',
    'basketball banquet ideas':'Basketball Banquet Ideas: Awards & Season Recaps | Hoopcut',
}
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
    published = item.get('datePublished', DATE)
    display_date = date.fromisoformat(published).strftime('%B %d, %Y').replace(' 0', ' ')
    caption_groups = item.get('captionGroups', [])
    captions_markup = ''.join('<section class="caption-group" id="captions-'+str(i)+'"><h2>'+H(group['heading'])+'</h2><ul class="caption-list">'+''.join('<li><p>'+H(text)+'</p><button type="button" data-copy-caption="'+H(text, quote=True)+'" aria-label="Copy caption: '+H(text, quote=True)+'">Copy</button></li>' for text in group['captions'])+'</ul></section>' for i,group in enumerate(caption_groups,1))
    if item.get('visual') and caption_groups:
        captions_markup = render_caption_groups(item)
    caption_nav = '<nav id="caption-categories" class="caption-topic-nav" aria-label="Caption categories">'+''.join('<a href="#captions-'+str(i)+'">'+H(group['heading'])+'</a>' for i,group in enumerate(caption_groups,1))+'</nav>' if caption_groups else ''
    caption_status = '<p id="caption-copy-status" class="copy-status" role="status" aria-live="polite"></p>' if caption_groups else ''
    downloads = '<section class="article-resources" id="downloads"><h2>Download the planning sheet</h2><ul>'+''.join('<li><a download href="'+H(url, quote=True)+'">'+H(label)+'</a></li>' for label,url in item['downloads'])+'</ul><p>Editable CSV files open in common spreadsheet apps. Example timings and blank rows are planning aids, not measured event results.</p></section>' if item.get('downloads') else ''
    editorial_links = '<section class="article-resources" id="next-steps"><h2>Next steps for your basketball footage</h2><ul>'+''.join('<li><a href="'+H(url, quote=True)+'">'+H(label)+'</a></li>' for label,url in item['editorialLinks'])+'</ul></section>' if item.get('editorialLinks') else ''
    cursor = [0]
    c = lambda text: copy(text, item, selected, cursor)
    sections = []
    for index, (heading, paragraph) in enumerate(item["sections"], 1):
        sections.append(f'<section id="step-{index}"><h2>{H(heading)}</h2><p>{c(paragraph)}</p></section>')
        if item.get('visual', {}).get('videoAfter') == index:
            sections.append(video_block(item))
    checklist_title = item["keyword"].capitalize() + ": final checks" if checklist_key else item.get("checklistTitle", "Before you export")
    table_title = item["keyword"].capitalize() + ": a working checklist" if worksheet_key else item["tableTitle"]
    sources = [("Hoopcut product overview", BASE + "/")] + item.get("sources", [])
    sources_markup = "".join(f'<li><a href="{H(url, quote=True)}">{H(label)}</a></li>' for label, url in sources)
    demo = '<figure class="guide-demo"><video controls playsinline preload="none" poster="/assets/video/players/all.jpg" width="1600" height="800"><source src="/assets/video/players/all.mp4" type="video/mp4"></video><figcaption>Hoopcut homepage demonstration: basketball clips with shot trajectories. This is a product example, not a recording of the steps below.</figcaption></figure>' if item.get('demo') else ''
    cta = H(item.get('ctaText', 'Explore Hoopcut'))
    product_note = H(item.get('productNote', 'Hoopcut is currently in TestFlight testing. It focuses on basketball editing on iPhone. Confirm access, pricing and export options before planning a project.'))
    return f'''<article class="post" id="article-content">
<header class="post-heading"><p class="eyebrow">{H(item['category'])}</p><h1>{H(item['title'])}</h1>
<p class="lede">{H(item['summary'])}</p><p class="byline">By Hoopcut · <time datetime="{published}">{display_date}</time></p></header>
{cover(item)}<p>{c(item['lead'])}</p>
{demo}{overview(item)}
{(caption_nav+caption_status+captions_markup+chr(10)) if caption_groups else ''}{''.join(sections)}
{(downloads+editorial_links+chr(10)) if downloads or editorial_links else ''}<section id="checklist"><h2>{H(checklist_title)}</h2><ul class="checklist">{''.join('<li>'+H(x)+'</li>' for x in item['checklist'])}</ul></section>
<section id="worksheet"><h2>{H(table_title)}</h2><div class="table-wrap"><table><thead><tr><th scope="col">{H(item.get("tableHeaders", ["Check", "What to look for"])[0])}</th><th scope="col">{H(item.get("tableHeaders", ["Check", "What to look for"])[1])}</th></tr></thead><tbody>{''.join('<tr><th scope="row">'+H(a)+'</th><td>'+H(b)+'</td></tr>' for a,b in item['rows'])}</tbody></table></div></section>
<section id="questions"><h2>Practical questions</h2>{''.join('<h3>'+c(q)+'</h3><p>'+c(a)+'</p>' for q,a in item['faq'])}</section>
<aside class="product-note"><h2>Where Hoopcut fits</h2><p>{product_note} <a href="/" data-cta="article-product">{cta}</a>.</p></aside>
<section id="sources" class="sources"><h2>Sources and further reading</h2><ul>{sources_markup}</ul><p>Workflows and checklists are editorial guidance. External product information is not a claim of hands-on comparative testing.</p></section>
</article>'''


def resolve_article(item):
    # Natural editorial copy; keyword metrics are diagnostic only.
    markup = article_markup(item)
    return markup, metrics(markup, item['keyword'])


def navigation(active='blog'):
    return f'''<a class="skip" href="#main">Skip to content</a><header class="blog-header"><a class="brand" href="/" aria-label="Hoopcut home"><img src="/assets/blog/brand-icon.png" width="102" height="102" alt=""><span>HoopCut</span></a><nav aria-label="Main navigation"><a href="/">Product</a><a href="/tools"{' aria-current="page"' if active=='tools' else ''}>Tools</a><a href="/blog"{' aria-current="page"' if active=='index' else ''}>Blog</a></nav></header>'''


def footer():
    return '<footer class="blog-footer"><a class="brand" href="/">HoopCut</a><p>More time on the court. Less time editing.</p><nav aria-label="Footer"><a href="/tools">Tools</a><a href="/blog">All guides</a><a href="/terms">Terms</a><a href="/privacy">Privacy</a><a href="mailto:hello@goswie.com">Contact</a></nav><small>© 2026 SWINK AI INC.</small></footer>'


def head(title, description, url, graph, image_path="/assets/blog/court.webp", image_alt="Basketball court action"):
    title = H(title, quote=True)
    description = H(description, quote=True)
    schema_json = json.dumps({'@context':'https://schema.org','@graph':graph}, ensure_ascii=False).replace('</','<\\/')
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><meta name="description" content="{description}"><link rel="canonical" href="{url}">
<link rel="icon" href="/assets/blog/brand-icon.png"><link rel="stylesheet" href="/assets/blog/blog.css">
<meta property="og:type" content="{'article' if '/blog/' in url else 'website'}"><meta property="og:site_name" content="Hoopcut"><meta property="og:title" content="{title}"><meta property="og:description" content="{description}"><meta property="og:url" content="{url}"><meta property="og:image" content="{BASE}{image_path}"><meta property="og:image:alt" content="{H(image_alt,quote=True)}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{title}"><meta name="twitter:description" content="{description}"><meta name="twitter:image" content="{BASE}{image_path}"><meta name="twitter:image:alt" content="{H(image_alt,quote=True)}">
<script type="application/ld+json">{schema_json}</script></head><body>'''


def cards(items, stats):
    return '<div class="cards">' + ''.join(f'''<article class="card">{('<img class="card-cover" loading="lazy" decoding="async" width="1536" height="1024" src="'+H(a["visual"]["image"])+'" alt="'+H(a["visual"]["alt"],quote=True)+'">') if a.get("visual") else ""}<p class="eyebrow">{H(a['category'])}</p><h3><a href="/blog/{slug(a['keyword'])}">{H(a['title'])}</a></h3><p>{H(a['summary'])}</p><span>{max(1, math.ceil(stats[a['keyword']]['words']/200))} min read <span aria-hidden="true">↗</span></span></article>''' for a in items) + '</div>'


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
        preferred = [next(x for x in ARTICLES if x['keyword'] == key) for key in item.get('relatedKeywords', [])]
        related = (preferred + [x for x in same + others if x not in preferred])[:3]
        caption_toc = ''.join('<a href="#captions-'+str(i)+'">'+H(group['heading'])+'</a>' for i,group in enumerate(item.get('captionGroups', []),1))
        published = item.get('datePublished', DATE)
        modified = item.get('dateModified', published)
        toc = ''.join(f'<a href="#step-{i}">{H(heading)}</a>' for i,(heading,_) in enumerate(item['sections'],1))
        graph = [
            {'@type':'BlogPosting','@id':url+'#article','headline':item['title'],'description':item['summary'],'url':url,'mainEntityOfPage':{'@type':'WebPage','@id':url},'datePublished':published+'T12:00:00+08:00','dateModified':modified+'T12:00:00+08:00','author':{'@type':'Organization','name':'Hoopcut','url':BASE+'/'},'publisher':{'@type':'Organization','name':'Hoopcut','url':BASE+'/'},'inLanguage':'en','wordCount':stat['words'],'image':BASE+item.get('visual', {}).get('image', '/assets/blog/court.webp'),'isPartOf':{'@type':'Blog','@id':BASE+'/blog#blog','url':BASE+'/blog','name':'Hoopcut Blog'}},
            {'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'Home','item':BASE+'/'},{'@type':'ListItem','position':2,'name':'Blog','item':BASE+'/blog'},{'@type':'ListItem','position':3,'name':item['title'],'item':url}]}
        ]
        document = head(item.get('seoTitle',SEO_TITLES.get(item['keyword'],item['title']+' | Hoopcut Blog')),item['summary'],url,graph,item.get('visual', {}).get('image', '/assets/blog/court.webp'),item.get('visual', {}).get('alt', 'Basketball court action'))+navigation()+f'''<main id="main"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a><span aria-hidden="true">/</span><a href="/blog">Blog</a><span aria-hidden="true">/</span><span aria-current="page">{H(item['title'])}</span></nav><div class="reading-layout">{resolved[item['keyword']]}<aside class="on-this-page"><p class="eyebrow">ON THIS PAGE</p><nav aria-label="On this page">{caption_toc}{toc}<a href="#checklist">Final checks</a><a href="#questions">Practical questions</a><a href="#sources">Sources</a></nav><a class="product-link" href="/">Explore Hoopcut <span aria-hidden="true">↗</span></a></aside></div><section class="related" aria-labelledby="related-title"><p class="eyebrow">KEEP READING</p><h2 id="related-title">More from the court.</h2>{cards(related,all_stats)}<a class="all-guides" href="/blog">Browse all basketball editing guides →</a></section></main>'''+footer()+'</body></html>'
        if item.get('visual'):
            document = document.replace('<body>', '<body class="visual-story'+(' caption-story' if item.get('captionGroups') else '')+'">')
        if item.get('captionGroups'):
            document = document.replace('</head>', '<script src="/assets/blog/captions.js" defer></script></head>')
        (ROOT/'blog'/(slug(item['keyword'])+'.html')).write_text(document)
    categories = list(dict.fromkeys(x['category'] for x in ARTICLES))
    index_url = BASE + '/blog'
    index_graph=[{'@type':'Blog','@id':index_url+'#blog','url':index_url,'name':'Hoopcut Blog','description':'Practical basketball video editing guides, review checklists and Shot Tracer workflows.','inLanguage':'en'},{'@type':'ItemList','itemListElement':[{'@type':'ListItem','position':i,'url':BASE+'/blog/'+slug(a['keyword']),'name':a['title']} for i,a in enumerate(ARTICLES,1)]}]
    index_graph.append({'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'Home','item':BASE+'/'},{'@type':'ListItem','position':2,'name':'Blog','item':index_url}]})
    sections=''.join(f'<section class="topic-section" id="{slug(cat)}"><div class="section-label"><h2>{H(cat)}</h2><span>{sum(x["category"]==cat for x in ARTICLES):02d} guides</span></div>{cards([x for x in ARTICLES if x["category"]==cat],all_stats)}</section>' for cat in categories)
    index=head('Basketball Highlight Guides, Captions & Team Ideas | Hoopcut','Basketball editing guides, Instagram captions and team-event ideas. Plan highlights, inspect Shot Tracer effects, and prepare media day or a season celebration.',index_url,index_graph)+navigation('index')+f'''<main id="main" class="blog-index"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a><span aria-hidden="true">/</span><span aria-current="page">Blog</span></nav><section class="index-hero"><div><p class="eyebrow">THE HOOPCUT PLAYBOOK</p><h1>Better footage.<br><span>Better highlights.</span></h1><p class="lede">Practical guides for the moments worth keeping. Learn to select the play, shape the edit and share a reel that makes sense.</p><p class="index-meta">{len(ARTICLES)} focused guides · Editing, captions & team stories</p></div><img src="/assets/blog/court.webp" width="1280" height="720" alt="Basketball players in action on an outdoor court" fetchpriority="high"></section><nav class="topic-nav" aria-label="Browse topics">{''.join('<a href="#'+slug(cat)+'">'+H(cat)+'</a>' for cat in categories)}</nav>{sections}</main>'''+footer()+'</body></html>'
    (ROOT/'blog/index.html').write_text(index)
    # The existing site's cleanUrls/trailingSlash configuration serves these paths.
    sitemap = Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    preserved = [node.text.removeprefix(BASE) for node in parse(ROOT/'sitemap.xml').getroot().findall('{*}url/{*}loc') if node.text.startswith(BASE+'/') and not node.text.removeprefix(BASE).startswith('/blog')]
    paths = list(dict.fromkeys(['/','/terms','/privacy','/blog'] + ['/blog/'+slug(a['keyword']) for a in ARTICLES] + preserved))
    for path in paths:
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
    report_dir = ROOT / 'reports'
    report_dir.mkdir(exist_ok=True)
    rows=[dict(keyword=a['keyword'],path='/blog/'+slug(a['keyword']),**all_stats[a['keyword']]) for a in ARTICLES]
    (report_dir/'hoopcut-blog-density.json').write_text(json.dumps({'definition':'exact phrase matches × phrase word count / visible article word count; excludes metadata, navigation and related cards','minimum_percent':None,'articles':rows},indent=2))
    with (report_dir/'hoopcut-blog-density.csv').open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
    print(f'Built {len(ARTICLES)} articles + blog index; sitemap has {len(paths)} URLs.')
    for row in rows:
        print(f"{row['coverage_percent']:6.2f}% {row['words']:3} words {row['exact_matches']:2} matches {row['keyword']}")


if __name__ == '__main__':
    build()
