"""Render individually authored video context; never generate filler for missing records."""
import json
import re
from datetime import date
from html import escape as H


def load(root, record):
    file = root/'content/videos/editorial'/(record['slug']+'.json')
    if not file.is_file():
        raise ValueError('Author individual video context before building: '+record['slug'])
    note = json.loads(file.read_text())
    if (note['video_id'], note['slug']) != (record['video_id'], record['slug']):
        raise ValueError('Editorial notes do not match the verified video')
    date.fromisoformat(note['date_modified'])
    if any(not isinstance(note.get(k), str) or not note[k].strip() for k in ('meta_description','heading','intro')):
        raise ValueError('Video context needs its own description, heading and introduction')
    if not note.get('sections') or not note.get('questions'):
        raise ValueError('Complete the video notes and relevant questions before building')
    for section in note['sections']:
        if not section.get('heading') or not section.get('nav_title') or not section.get('paragraphs') or any(not isinstance(p,str) or not p.strip() for p in section['paragraphs']):
            raise ValueError('Each video section needs a heading, navigation label and useful text')
    if any(not isinstance(pair,list) or len(pair)!=2 or any(not isinstance(v,str) or not v.strip() for v in pair) for pair in note['questions']):
        raise ValueError('Each video question needs a factual answer')
    ids = [s['id'] for s in note['sections']]
    if len(ids) != len(set(ids)) or not all(re.fullmatch(r'[a-z][a-z0-9-]+',i) for i in ids):
        raise ValueError('Invalid or duplicate editorial anchors')
    return note


def render(note, store_url):
    if not note:
        return ''
    nav = ''.join('<a href="#'+H(s['id'],quote=True)+'">'+H(s['nav_title'])+'</a>' for s in note['sections'])
    nav += '<a href="#video-questions">Questions</a>'
    sections = []
    for i, section in enumerate(note['sections'],1):
        paragraphs = ''.join('<p>'+H(p)+'</p>' for p in section['paragraphs'])
        checks = section.get('checks',[])
        if checks:
            paragraphs += '<ol class="watch-checkpoints">'+''.join('<li><h4>'+H(title)+'</h4><p>'+H(text)+'</p></li>' for title,text in checks)+'</ol>'
        links = section.get('links',[])
        if links:
            paragraphs += '<ul class="watch-context-links">'+''.join('<li><a href="'+H(url,quote=True)+'">'+H(label)+' <span aria-hidden="true">→</span></a></li>' for label,url in links)+'</ul>'
        sections.append('<section id="'+H(section['id'],quote=True)+'" class="watch-context-section"><span class="watch-context-number" aria-hidden="true">'+str(i).zfill(2)+'</span><div><h3>'+H(section['heading'])+'</h3>'+paragraphs+'</div></section>')
    faq = '<section id="video-questions" class="watch-context-faq"><h3>Questions about this basketball clip</h3>'+''.join('<div><h4>'+H(q)+'</h4><p>'+H(a)+'</p></div>' for q,a in note['questions'])+'</section>'
    modified = date.fromisoformat(note['date_modified'])
    byline = 'Play notes by Hoopcut · Updated <time datetime="'+modified.isoformat()+'">'+modified.strftime('%B %d, %Y').replace(' 0',' ')+'</time>'
    return '<section id="video-context" class="watch-context" aria-labelledby="video-context-title"><header><p class="watch-context-kicker">BEYOND THE REPLAY</p><h2 id="video-context-title">'+H(note['heading'])+'</h2><p class="watch-context-intro">'+H(note['intro'])+'</p><p class="watch-context-byline">'+byline+'</p></header><nav class="watch-context-nav" aria-label="Explore this video">'+nav+'</nav>'+''.join(sections)+faq+'<div class="watch-context-next"><p>Bring your own game to the next edit.</p><a href="'+H(store_url,quote=True)+'" data-app-access="app-store">Download Hoopcut on the App Store <span aria-hidden="true">↗</span></a><a href="#main">Back to the video <span aria-hidden="true">↑</span></a></div></section>'
