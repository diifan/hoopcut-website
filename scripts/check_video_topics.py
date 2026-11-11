#!/usr/bin/env python3
"""Check real generated topic pages against their shared media and authored content."""
import itertools,json,re,html
from pathlib import Path
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
topics=json.loads((ROOT/'content/videos/topics.json').read_text())
media={r['video_id']:r for r in json.loads((ROOT/'content/videos/manifest.json').read_text())}
assert len(topics)==28
urls=[x.text for x in ET.parse(ROOT/'sitemap.xml').findall('{*}url/{*}loc')]
seen={k:set() for k in ['title','h1','description','body','faq']};bodies={};records=[]
def graph(source):
 out=[]
 for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>',source,re.S):
  d=json.loads(raw);out.extend(d.get('@graph',[d]))
 return out
for t in topics:
 path='/videos/'+t['slug'];url='https://hoopcut.ai'+path
 src=(ROOT/(path[1:]+'.html')).read_text();built=(ROOT/'dist'/(path[1:]+'.html')).read_text()
 assert t['h1'] in built and 'data-video-comments' in built,('missing production output',path)
 base=(ROOT/'videos'/(media[t['video_id']]['slug']+'.html')).read_text()
 assert re.findall(r'<iframe[^>]*src="([^"]+)"',src)==re.findall(r'<iframe[^>]*src="([^"]+)"',base),('same video player',path)
 assert 'data-video-comments data-video-id="'+t['video_id']+'"' in src
 assert re.findall(r'<link rel="canonical" href="([^"]+)"',src)==[url]
 assert urls.count(url)==1
 assert 'noindex' not in src
 vals={'title':html.unescape(re.search(r'<title>(.*?)</title>',src)[1]),'h1':html.unescape(re.search(r'<h1>(.*?)</h1>',src)[1]),'description':t['description'],'body':json.dumps(t['sections']),'faq':json.dumps(t['questions'])}
 assert len(re.findall(r'<h1\b',src))==1 and vals['h1']==t['h1']
 for k,v in vals.items():assert v not in seen[k],('duplicate',k,path);seen[k].add(v)
 g=graph(src);v=next(x for x in g if x['@type']=='VideoObject');original=next(x for x in graph(base) if x['@type']=='VideoObject');assert v==original,('video facts diverged',path)
 crumb=next(x for x in g if x['@type']=='BreadcrumbList');assert crumb['itemListElement'][-1]['item']==url
 faq=next(x for x in g if x['@type']=='FAQPage')['mainEntity']
 assert [(q['name'],q['acceptedAnswer']['text']) for q in faq]==[tuple(x) for x in t['questions']]
 for q,a in t['questions']:assert html.escape(q) in src and html.escape(a) in src
 assert all(html.escape(p) in src for sec in t['sections'] for p in sec['paragraphs'])
 assert 'id="video-context"' in src and 'aria-label="Breadcrumb"' in src
 assert 'href="'+path+'"' in (ROOT/'videos/index.html').read_text()
 text=' '.join([t['intro']]+[p for sec in t['sections'] for p in sec['paragraphs']]+[x for qa in t['questions'] for x in qa])
 words=re.findall(r'[a-z0-9]+',text.lower());bodies[t['slug']]={' '.join(words[i:i+5]) for i in range(len(words)-4)}
 records.append({'path':path,'title':t['title'],'h1':t['h1'],'intent':t['keyword'],'authored_words':len(words),'shared_video_id':t['video_id']})
pairs=[]
for a,b in itertools.combinations(bodies,2):
 score=len(bodies[a]&bodies[b])/len(bodies[a]|bodies[b]);assert score<.3,('near duplicate body',a,b,score);pairs.append((score,a,b))
report={'status':'pass','pages':records,'maximum_internal_five_word_overlap':max(pairs),'note':'Overlap checks compare authored topic text only; not an indexing or ranking prediction.'}
(ROOT/'reports').mkdir(exist_ok=True);(ROOT/'reports/video-topics-checks.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: 28 generated topic pages; unique content/metadata, shared factual video, FAQ, breadcrumbs, canonical, sitemap, links and matching dist output.')
print('Maximum pairwise five-word overlap:',round(max(pairs)[0],4))
