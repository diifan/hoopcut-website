"""Idempotent video-page build adapter. Only verified public upload receipts enter sitemap."""
import json,re,hashlib,html,datetime
from pathlib import Path
from xml.etree import ElementTree as ET
ID=re.compile(r'^[A-Za-z0-9_-]{11}$')
SLUG=re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
ORIGIN='https://hoopcut.ai'
def validate(r):
 if not ID.fullmatch(r.get('video_id','')):raise ValueError('Invalid returned YouTube ID')
 if not SLUG.fullmatch(r.get('slug','')):raise ValueError('Invalid stable video slug')
 if r.get('status') not in ('public_verified','scheduled_private') or r.get('channel_handle')!='@HoopCut-Office':raise ValueError('Upload/public-channel verification required')
 if not r.get('upload_receipt_id') or not r.get('verified_at'):raise ValueError('Upload receipt required')
 if r.get('status')=='scheduled_private' and (not r.get('uploaded_at') or not r.get('scheduled_publish_at')):raise ValueError('Draft requires actual upload and schedule receipt')
 for key in ['title','description','scene_notes','source_url','published_at']:
  if not isinstance(r.get(key),str) or not r[key].strip():raise ValueError('Missing factual field: '+key)
 if not r['source_url'].startswith('https://www.youtube.com/watch?v='):raise ValueError('Invalid source URL')
 datetime.datetime.fromisoformat(r['published_at'].replace('Z','+00:00'))
 if not 1<=float(r.get('duration_seconds',0))<=3600:raise ValueError('Invalid measured duration')
 if r.get('display_aspect_ratio') not in ('9:16','16:9'):raise ValueError('Record a verified, supported display_aspect_ratio before building video '+r['slug'])
 return r

def build(root):
 root=Path(root);source=root/'content/videos/manifest.json'
 records=[validate(r) for r in json.loads(source.read_text())] if source.exists() else []
 if len({r['video_id'] for r in records})!=len(records):raise ValueError('Duplicate video IDs')
 if len({r['slug'] for r in records})!=len(records):raise ValueError('Duplicate video slugs')
 # Check all individual context before writing output; missing copy must not
 # silently fall back to a thin watch page or another video's text.
 from video_editorial import load, validate_note
 editorials={r['slug']:load(root,r) for r in records}
 media_by_id={r['video_id']:r for r in records}
 topic_file=root/'content/videos/topics.json'
 topics=json.loads(topic_file.read_text()) if topic_file.exists() else []
 for field in ['slug','title','h1','description']:
  values=[t[field] for t in topics]
  if len(set(values))!=len(values):raise ValueError('Topic '+field+' values must be unique')
 pages=list(records)
 for topic in topics:
  if topic['video_id'] not in media_by_id:raise ValueError('Topic requires a verified underlying video')
  if not SLUG.fullmatch(topic['slug']) or topic['slug'] in {p['slug'] for p in pages}:raise ValueError('Invalid or duplicate topic URL')
  note=dict(topic,meta_description=topic['description'])
  media=media_by_id[topic['video_id']]
  record=dict(media,slug=topic['slug'],title=topic['title'],h1=topic['h1'],media_title=media['title'],editorial_summary=topic['intro'],topic=True,keyword=topic['keyword'])
  editorials[topic['slug']]=validate_note(note,record)
  pages.append(record)
 site=json.loads((root/'content/site-config.json').read_text());store_url=site['app']['appStoreUrl']
 # Use the site's established design and metadata primitives.
 import sys
 sys.path.insert(0,str(root/'scripts'))
 from build_blog import head,navigation,footer
 H=html.escape
 (root/'videos').mkdir(exist_ok=True)
 records.sort(key=lambda r:r['published_at'],reverse=True)
 # Ship only the public allowlist needed by the comment API, not editorial receipts.
 (root/'lib').mkdir(exist_ok=True)
 (root/'lib/comment-videos.json').write_text(json.dumps([r['video_id'] for r in records if r['status']=='public_verified'])+'\n')
 def comment_asset(name):
  raw=(root/'assets'/name).read_bytes(); suffix=Path(name).suffix
  url='/assets/static/'+Path(name).stem+'.'+hashlib.sha256(raw).hexdigest()[:12]+suffix
  (root/'assets/static').mkdir(exist_ok=True)
  (root/url.lstrip('/')).write_bytes(raw)
  return url
 comment_css=comment_asset('video-comments.css');comment_js=comment_asset('video-comments.js')
 editorial_dates={}
 def card(r):
  vid=r['video_id'];return '<article class="card"><a href="/videos/'+r['slug']+'"><img src="/assets/videos/'+vid+'.jpg" alt="'+H(r['title'],quote=True)+'" loading="lazy" width="480" height="360" style="width:100%;height:auto"></a><h2><a href="/videos/'+r['slug']+'">'+H(r['title'])+'</a></h2><p>'+H(r['description'])+'</p></article>'
 for r in pages:
  vid=r['video_id'];url=ORIGIN+'/videos/'+r['slug']
  editorial=editorials[r['slug']]
  media=media_by_id[vid]
  video_entity=ORIGIN+'/videos/'+media['slug']+'#video'
  description=editorial['meta_description'] if editorial else r['description']
  editorial_assets=''
  if editorial:
   editorial_dates[url]=editorial['date_modified']
   editorial_assets='<link rel="stylesheet" href="'+comment_asset('video-context.css')+'">'
  cover='/assets/videos/'+vid+'.jpg'
  if not (root/cover.lstrip('/')).is_file():raise ValueError('Verified thumbnail missing: '+vid)
  graph=[{'@type':'WebPage','@id':url+'#page','url':url,'name':r['title'],'mainEntity':{'@id':video_entity}},
    {'@type':'VideoObject','@id':video_entity,'name':media['title'],'description':media['description'],'thumbnailUrl':[ORIGIN+cover],'uploadDate':media['published_at'],'duration':'PT'+str(round(media['duration_seconds']))+'S','embedUrl':'https://www.youtube.com/embed/'+vid,'publisher':{'@type':'Organization','name':'HoopCut','url':ORIGIN}},
    {'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'Home','item':ORIGIN+'/'},{'@type':'ListItem','position':2,'name':'Videos','item':ORIGIN+'/videos'},{'@type':'ListItem','position':3,'name':r.get('h1',r['title']),'item':url}]}]
  if r.get('topic'):
   graph.append({'@type':'Article','@id':url+'#article','headline':r['h1'],'description':description,'mainEntityOfPage':{'@id':url+'#page'},'associatedMedia':{'@id':video_entity},'author':{'@type':'Organization','name':'HoopCut'},'dateModified':editorial['date_modified']})
  graph.append({'@type':'FAQPage','@id':url+'#video-questions','isPartOf':{'@id':url+'#page'},'mainEntity':[{'@type':'Question','name':q,'acceptedAnswer':{'@type':'Answer','text':a}} for q,a in editorial['questions']]})
  graph[0].update(description=description,inLanguage='en')
  if editorial:graph[0]['dateModified']=editorial['date_modified']
  related=sorted([x for x in records if x['video_id']!=vid and x['status']==r['status']],key=lambda x:len(set(x.get('tags',[]))&set(r.get('tags',[]))),reverse=True)[:3]
  if any(t['video_id']==vid for t in topics):
   candidates=[p for p in pages if p['slug']!=r['slug'] and p['video_id']==vid]
   i=pages.index(r)
   related=([media] if r.get('topic') else [])+[p for p in candidates[i%len(candidates):]+candidates[:i%len(candidates)] if p['slug']!=media['slug']][:2]
   r=dict(r,related_heading='Explore this clip')
  from video_layout import detail
  css=(root/'assets/video-page.css').read_text()
  page=head(r['title'],description,url,graph,cover,r['title']).replace('</head>','<style>'+css+'</style><link rel="stylesheet" href="'+comment_css+'">'+editorial_assets+'<script src="'+comment_js+'" defer></script></head>').replace('<body>','<body class="video-page">')+navigation()+detail(r,related,store_url,editorial)+footer()+'</body></html>'
  if r['status']=='scheduled_private':
   page=page.replace('</head>','<meta name="robots" content="noindex,nofollow"></head>')
   page=page.replace('<main ', '<main data-review-draft="true" ',1)
   page=re.sub(r'<iframe.*?</iframe>', '<video controls playsinline preload="metadata" style="object-fit:contain" src="'+r['local_review_media']+'"></video>',page,count=1,flags=re.S)
   page=page.replace('<h1>', '<p class="draft-notice">Review draft · Local export preview. YouTube is scheduled and not public yet.</p><h1>',1)
  (root/'videos'/f'{r["slug"]}.html').write_text(page)
  # Preserve the published ID URL while consolidating search signals on the title URL.
  if not r.get('topic'):(root/'videos'/f'{vid}.html').write_text(page)
 if records:
  url=ORIGIN+'/videos';graph=[{'@type':'CollectionPage','url':url,'name':'HoopCut basketball videos'}]
  from video_layout import index
  css=(root/'assets/video-page.css').read_text()
  (root/'videos/index.html').write_text(head('Basketball Highlights with Shot Tracer | HoopCut','Watch basketball plays with Shot Tracer, source footage and notes about each clip.',url,graph).replace('</head>','<style>'+css+'</style></head>').replace('<body>','<body class="video-page">')+navigation()+index([r for r in records if r['status']=='public_verified'],[t for t in topics if media_by_id[t['video_id']]['status']=='public_verified'])+footer()+'</body></html>')

 tree=ET.parse(root/'sitemap.xml');ns='{http://www.sitemaps.org/schemas/sitemap/0.9}';smap=tree.getroot()
 known={x.findtext(ns+'loc') for x in smap}
 for url in ([ORIGIN+'/videos'] if records else [])+[ORIGIN+'/videos/'+r['slug'] for r in pages if r['status']=='public_verified']:
  if url not in known:
   node=ET.SubElement(smap,ns+'url');ET.SubElement(node,ns+'loc').text=url
 # Keep only preferred title URLs in the sitemap; the old ID page remains accessible.
 for node in list(smap):
  loc=node.findtext(ns+'loc')
  if loc in {ORIGIN+'/videos/'+r['video_id'] for r in records} or loc in {ORIGIN+'/videos/'+r['slug'] for r in pages if r['status']!='public_verified'}:smap.remove(node)
 for node in smap:
  modified=editorial_dates.get(node.findtext(ns+'loc'))
  if modified:
   stamp=node.find(ns+'lastmod')
   if stamp is None:stamp=ET.SubElement(node,ns+'lastmod')
   stamp.text=max(stamp.text or '',modified)
 ET.register_namespace('',ns[1:-1]);tree.write(root/'sitemap.xml',encoding='utf-8',xml_declaration=True)
 return {'video_pages':len(records),'topic_pages':len(topics),'index':bool(records)}
if __name__=='__main__':
 import sys
 print(json.dumps(build(sys.argv[1])))
