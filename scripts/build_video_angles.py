#!/usr/bin/env python3
"""Build ten isolated local watch-page candidates around one verified video.

Does not modify the production manifest, sitemap, comments store or release PR.
Each candidate has its own useful worksheet, editorial angle and comment thread.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import re
import secrets
import shutil
import sys
import time
from datetime import datetime, timezone
from html import escape as H
from html.parser import HTMLParser
from http.server import ThreadingHTTPServer
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/video-angles'
BASE='https://hoopcut.ai'
sys.path.insert(0,str(ROOT/'scripts'))
from video_angle_content import PAGES
from build_videos import validate
from video_editorial import load, render
from video_layout import detail
from build_blog import head, navigation, footer


def slug_valid(value):
    return bool(re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',value))


def note_for(page,media):
    sections=[]
    for i,(slug,title,text) in enumerate(page['sections']):
        section={'id':slug,'nav_title':title.split(':')[0], 'heading':title,'paragraphs':[text]}
        if i==len(page['sections'])-1:section['links']=page['links']
        sections.append(section)
    if page.get('checks_extra'):
        sections.append({'id':'caption-options','nav_title':'Caption options','heading':'Six basketball caption options to adapt','paragraphs':page['checks_extra']})
    return {'video_id':media['video_id'],'slug':page['slug'],'date_modified':'2026-11-05',
            'meta_description':page['description'],'heading':page['question'],
            'intro':'Use the '+page['download'].lower()+' to keep your observations and next editing decision together.',
            'sections':sections,'questions':page['faq']}


def summary_metrics(page):
    text=' '.join([page['intro'],page['question']]+[t+' '+p for _,t,p in page['sections']]+[q+' '+a for q,a in page['faq']]+[t+' '+v for t,v in page['checks']]+page.get('checks_extra',[]))
    words=re.findall(r"[a-z0-9]+(?:['’][a-z]+)?",text.lower())
    phrase=re.findall(r'[a-z0-9]+',page['keyword'].lower())
    occurrences=sum(words[i:i+len(phrase)]==phrase for i in range(len(words)-len(phrase)+1))
    grams={' '.join(words[i:i+5]) for i in range(max(0,len(words)-4))}
    return {'words':len(words),'exact_topic_mentions':occurrences,
            'topic_occurrences_per_100_words':round(100*occurrences/len(words),2),
            'topic_word_coverage_percent':round(100*occurrences*len(phrase)/len(words),2),
            'basketball_word_percent':round(100*words.count('basketball')/len(words),2)},grams


def build():
    media=next(r for r in json.loads((ROOT/'content/videos/manifest.json').read_text()) if r['video_id']=='MLcda_7VYkQ')
    validate(media)
    assert len(PAGES)==10
    for field in ['slug','title','description','question']:
        assert len({p[field] for p in PAGES})==10,field
    assert all(slug_valid(p['slug']) for p in PAGES)
    comments=[c for p in PAGES for c in p['examples']]
    assert len(comments)==len(set(comments))==30
    site=OUT/'site';site.mkdir(parents=True,exist_ok=True)
    for folder in ['videos','api','downloads','content/videos/editorial']:(site/folder).mkdir(parents=True,exist_ok=True)
    for name in ['assets','blog','templates','demo','index.html','tools.html','terms.html','privacy.html']:
        link=site/name
        if not link.exists():link.symlink_to(ROOT/name,target_is_directory=(ROOT/name).is_dir())
    for name in [media['slug']+'.html',media['video_id']+'.html']:
        link=site/'videos'/name
        if not link.exists():link.symlink_to(ROOT/'videos'/name)
    config=json.loads((ROOT/'content/site-config.json').read_text())
    records=[dict(media,slug=p['slug'],title=p['title'],editorial_summary=p['intro']) for p in PAGES]
    threads=['angle:'+p['slug'] for p in PAGES]
    (site/'api/video-ids.json').write_text(json.dumps(threads+[media['video_id']])+'\n')
    css=(ROOT/'assets/video-page.css').read_text()
    extras='<link rel="stylesheet" href="/assets/video-comments.css"><link rel="stylesheet" href="/assets/video-context.css"><script src="/assets/video-comments.js" defer></script>'
    inventory=[];gram_sets=[]
    for i,(page,record,thread) in enumerate(zip(PAGES,records,threads)):
        note=note_for(page,media)
        (site/'content/videos/editorial'/(page['slug']+'.json')).write_text(json.dumps(note,ensure_ascii=False,indent=2)+'\n')
        load(site,record)  # Same per-video content contract as the production template.
        url=BASE+'/videos/'+page['slug'];video_entity=BASE+'/videos/'+media['slug']+'#video'
        graph=[{'@type':'WebPage','@id':url+'#page','url':url,'name':page['title'],
                'description':page['description'],'inLanguage':'en','dateModified':'2026-11-05',
                'mainEntity':{'@id':video_entity},'about':{'@type':'Thing','name':page['keyword']}},
               {'@type':'VideoObject','@id':video_entity,'name':media['title'],'description':media['description'],
                'thumbnailUrl':[BASE+'/assets/videos/'+media['video_id']+'.jpg'],'uploadDate':media['published_at'],
                'duration':'PT'+str(round(media['duration_seconds']))+'S','embedUrl':'https://www.youtube.com/embed/'+media['video_id'],
                'publisher':{'@type':'Organization','name':'HoopCut','url':BASE}},
               {'@type':'BreadcrumbList','itemListElement':[
                {'@type':'ListItem','position':1,'name':'Home','item':BASE+'/'},
                {'@type':'ListItem','position':2,'name':'Videos','item':BASE+'/videos'},
                {'@type':'ListItem','position':3,'name':page['title'],'item':url}]}]
        related=[records[(i+1)%10],records[(i+2)%10]]
        body=detail(record,related,config['app']['appStoreUrl'],note)
        needle='data-video-id="'+media['video_id']+'"';assert body.count(needle)==1
        body=body.replace(needle,'data-video-id="'+H(thread,quote=True)+'"')
        body=body.replace('<h2>More videos</h2>','<h2>Other views of this clip</h2>')
        body=body.replace('aria-label="More basketball videos and guides"','aria-label="Other views of this clip and related guides"')
        # A page-specific native checklist and a real editable download add utility.
        download='/downloads/'+page['slug']+'.csv'
        with (site/download.lstrip('/')).open('w',newline='') as f:
            writer=csv.writer(f);writer.writerow(['Check','Prompt or example','Your notes']);writer.writerows((a,b,'') for a,b in page['checks'])
            if page.get('checks_extra'):writer.writerows(('Caption option',line,'') for line in page['checks_extra'])
        worksheet='<section class="angle-worksheet" aria-labelledby="worksheet-title"><p class="watch-context-kicker">USE THIS WHILE YOU WATCH</p><h2 id="worksheet-title">'+H(page['download'])+'</h2><p>Mark what you have reviewed. These checks stay on this page; download the editable worksheet to keep your own notes.</p><fieldset><legend class="sr-only">'+H(page['download'])+'</legend>'+''.join('<label><input type="checkbox"><span><strong>'+H(title)+'</strong>'+H(text)+'</span></label>' for title,text in page['checks'])+'</fieldset><a href="'+download+'" download>Download this basketball worksheet (CSV) ↓</a></section>'
        worksheet_css='.angle-worksheet{margin:30px 0;padding:23px;background:#191e17;border:1px solid #ffffff25;border-radius:12px}.angle-worksheet p{font-size:13px;color:#b7c1aa;line-height:1.7}.angle-worksheet fieldset{padding:0;border:0;margin:18px 0}.angle-worksheet label{display:flex;gap:12px;align-items:flex-start;padding:12px 0;border-top:1px solid #ffffff15;cursor:pointer;font-size:13px;line-height:1.65;color:#bdc8b0}.angle-worksheet strong{display:block;color:#f0f1e6;font-size:14px}.angle-worksheet input{width:18px;height:18px;flex:none;margin-top:4px;accent-color:#ff975f}.angle-worksheet a{font-size:13px;color:#ffb085}.sr-only{position:absolute;width:1px;height:1px;padding:0;overflow:hidden;clip:rect(0,0,0,0)}'
        body=body.replace('<section class="video-notes">',worksheet+'<section class="video-notes">',1)
        html=head(page['title'],page['description'],url,graph,'/assets/videos/'+media['video_id']+'.jpg','Two pickup basketball jump shots with an existing ball trail')
        html=html.replace('property="og:type" content="article"','property="og:type" content="video.other"')
        html=html.replace('</head>','<style>'+css+worksheet_css+'</style>'+extras+'</head>').replace('<body>','<body class="video-page">')
        (site/'videos'/(page['slug']+'.html')).write_text(html+navigation()+body+footer()+'</body></html>')
        metrics,grams=summary_metrics(page);gram_sets.append(grams)
        inventory.append({'slug':page['slug'],'title':page['title'],'description':page['description'],
                          'path':'/videos/'+page['slug'],'keyword':page['keyword'],'thread':thread,
                          'same_video_id':media['video_id'],'download':download,'metrics':metrics,
                          'content_sha256':hashlib.sha256(json.dumps(page,sort_keys=True).encode()).hexdigest()})
    # Honest collection: ten editorial perspectives, one underlying recording.
    hub='<main id="main"><p class="video-kicker">ONE CLIP / TEN QUESTIONS</p><h1>Ten ways to review<br>one basketball clip.</h1><p class="index-lede">These pages use the same verified pickup video. Each focuses on a different editing question and includes its own worksheet and discussion. Local review candidates; no additional footage is claimed.</p><div class="video-grid">'+''.join('<article class="video-tile"><a href="'+p['path']+'"><img src="/assets/videos/'+media['video_id']+'.jpg" width="480" height="360" alt="Same basketball clip, viewed for '+H(p['keyword'],quote=True)+'"><div class="tile-copy"><p class="video-kicker">'+str(i).zfill(2)+' / '+H(p['keyword'])+'</p><h2>'+H(p['title'].replace(' | Hoopcut',''))+'</h2><p>'+H(p['description'])+'</p></div></a></article>' for i,p in enumerate(inventory,1))+'</div></main>'
    (site/'videos/index.html').write_text(head('Ten Basketball Video Review Angles | Hoopcut','One pickup clip, ten different basketball editing questions, practical worksheets and separate discussions.',BASE+'/videos',[{'@type':'CollectionPage','name':'Ten perspectives on one basketball clip','url':BASE+'/videos'}]).replace('</head>','<style>'+css+'</style></head>').replace('<body>','<body class="video-page">')+navigation()+hub+footer()+'</body></html>')
    (site/'robots.txt').write_text('User-agent: *\nDisallow: /\n')
    smap=Element('urlset',xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    for p in inventory:
        n=SubElement(smap,'url');SubElement(n,'loc').text=BASE+p['path']
    (site/'sitemap.xml').write_bytes(tostring(smap,encoding='utf-8',xml_declaration=True))
    pairs=[]
    for i in range(10):
        for j in range(i+1,10):
            pairs.append({'a':PAGES[i]['slug'],'b':PAGES[j]['slug'],'five_word_jaccard':round(len(gram_sets[i]&gram_sets[j])/len(gram_sets[i]|gram_sets[j]),4)})
    report={'pages':inventory,'page_count':10,'underlying_video_count':1,'sample_comments':30,
            'comment_threads':10,'same_video_url':media['video_id'],'local_only':True,'deployed':False,
            'metrics_note':'Visible authored text only; density is diagnostic, not a ranking target. Excludes metadata, navigation and fictional comments.',
            'overlap_note':'Internal 5-word overlap only, not an AI detector or external plagiarism score.',
            'max_pair_overlap':max(pairs,key=lambda p:p['five_word_jaccard']),'pairs':pairs}
    (OUT/'inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return site,report


def serve(site,port):
    import os
    import preview_site
    import preview_comments
    preview_site.ROOT=site
    preview_comments.api.ROOT=site
    os.environ['COMMENTS_SQLITE_PATH']=str(OUT/'comments.sqlite3')
    os.environ['COMMENTS_PREVIEW']='1'
    if os.environ.get('VERCEL') or os.environ.get('COMMENTS_DATABASE_URL'):
        raise RuntimeError('Local sample seeding is not permitted against a hosted database')
    db=preview_comments.api.Database()
    with db.connect() as conn:
        for i,page in enumerate(PAGES):
            thread='angle:'+page['slug']
            for j,text in enumerate(page['examples']):
                key='angle-example:'+page['slug']+':'+str(j)
                if db.query(conn,'SELECT 1 FROM hc_comments WHERE request_key=?',(key,)).fetchone():continue
                visitor,_=db.visitor(conn,None)
                db.query(conn,'''INSERT INTO hc_comments(id,video_id,parent_id,visitor,name,body,created_at,request_key,is_example)
                                VALUES (?,?,NULL,?,?,?,?,?,1)''',
                         (secrets.token_hex(16),thread,visitor,'Guest '+str(i+1).zfill(2)+'-'+str(j+1),text,int(time.time()*1000)-(j+1)*60000,key))
    server=ThreadingHTTPServer(('127.0.0.1',port),preview_comments.Handler)
    print('Local review: http://127.0.0.1:'+str(server.server_address[1])+'/videos',flush=True)
    server.serve_forever()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--serve',action='store_true');parser.add_argument('--port',type=int,default=8771);args=parser.parse_args()
    site,report=build();print(json.dumps({'pages':10,'video_files':1,'site':str(site),'deployed':False}),flush=True)
    if args.serve:serve(site,args.port)
