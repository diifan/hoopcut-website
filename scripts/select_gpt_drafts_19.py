import json,csv,re,pathlib,collections
from prepare_hudl_tracer_batch import slugify
from tracer_keyword_policy import rejection_reason, identity_aligned
W=pathlib.Path(__file__).resolve().parents[1];O=W/'reports/tracer-daily-20261119';D=pathlib.Path('/var/lib/swi-codex/xcut-seo-agent/data/tracer-keywords-199');R=pathlib.Path('/data/swi-algo/Swi-IP-Config/swie-app-mac/data/tracer-daily/2026-11-19-receipt.json')
pages=json.load(open(W/'content/shot-tracer/batches/tracer-daily-20261119/pages.json'));used={x['keyword'].casefold() for x in pages};slugs={x['slug'] for x in pages};base=set(json.load(open(R.with_name('2026-11-19-baseline.json'))));available={r['keyword'].casefold() for r in csv.DictReader(open(D/'keywords.csv')) if r['status']=='available'}
probes={r['source_url']:r for r in json.load(open(O/'source-probes.json'))};sources={}
for f in json.load(open(D/'manifest.json'))['sources']:
 for row in csv.DictReader(open(f['local_path'],encoding='utf-8-sig')):sources.setdefault(row['Keyword'].casefold(),row)
exclude=re.compile(r'\b(weather|obituar\w*|funeral|death|dead|murder|arrest|jail|prison|porn|nude|sex|restaurant\w*|pizza|barber\w*|salon|real estate|realtor|auction\w*|financial|bank|loan|insurance|dentist|dental|hospital|clinic|veterinar\w*|church|bible|sermon|prayer|meaning|pronounce|recipe|menu|lyrics|movie|novel|book|wedding|divorce|wife|husband|net worth|salary|jobs|employment|tuition|admission\w*|calendar|lunch|powerschool|login|log in|tickets|scores?|live|stream\w*|rankings?|roster|vs|football|soccer|baseball|softball|hockey|volleyball|lacrosse|wrestling|rugby|cricket|golf|swimming|gymnastics|cheerleading|tennis)\b',re.I)
def tokens(s):return set(re.findall(r'[a-z]{3,}',s.lower()))-{'the','and','school','high','hudl','home','sports','club','highlights','with','junior','senior','boys','girls','team'}
rows=[];counts=collections.Counter();decisions=[]
for k,r in sources.items():
 slug=slugify(k);u=r.get('URL','');p=probes.get(u,{})
 if k not in available or k in used or slug in slugs or 'https://hoopcut.ai/shot-tracer/'+slug in base:counts['occupied_or_unavailable']+=1;continue
 if exclude.search(k) or rejection_reason(k):counts['explicit_unrelated_intent']+=1;continue
 title=p.get('title','');txt=p.get('text_excerpt','');typ='school-sports-source' if '/organization/' in u or '/team/' in u else 'sports-video-source' if '/video/' in u else 'sports-profile-source' if '/profile/' in u else 'editing-workflow'
 # Confirm keyword alignment with cached identity/title, without requiring basketball terms.
 aligned=identity_aligned(k,title);school=bool(re.search(r'\b(school|academy|college|university|prep|isd|hs)\b',k,re.I))
 workflow='hudl' in k and bool(re.search(r'video|edit|highlight|clip|download|upload|library|camera|telestrat',k))
 if not ((p.get('http')==200 and aligned and typ!='editing-workflow') or (school and 'hudl.com' in u and '/organization/' in u) or workflow):counts['unresolved_context_or_alignment']+=1;continue
 priority=0 if typ=='school-sports-source' or school else 1 if workflow else 2 if typ=='sports-video-source' else 3
 rows.append({'keyword':r['Keyword'],'source_url':u,'clip_type':'saved basketball clip','context_type':typ,'cached_title':title,'flags':['draft_context_review_pending'],'priority':priority,'volume':int(float(r.get('Search Volume','0') or 0))});counts['eligible']+=1
rows.sort(key=lambda x:(x['priority'],-x['volume'],x['keyword']));selected=[];taken=set(slugs)
for r in rows:
 s=slugify(r['keyword'])
 if s in taken:continue
 selected.append(r);taken.add(s)
 if len(selected)==2000-len(pages):break
for i,n in enumerate('abc'):(O/f'gpt-selection-{n}.json').write_text(json.dumps(selected[i::3],ensure_ascii=False,indent=2))
summary={'existing':len(pages),'eligible':len(rows),'selected':len(selected),'remaining':2000-len(pages)-len(selected),'classification_counts':dict(counts),'selected_contexts':dict(collections.Counter(x['context_type'] for x in selected))};(O/'gpt-selection-summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
