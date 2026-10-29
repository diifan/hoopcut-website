"""Apply the 2026-10-28 audit fixes after the complete content build.

No network, deployment, account settings or fabricated product evidence.
"""
import hashlib
import json
import re
from html import escape as H
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urljoin
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://hoopcut.ai'
DATE = '2026-10-29'


def dumps(data):
    return json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')


class Tag(HTMLParser):
    def __init__(self, raw):
        super().__init__(); self.attrs = {}; self.name = ''; self.feed(raw)

    def handle_starttag(self, name, attrs):
        self.name = name; self.attrs = dict(attrs)

    def handle_startendtag(self, name, attrs):
        self.handle_starttag(name, attrs)

    def render(self):
        return '<' + self.name + ''.join(' '+k if v is None else ' '+k+'="'+H(str(v), quote=True)+'"' for k,v in self.attrs.items()) + '>'


def local_path(value):
    url = urlsplit(urljoin(BASE+'/', value))
    return url.path if url.netloc == 'hoopcut.ai' else ''


def build():
    config = json.loads((ROOT/'content/site-config.json').read_text())
    assert config['app']['status'] == 'app-store'
    media = json.loads((ROOT/'content/seo-media.json').read_text())
    static_file = ROOT/'content/seo-static.json'
    old_static = json.loads(static_file.read_text()) if static_file.exists() else {}
    reverse = {v['url']: k for k,info in media['images'].items() for v in info['variants']}
    reverse.update({v:k for k,v in old_static.items()})
    # Read source paths even on repeated builds of already processed root/demo files.
    def restore(source):
        for output, original in reverse.items():
            source = source.replace(output, original)
        seen = set()
        def stylesheet(match):
            tag = Tag(match[0]); href = tag.attrs.get('href','')
            if tag.attrs.get('rel') != 'stylesheet': return match[0]
            if href in seen: return ''
            seen.add(href); return match[0]
        source = re.sub(r'<link\b[^>]*>', stylesheet, source)
        return source

    request_url = config['app']['appStoreUrl']
    store = urlsplit(request_url)
    assert store.scheme == 'https' and store.netloc == 'apps.apple.com' and store.path.endswith('/id'+config['app']['appId']), 'Use the verified app detail URL'

    images = media['images']
    def variant(src, width=960):
        info = images[src]
        return min(info['variants'], key=lambda v:abs(v['width']-width))['url']

    hero_media = {key:{'desktop':info['variants']['desktop']['url'], 'mobile':info['variants']['mobile']['url'], 'poster':variant('/assets/video/players/'+key+'.jpg',960)} for key,info in media['videos'].items()}

    def access_anchor(match):
        tag = Tag('<a'+match[1]+'>')
        href = tag.attrs.get('href','')
        is_access_mail = href.startswith('mailto:') and any(x in href.lower() for x in ['testflight','iphone%20access'])
        if 'apps.apple.com' not in href and not tag.attrs.get('data-app-access') and not is_access_mail:
            return match[0]
        tag.attrs['href'] = request_url
        tag.attrs['data-app-access'] = 'app-store'
        tag.attrs.pop('target',None); tag.attrs.pop('rel',None)
        content = '<span class="store-label"><span>Download on the</span><strong>App Store</strong></span>' if 'store-label' in match[2] else 'Get the app' if 'nav-download' in tag.attrs.get('class','') else 'Download Hoopcut on the App Store'
        return tag.render()+content+'</a>'

    def optimize_tag(match):
        tag = Tag(match[0]); a = tag.attrs
        if tag.name == 'link' and a.get('rel') == 'icon':
            a['href'] = images['/assets/icon.png']['favicon']
            a['type'] = 'image/png'; a['sizes'] = '48x48'
        if tag.name in ('img','image'):
            attr = 'src' if tag.name == 'img' else 'href'
            src = local_path(a.get('data-original-'+attr, a.get(attr,'')))
            if src in images:
                a['data-original-'+attr] = src
                a[attr] = variant(src, 96 if 'icon' in src else 960)
                if tag.name == 'img':
                    a['srcset'] = ', '.join(v['url']+' '+str(v['width'])+'w' for v in images[src]['variants'])
                    a['sizes'] = '32px' if 'icon' in src else '(max-width: 700px) 90vw, (max-width: 1100px) 46vw, 640px' if any(x in a.get('class','') for x in ['hero-design','card-cover']) or '/resources/' in src else '(max-width: 700px) 90vw, 1000px'
                    a['decoding'] = 'async'
        if tag.name == 'video':
            src = local_path(a.get('data-original-poster', a.get('poster','')))
            if src in images:
                a['data-original-poster'] = src
                a['poster'] = variant(src,960)
        if tag.name == 'source' and '/assets/video/players/all.mp4' in a.get('data-original-src', a.get('src','')):
            a['data-original-src'] = '/assets/video/players/all.mp4'
            a['src'] = hero_media['all']['desktop']
        return tag.render()

    files = [ROOT/'index.html', ROOT/'terms.html', ROOT/'privacy.html', ROOT/'tools.html', *ROOT.glob('blog/*.html'), *ROOT.glob('templates/*.html'), *ROOT.glob('demo/*.html')]
    changed_paths = []
    for file in files:
        before = file.read_text(); src = restore(before)
        src = re.sub(r'<!-- AUDIT SETTINGS START -->.*?<!-- AUDIT SETTINGS END -->', '', src, flags=re.S)
        src = re.sub(r'<a\b([^>]*)>(.*?)</a>', access_anchor, src, flags=re.S)
        src = src.replace('TestFlight access · request by email', 'Available on the App Store for iPhone')
        src = src.replace('Join the Hoopcut TestFlight beta', 'Available on the App Store for iPhone')
        src = src.replace('Can I try Hoopcut for free?', 'Where can I download Hoopcut?')
        for old in ['Yes. Search for Hoopcut on the App Store to download the app and try it for free.', 'Hoopcut is currently in TestFlight testing on iPhone. Email us to request access; availability and testing terms are confirmed with your invitation.']:
            src = src.replace(old, 'Hoopcut is available on the App Store for iPhone. Download the app to create basketball highlights with auto clipping and Shot Tracer. Check the App Store listing for current pricing, device requirements and availability.')
        src = src.replace('Current access and feature availability may vary.', 'Available on the App Store for iPhone. Check the listing for device requirements and current feature availability.')
        if file == ROOT/'index.html':
            # The original customer review block is intentionally untouched.
            src = re.sub(r'(<video\b[^>]*id="banner-video"[^>]*>).*?(</video>)', r'\1\2', src, flags=re.S)
            src = re.sub(r'<video\b[^>]*id="banner-video"[^>]*>', lambda m:m[0].replace(' autoplay','').replace('preload="metadata"','preload="none"'), src)
            src = src.replace('<section class="hero" aria-label=', '<section class="hero" aria-label=', 1)
            if 'Who makes Hoopcut?' not in src:
                src = src.replace('</div></section><div class="end">', '<details><summary>Who makes Hoopcut?</summary><p>Hoopcut is a basketball video app by SWINK AI INC., focused on auto clipping and Shot Tracer. Its free browser tools help with planning and graphics. Questions or feedback? <a href="mailto:hello@goswie.com">Contact the Hoopcut team</a>.</p></details></div></section><div class="end">', 1)
        if file == ROOT/'blog/index.html':
            src = src.replace('Better footage.<br><span>Better highlights.</span>', 'Basketball guides.<br><span>Better highlights.</span>')
        src = re.sub(r'<(?:img|image|video|source|link)\b[^>]*>', optimize_tag, src)

        # Organization identity is shared; schema never invents price or ratings.
        def schema(match):
            data = json.loads(match[1]); nodes = data.get('@graph',[data])
            nodes = [x for x in nodes if x.get('@id') != BASE+'/#organization']
            org = {'@type':'Organization','@id':BASE+'/#organization','name':'Hoopcut','legalName':'SWINK AI INC.','url':BASE+'/','logo':{'@type':'ImageObject','url':BASE+'/assets/blog/brand-icon.png'},'email':config['app']['contactEmail'],'description':'Basketball auto clipping and Shot Tracer for iPhone.'}
            nodes.append(org)
            for node in nodes:
                if node.get('@type') in ['WebSite','WebPage','CollectionPage','Blog','BlogPosting']:
                    node['publisher'] = {'@id':org['@id']}
                for key in ('author','publisher'):
                    if isinstance(node.get(key),dict) and node[key].get('name') == 'Hoopcut': node[key]['@id'] = org['@id']
            return '<script type="application/ld+json">'+dumps({'@context':'https://schema.org','@graph':nodes})+'</script>'
        src = re.sub(r'<script type="application/ld\+json">(.*?)</script>', schema, src, flags=re.S)
        settings = '<!-- AUDIT SETTINGS START --><script id="site-settings" type="application/json">'+dumps({'analytics':config['analytics']})+'</script><script src="/assets/site-events.js" defer></script>'
        if file == ROOT/'index.html':
            settings += '<meta name="apple-itunes-app" content="app-id='+config['app']['appId']+'">'
            settings += '<script id="hero-media-data" type="application/json">'+dumps(hero_media)+'</script>'
            # Preload the poster used as the background video's first frame.
            settings += '<link rel="preload" as="image" href="'+hero_media['all']['poster']+'" fetchpriority="high">'
        src = src.replace('</head>', settings+'<!-- AUDIT SETTINGS END --></head>')
        file.write_text(src)
        if src != before:
            changed_paths.append('/' if file == ROOT/'index.html' else '/blog' if file == ROOT/'blog/index.html' else '/'+str(file.relative_to(ROOT)).removesuffix('.html'))

    # Fingerprint CSS/JS only after content and scripts are final. Their source
    # paths remain available for editing and for media generated dynamically.
    static = {}
    target = ROOT/'assets/static'; target.mkdir(exist_ok=True)
    for file in files:
        src = file.read_text()
        def fingerprint(match):
            value = match[2]; original = local_path(value)
            if not original.startswith('/assets/') or not original.endswith(('.css','.js')): return match[0]
            path = ROOT/original.lstrip('/'); raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()[:12]
            output = '/assets/static/'+path.stem+'.'+digest+path.suffix
            (ROOT/output.lstrip('/')).write_bytes(raw); static[original] = output
            return match[1]+'"'+output+'"'
        src = re.sub(r'((?:src|href)=)"([^"]+)"', fingerprint, src)
        file.write_text(src)
    static_file.write_text(json.dumps(static,indent=2)+'\n')
    # This rollout changes metadata/media/shared navigation on every URL.
    ns = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
    tree = ET.parse(ROOT/'sitemap.xml')
    for node in tree.getroot():
        stamp = node.find(ns+'lastmod')
        if stamp is None: stamp = ET.SubElement(node,ns+'lastmod')
        stamp.text = DATE
    ET.register_namespace('', ns[1:-1]); tree.write(ROOT/'sitemap.xml',encoding='utf-8',xml_declaration=True)
    settings = json.loads((ROOT/'vercel.json').read_text())
    settings['redirects'] = [{'source':'/:path*','has':[{'type':'host','value':'www.hoopcut.ai'}],'destination':'https://hoopcut.ai/:path*','permanent':True}]
    settings['headers'] = [{'source':p,'headers':[{'key':'Cache-Control','value':'public, max-age=31536000, immutable'}]} for p in ['/assets/optimized/:path*','/assets/static/:path*']]
    (ROOT/'vercel.json').write_text(json.dumps(settings,indent=2)+'\n')
    print(f'Polished {len(files)} local pages; App Store downloads and anonymous event hooks; no publishing.')


if __name__ == '__main__':
    build()
