#!/usr/bin/env python3
"""Prepare a traceable first 1,000-keyword Hudl release on the shared Tracer UI."""
import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit, urlunsplit

import build_shot_tracer as tracer

ROOT = Path(__file__).resolve().parents[1]
BATCH = 'hudl-20261113-1000'
TARGET = 1000
SEEDS = ['basketball editor', 'types of basketball shots', "gannon men's basketball", 'ferris state football']
CATEGORIES = {
 'basketball-skills': ('Basketball shots & skills', 'Connect basketball shot terms and visible play details with your own traced recording.'),
 'basketball-training': ('Basketball practice recordings', 'Prepare practice footage, preserve session context and add a tracer to a visible shot.'),
 'basketball-teams': ('Team & player video context', 'Find a team or player source, then work with your own clearly identified basketball footage.'),
 'basketball-schedules': ('Schedules, scores & footage', 'Check the event source and keep dates, scores and video excerpts correctly identified.'),
 'basketball-video': ('Basketball editing workflows', 'Choose basketball footage, review a shot trail and save a clearly labeled highlight.'),
 'scouting': ('Scouting footage preparation', 'Keep source footage and player context organized when preparing a basketball highlight.'),
 'sports-video': ('Sports recording workflows', 'Plan sports recordings and use the basketball Tracer on your own court footage.'),
 'fan-basketball': ('Fans on the basketball court', 'Bring your own basketball clip into HoopCut while keeping team information and other sports distinct.'),
}

def normalized(value):
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().replace('’', "'").split())

def slugify(value):
    ascii_value = unicodedata.normalize('NFKD', value).encode('ascii','ignore').decode()
    return re.sub(r'[^a-z0-9]+','-',ascii_value.lower().replace("'",'')).strip('-')[:130].rstrip('-')

def context(row):
    keyword = row['Keyword']; key = normalized(keyword); url = row['URL']
    parsed = urlsplit(url)
    if parsed.scheme not in ('https','http') or not (parsed.hostname == 'hudl.com' or (parsed.hostname or '').endswith('.hudl.com')):
        raise ValueError('Unexpected source URL: '+url)
    url = urlunsplit(('https',parsed.netloc,parsed.path,parsed.query,parsed.fragment))
    path = unquote(parsed.path).lower()
    sports = ['basketball','football','soccer','volleyball','baseball','softball','lacrosse','hockey','wrestling']
    explicit = next((s for s in sports if re.search(r'\b'+s+r'\b',key)), '')
    sport = explicit or next((s for s in sports if s in path), '')
    source_type = 'profile' if '/profile/' in path else 'video' if '/video/' in path else 'team' if '/team/' in path else 'organization' if '/organization/' in path else 'resource'
    segments = parsed.path.strip('/').split('/')
    entity = ''
    for label in ['organization','profile']:
        if label in segments:
            i = segments.index(label)
            if len(segments)>i+2 and not segments[i+2].isdigit() and segments[i+2].lower() not in ['tickets','schedule','roster','videos','highlights','stats','scores','team','teams']:
                entity = unquote(segments[i+2]).replace('-',' ');break
    if re.search(r'\b(schedule|schedules|score|scores|result|results|standing|standings|tickets|live|stream|streaming)\b',key):
        category='basketball-schedules' if sport=='basketball' else 'fan-basketball'
    elif re.search(r'\b(scout|scouting|recruit|recruiting|recruitment)\b',key): category='scouting'
    elif re.search(r'\b(editor|editing|camera|filming|recording|compressor|video|videos|film|highlight|highlights|reels?)\b',key): category='basketball-video' if sport=='basketball' or keyword=='basketball editor' else 'sports-video'
    elif sport=='basketball' and re.search(r'\b(training|practice|drill|drills|workout|workouts|coach|coaching)\b',key): category='basketball-training'
    elif sport=='basketball' and (re.match(r'(what|how|types|definition|meaning)\b',key) or re.search(r'\b(shot|shots|foul|fouls|field goal|fg|dunk|layup|jumper|rebound|dribble|offense|defense|screen|pick and roll|free throw)\b',key)): category='basketball-skills'
    elif sport=='basketball': category='basketball-teams'
    else: category='fan-basketball'
    if source_type=='profile' and not re.search(r'\b(basketball|video|videos|highlights|camera|filming|scouting|recruiting)\b',key):
        category='basketball-teams' if sport=='basketball' else 'fan-basketball'
    # An export URL is provenance, never proof that an ambiguous query has one identity.
    ambiguous = bool(re.search(r'\b(weather|restaurants?|archangels|bangala|keezy|locati0n|official records|external events|privately owned|before:)\b',key))
    has_basketball = 'basketball' in key or bool(re.search(r'\b(hoops|hooper|dunk|layup|jump shots?|free throws?|shot tracer)\b',key))
    if has_basketball: priority=0 if category in ['basketball-video','basketball-skills','basketball-training'] else 1
    elif sport=='basketball' and not ambiguous: priority=2
    elif category in ['sports-video','scouting'] and not ambiguous: priority=3
    elif explicit or re.search(r'\b(high school|university|college|academy|sports|athletics|prep)\b',key):priority=4
    else:priority=5
    if ambiguous:priority=9
    return {'keyword':keyword,'display_keyword':keyword,'sport':sport,'source_type':source_type,'source_url':url,'entity':entity,'category':category,'priority':priority,'identity_unverified':True}

def select(csv_path):
    existing = [p for p in tracer.load_pages(ROOT) if p.get('releaseApproval',{}).get('batch_id') != BATCH]
    existing_keys = {normalized(p.get('keyword','')) for p in existing if p.get('keyword')}
    used_slugs = {p['slug'] for p in existing}
    with csv_path.open(encoding='utf-8-sig') as source:
        rows = list(csv.DictReader(source))
    seen = set(); candidates=[]; existing_rows=[]
    for ordinal,row in enumerate(rows):
        key=normalized(row['Keyword'])
        if key in seen:raise ValueError('Input must already be deduplicated: '+key)
        seen.add(key)
        if key in existing_keys:existing_rows.append(row);continue
        ctx=context(row)
        candidates.append({'row':row,'context':ctx,'source_ordinal':ordinal})
    candidates.sort(key=lambda x:(-1 if normalized(x['row']['Keyword']) in SEEDS else x['context']['priority'], -float(x['row']['Search Volume'] or 0), x['source_ordinal']))
    selected=[]
    for item in candidates[:TARGET]:
        key=item['row']['Keyword']; slug=slugify(key)
        if not slug:raise ValueError('Empty keyword slug')
        if slug in used_slugs:slug+='-'+hashlib.sha256(key.encode()).hexdigest()[:8]
        if slug in used_slugs:raise ValueError('Slug collision')
        used_slugs.add(slug);item['slug']=slug;selected.append(item)
    if len(selected)!=TARGET:raise ValueError('Fewer than 1000 new keywords')
    return rows,selected,candidates[TARGET:],existing_rows

def main():
    args=argparse.ArgumentParser();args.add_argument('--csv',type=Path,required=True);args.add_argument('--select-only',action='store_true');args=args.parse_args()
    rows,selected,pending,existing=select(args.csv)
    selection=ROOT/'content/shot-tracer/keyword-profiles'/f'{BATCH}-selection.json'
    selection.parent.mkdir(parents=True,exist_ok=True)
    selection.write_text(json.dumps(selected,ensure_ascii=False,indent=2)+'\n')
    if args.select_only:
        print(json.dumps({'selected':len(selected),'categories':Counter(x['context']['category'] for x in selected),'pending':len(pending),'existing':len(existing)},indent=2));return
    from hudl_editorial import make_profile
    overrides=json.loads((ROOT/'content/shot-tracer/keyword-profiles'/f'{BATCH}-reviewed-samples.json').read_text())
    by_keyword={normalized(p['keyword']):p for p in overrides}
    pages=[]
    for item in selected:
        row,ctx=item['row'],item['context']
        p=by_keyword.get(normalized(row['Keyword']))
        if p:p=json.loads(json.dumps(p));p['slug']=item['slug']
        else:p=make_profile(row,item['slug'],ctx['category'],ctx)
        p['status']='approved'
        p['demandEvidence']={'source':'User-provided Semrush Hudl US ranking export','file':args.csv.name,'file_sha256':hashlib.sha256(args.csv.read_bytes()).hexdigest(),'keyword':row['Keyword'],'searchVolume':row['Search Volume'],'keywordDifficulty':row['Keyword Difficulty'],'position':row['Position'],'positionType':row['Position Type'],'competitorUrl':row['URL'],'dataTimestamp':row['Timestamp'],'market':'US','note':'Exported estimates and dates preserved; not HoopCut traffic or a forecast.'}
        p['exampleEvidence']={'url':'/videos/basketball-shot-tracer-example','scope':'Shared HoopCut basketball demonstration, not footage of the named team or player.'}
        p['reviewedBy']='Site owner approved original shared Tracer template and requested publishing 1000 keyword pages on 2026-11-13.'
        p['releaseApproval']={'batch_id':BATCH,'user_instruction':'今天先上线1000个关键词页面','scope':'1000 new Hudl keyword pages using the reviewed original Tracer template, with required SEO integration'}
        pages.append(p)
    target=ROOT/'content/shot-tracer/batches'/BATCH/'pages.json';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(pages,ensure_ascii=False,indent=2)+'\n')
    taxonomy_file=ROOT/'content/shot-tracer/internal-link-taxonomy.json';taxonomy=json.loads(taxonomy_file.read_text())
    taxonomy['pages']={slug:mapping for slug,mapping in taxonomy['pages'].items() if not str(mapping.get('relatedGroup','')).startswith(BATCH+'-')}
    category_ids={c['id'] for c in taxonomy['categories']}
    used_categories={i['context']['category'] for i in selected}
    for id,(label,description) in CATEGORIES.items():
        if id in used_categories and id not in category_ids:taxonomy['categories'].append({'id':id,'label':label,'description':description})
    for item in selected:
        ctx=item['context'];key=normalized(item['row']['Keyword'])
        modifier=next((m for m in ['schedule','score','roster','field goal','foul','highlight','camera','recruit','training','drill'] if m in key),'general')
        topic = slugify(ctx['entity']) if ctx['category'] in ['basketball-teams','basketball-schedules','fan-basketball'] and ctx['entity'] else modifier
        taxonomy['pages'][item['slug']]={'category':ctx['category'],'relatedGroup':BATCH+'-'+ctx['category']+'-'+ctx['sport']+'-'+topic}
    taxonomy_file.write_text(json.dumps(taxonomy,ensure_ascii=False,indent=2)+'\n')
    # Existing published URLs are never overwritten to reach the requested count.
    loaded=tracer.load_pages(ROOT)
    manifest={'batchId':BATCH,'status':'approved_for_publication','sourceFile':args.csv.name,'sourceSha256':hashlib.sha256(args.csv.read_bytes()).hexdigest(),'sourceKeywords':len(rows),'newPages':len(pages),'existingKeywordMatches':len(existing),'remainingKeywords':len(pending),'selectionPolicy':'Previously reviewed four samples first, then basketball and video workflows in demand order; remaining keywords stay queued. No search-volume or KD threshold added.','previewSlugs':[p['slug'] for p in pages],'urls':[tracer.BASE+tracer.route(p) for p in pages],'categories':dict(Counter(i['context']['category'] for i in selected)),'approval':'User requested publication of 1000 pages in this chat on 2026-11-13.','unverified':'No new GSC traffic or indexing outcomes claimed.'}
    (ROOT/'content/shot-tracer/batch-manifests'/f'{BATCH}.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'batch':BATCH,'new_pages':len(pages),'total_tracer_records':len(loaded),'categories':manifest['categories'],'remaining':len(pending)},indent=2))

if __name__=='__main__':main()
