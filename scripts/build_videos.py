"""Idempotent video-page build adapter. Only verified public upload receipts enter sitemap."""
import json,re,hashlib,html,datetime
from pathlib import Path
from xml.etree import ElementTree as ET
ID=re.compile(r'^[A-Za-z0-9_-]{11}$')
ORIGIN='https://hoopcut.ai'
def validate(r):
 if not ID.fullmatch(r.get('video_id','')):raise ValueError('Invalid returned YouTube ID')
 if r.get('status')!='public_verified' or r.get('channel_handle')!='@HoopCut-Office':raise ValueError('Upload/public-channel verification required')
 if not r.get('upload_receipt_id') or not r.get('verified_at'):raise ValueError('Upload receipt required')
 for key in ['title','description','scene_notes','source_url','published_at']:
  if not isinstance(r.get(key),str) or not r[key].strip():raise ValueError('Missing factual field: '+key)
 if not r['source_url'].startswith('https://www.youtube.com/watch?v='):raise ValueError('Invalid source URL')
 datetime.datetime.fromisoformat(r['published_at'].replace('Z','+00:00'))
 if not 1<=float(r.get('duration_seconds',0))<=3600:raise ValueError('Invalid measured duration')
 return r

def build(root):
 root=Path(root);source=root/'content/videos/manifest.json'
 records=[validate(r) for r in json.loads(source.read_text())] if source.exists() else []
 if len({r['video_id'] for r in records})!=len(records):raise ValueError('Duplicate video IDs')
 # Use the site's established design and metadata primitives.
 import sys
 sys.path.insert(0,str(root/'scripts'))
 from build_blog import head,navigation,footer
 H=html.escape
 (root/'videos').mkdir(exist_ok=True)
 records.sort(key=lambda r:r['published_at'],reverse=True)
 def card(r):
  vid=r['video_id'];return '<article class="card"><a href="/videos/'+vid+'"><img src="/assets/videos/'+vid+'.jpg" alt="'+H(r['title'],quote=True)+'" loading="lazy" width="480" height="360" style="width:100%;height:auto"></a><h2><a href="/videos/'+vid+'">'+H(r['title'])+'</a></h2><p>'+H(r['description'])+'</p></article>'
 for r in records:
  vid=r['video_id'];url=ORIGIN+'/videos/'+vid
  cover='/assets/videos/'+vid+'.jpg'
  if not (root/cover.lstrip('/')).is_file():raise ValueError('Verified thumbnail missing: '+vid)
  graph=[{'@type':'WebPage','@id':url+'#page','url':url,'name':r['title'],'mainEntity':{'@id':url+'#video'}},{'@type':'VideoObject','@id':url+'#video','name':r['title'],'description':r['description'],'thumbnailUrl':[ORIGIN+cover],'uploadDate':r['published_at'],'duration':'PT'+str(round(r['duration_seconds']))+'S','embedUrl':'https://www.youtube.com/embed/'+vid,'publisher':{'@type':'Organization','name':'HoopCut','url':ORIGIN}},{'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'Home','item':ORIGIN+'/'},{'@type':'ListItem','position':2,'name':'Videos','item':ORIGIN+'/videos'},{'@type':'ListItem','position':3,'name':r['title'],'item':url}]}]
  related=sorted([x for x in records if x['video_id']!=vid],key=lambda x:len(set(x.get('tags',[]))&set(r.get('tags',[]))),reverse=True)[:3]
  more=''.join(card(x) for x in related) or '<p><a href="/blog/how-to-add-shot-tracer-to-basketball-video">How to review a basketball Shot Tracer</a> · <a href="/tools">Basketball planning tools</a></p>'
  from video_layout import detail
  css=(root/'assets/video-page.css').read_text()
  page=head(r['title'],r['description'],url,graph,cover,r['title']).replace('</head>','<style>'+css+'</style></head>').replace('<body>','<body class="video-page">')+navigation()+detail(r)+footer()+'</body></html>'
  (root/'videos'/f'{vid}.html').write_text(page)
 if records:
  url=ORIGIN+'/videos';graph=[{'@type':'CollectionPage','url':url,'name':'HoopCut basketball videos'}]
  from video_layout import index
  css=(root/'assets/video-page.css').read_text()
  (root/'videos/index.html').write_text(head('Basketball Highlights with Shot Tracer | HoopCut','Watch basketball plays with Shot Tracer, source footage and notes about each clip.',url,graph).replace('</head>','<style>'+css+'</style></head>').replace('<body>','<body class="video-page">')+navigation()+index(records)+footer()+'</body></html>')

 tree=ET.parse(root/'sitemap.xml');ns='{http://www.sitemaps.org/schemas/sitemap/0.9}';smap=tree.getroot()
 known={x.findtext(ns+'loc') for x in smap}
 for url in ([ORIGIN+'/videos'] if records else [])+[ORIGIN+'/videos/'+r['video_id'] for r in records]:
  if url not in known:
   node=ET.SubElement(smap,ns+'url');ET.SubElement(node,ns+'loc').text=url
 ET.register_namespace('',ns[1:-1]);tree.write(root/'sitemap.xml',encoding='utf-8',xml_declaration=True)
 return {'video_pages':len(records),'index':bool(records)}
if __name__=='__main__':
 import sys
 print(json.dumps(build(sys.argv[1])))
