#!/usr/bin/env python3
"""Build an explicitly approved batch from unused, traceable Hudl export terms.

School aliases use the reviewed basketball clip workflow. Hudl editing queries
get file-handoff instructions; no URL importer, team affiliation or footage is
invented. This script does not publish or change keyword-pool state.
"""
import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path

from prepare_hudl_tracer_batch import normalized, slugify, context
from prepare_school_tracer_batch import label, saved_hudl_copy, dump
from build_shot_tracer import load_pages

ROOT = Path(__file__).resolve().parents[1]
GUIDE = 'https://www.hudl.com/support/athletes-guide-to-hudl/guides/highlights'
DOWNLOAD = 'https://support.hudl.com/s/article/download-highlights?language=en_US&topic=Highlights_for_Athletes'
LIBRARY = 'https://support.hudl.com/s/article/download-video-new-hudl?language=en_US'
EXCLUDE = re.compile(r'\b(football|soccer|hockey|baseball|softball|volleyball|lacrosse|wrestling|rugby|cricket|golf|weather|login|log in|jobs|staff|logo|before|restaurants?|tuition|calendar|powerschool|address|salary|employment|admissions?|transcript|graduation|lunch|menu|schedule|scores?|tickets|live|stream|rankings?|vs|roster|porn)\b')

def category(row):
    k = normalized(row['Keyword']); ctx = context(row)
    if re.search(r'\b(events?|financial|legal|distress|internal|external|disruption|fiscal|crisis|weakness|photos|news|official website|meaning|contact|leaders|promoted|superintendent|characterstrong|sel|programs|church|correctional|hospital|clinic|veterinary|hotel|holiday inn|homes|sale|little league|where to watch|rest area|what day|gymnastics|tumbling|cheer|dental|humane society|prayer|fishing rods|gottschee|seasongreen|takitaki)\b|^8th 7th$', k):
        return None
    if len(k) > 65 or not re.search(r'[a-z]', k) or EXCLUDE.search(k) or re.search(r'https?\b|www\b|\.com\b|fanhudl|hudl fan|fan hudl|kcmc|carter meadows|bryson kennedy|joxpreps|league central|conference', k):
        return None
    if 'hudl' in k and re.search(r'highlight|download|upload|video|clips?|library', k):
        if re.search(r'delete|sportscode|app download|download hudl app|production truck', k) or k in ('download hudl', 'hudl downloader'):
            return None
        return 'download' if re.search(r'download', k) else 'upload' if 'upload' in k else 'library' if 'library' in k else 'highlights'
    # A competitor ranking URL alone is not proof that the query is a school.
    # These unrelated intents were found during the batch's source review.
    if re.search(r'\b(relationship|nude|funeral|obituaries|jail|nazi|wine|company|llc|services|textbook|classifieds|medical|staffing|bleach|hours|portal|scoreboard|tv|broadcast|smugmug|competitive dance|ice rink|ice arena|junior flyers|cross country|wilderness|homeowners|watch|today|free sms|little league|library)\b|academy sports|27 simpson|8 mateo|shawn hornbeck|levi sanders|beth paphato|kinta sakata|heather birkmire|allen mizdrak|alexis landschoot|shitta sillah|lacie nemchick|analy cruz|lfny snl|youth home|trilogy at vistancia|mississinewa lake|parview at|nienhuis park|little squalicum|baboquivari|miesville mudhens|lohud sports|wmfd sports|big board friday|name the organization|^sep 11$|^oct |sports complex|^spc ', k):
        return None
    school_source = ctx['source_type'] in ('organization', 'team') and re.search(r'school|scho\b|academy|college|univer|prep|\bhigh\b|middl|junior|community|\bcc\b', ctx['entity'], re.I)
    school_query = ctx['source_type'] != 'profile' and re.search(r'\b(hs|high|middle|jhs|junior|isd|secondary)\b', k)
    if school_source or school_query:
        return 'school-alias'
    return None

def workflow_page(template, keyword, mode):
    p = deepcopy(template); name = label(keyword).replace('Hudl', 'Hudl')
    p['label'] = name
    p['title'] = f'{name}: Tracer Workflow | HoopCut'
    p['heading'] = f'{name} — prepare a basketball clip for a shot tracer'
    p['description'] = f'{name}: save your basketball video, preview a shot tracer and export the edited clip with HoopCut. Local video file required.'
    first = {
        'download': ('Save the basketball video before adding a tracer',
            'Want a shot trail on a basketball clip you found in Hudl? First save a video file using the download options available to your account. Then upload that file here to trace the shot. A Hudl share link alone is not a video file.',
            'Start with the official download route',
            'Hudl documents separate routes for highlights and team-library video. Check the relevant help page below and the options in your own account. If you cannot export the recording, ask the coach or owner for a copy you may edit; this uploader cannot unlock or download it.'),
        'upload': ('Prepare the basketball edit before your Hudl upload',
            'Preparing a basketball video for Hudl? You can add a shot tracer to your saved clip first. Upload the local recording here, preview the ball trail and export a separate edited copy; then use the upload options available in your Hudl account.',
            'Keep the original and edited files separate',
            'Name the traced version clearly so it is not confused with the original game recording. HoopCut does not upload to Hudl or connect to your team library. Availability of a Hudl upload route depends on your account and team permissions.'),
        'library': ('Choose one basketball possession from your library',
            'Your Hudl library can be the starting point for a basketball highlight. Obtain a saved copy of a recording you may edit, choose one visible shot and use the Tracer below to make its flight easier to follow.',
            'Bring a saved file, not your account credentials',
            'Use the video download options available in Hudl or ask your coach for an export. HoopCut has no access to your Hudl library, account or private team recordings. The uploader works with the video file you select on your device.'),
        'highlights': ('Give a basketball highlight a visible ball trail',
            'Making basketball highlights on Hudl? Choose a clear shot from your own recording, add a tracer here and keep the edited clip for your highlight workflow. The ball trail draws attention to the flight while the pass, footwork and finish remain visible.',
            'Build the reel in Hudl; trace a saved shot here',
            'Hudl provides highlight creation and sharing tools. This page adds a separate basketball effect to a local video file; it does not edit a Hudl reel directly. Keep the original recording and use the saved traced version wherever your editing workflow accepts it.')
    }[mode]
    p['intro'] = first[1]
    p['heroDetail'] = 'Upload a saved basketball video, select up to 30 seconds and mark the hoop. Preview the shot trail before exporting. This is an independent HoopCut tool, not a Hudl integration.'
    p['toolHeading'] = 'Add a shot tracer to your saved basketball clip'
    p['workflowHeading'] = 'From saved basketball recording to traced highlight'
    p['sampleHeading'] = 'Preview the basketball shot tracer effect'
    p['faqHeading'] = f'{name}: file and tracer questions'
    p['examplesHeading'] = 'See a shared HoopCut basketball example'
    p['sections'] = [
        {'heading': first[0], 'text': first[1], 'subsections': [{'heading': first[2], 'text': first[3]}]},
        {'heading': 'Choose the part of the basketball clip worth tracing',
         'text': 'Keep one continuous attempt with the release, ball flight and rim visible. For a catch-and-shoot highlight, start before the pass arrives. For a pull-up, preserve the final dribble. End after the ball reaches the basket rather than cutting away during the flight.',
         'subsections': [{'heading': 'Avoid tracing across a montage cut', 'text': 'A cut, sudden zoom or blocked ball can make the trail harder to review. Work on one clear shot before combining it with other plays in your usual editor.'}]},
        {'heading': 'Preview and export the traced basketball shot',
         'text': 'Select your saved file in the uploader, choose up to 30 seconds and mark the hoop. Review the release and arrival at the rim. When the preview looks right, export the Firework effect free and keep the edited copy alongside the source.',
         'subsections': [{'heading': 'Keep the effect separate from performance evidence', 'text': 'A tracer is a visual effect, not a shooting percentage, recruiting evaluation or measured ball trajectory. Preserve the original recording if a coach needs to review the unedited possession.'}]}
    ]
    p['faq'] = [
        ['Can I paste a Hudl URL into HoopCut?', 'No. Select a video file saved on your device. HoopCut does not import Hudl URLs or access your account.'],
        ['What if I cannot download the original clip?', 'Use the official Hudl help links and check the permissions available to your account. Ask the recording owner or coach for a copy you may edit. A share or embed link does not grant file access.'],
        ['Is downloading from Hudl always free?', 'Do not assume so. Download availability and any cost depend on the Hudl product, account and video. The free Firework export offered here applies to the HoopCut effect, not Hudl downloads.'],
        ['Will this tool upload the finished video to Hudl?', 'No. Save the traced file and manage any subsequent upload through your own authorized account.'],
        ['Is the demonstration my team video?', 'No. It is a shared HoopCut example. Upload your own basketball clip to preview the effect on your footage.']
    ]
    p['workflowSteps'] = [
        {'title': 'Prepare a saved basketball file', 'text': 'Choose a recording you own or have permission to edit; obtain the file before opening the uploader.'},
        {'title': 'Select the shot and mark the hoop', 'text': 'Choose up to 30 seconds and preview the trail from release to basket.'},
        {'title': 'Export the edited copy', 'text': 'Save the Firework effect free and keep your original recording for reference.'}
    ]
    p['sources'] = [{'title': 'Hudl official highlight creation and sharing guide', 'url': GUIDE}, {'title': 'Hudl official highlight download help', 'url': DOWNLOAD}, {'title': 'Hudl official team-library download help', 'url': LIBRARY}]
    p['examples'] = [['/videos/basketball-shot-tracer-example', 'Watch a HoopCut basketball tracer example', 'A shared demonstration of the effect, not footage from your Hudl account.']]
    p['note'] = 'HoopCut is independent of Hudl. Local video file required; no Hudl account connection or URL downloader.'
    p['topic'] = 'basketball-video'; p['editorialIntent'] = 'workflow'
    return p

def main():
    a = argparse.ArgumentParser(); a.add_argument('--pool', type=Path, required=True); a.add_argument('--csv', type=Path, required=True); a.add_argument('--batch', required=True); a.add_argument('--count', type=int, default=2000); a.add_argument('--approval', required=True); args = a.parse_args()
    target = ROOT / 'content/shot-tracer/batches' / args.batch / 'pages.json'
    if target.exists(): raise SystemExit('Existing batch: resume it instead of selecting again.')
    pool = {normalized(r['keyword']): r for r in csv.DictReader(args.pool.open(encoding='utf-8-sig'))}
    existing = load_pages(ROOT); keys = {normalized(p.get('keyword', '')) for p in existing}; slugs = {p['slug'] for p in existing}
    candidates = []
    for ordinal, row in enumerate(csv.DictReader(args.csv.open(encoding='utf-8-sig'))):
        key = normalized(row['Keyword']); mode = category(row)
        if key not in keys and pool.get(key, {}).get('status') == 'available' and mode:
            candidates.append((mode, ordinal, row))
    candidates.sort(key=lambda x: (x[0] == 'school-alias', not bool(re.search(r'basketball| hudl$', normalized(x[2]['Keyword']))), -float(x[2]['Search Volume'] or 0), x[1]))
    if len(candidates) < args.count: raise SystemExit(f'Only {len(candidates)} unused relevant candidates; no padding.')
    samples = json.loads((ROOT / 'content/shot-tracer/editorial-templates/school-basketball-v2.json').read_text())
    taxonomy_file = ROOT / 'content/shot-tracer/internal-link-taxonomy.json'; taxonomy = json.loads(taxonomy_file.read_text())
    pages = []; selected = []
    for mode, ordinal, row in candidates[:args.count]:
        key = normalized(row['Keyword']); name = label(row['Keyword']); ctx = context(row); slug = slugify(key)
        if slug in slugs: slug += '-' + hashlib.sha256(key.encode()).hexdigest()[:8]
        slugs.add(slug); keys.add(key)
        if mode == 'school-alias':
            p = json.loads(json.dumps(samples[0]).replace(samples[0]['label'], name))
            p['label'] = name; p['title'] = f'{name} Basketball Shot Tracer | HoopCut'; p['heading'] = f'{name} basketball highlights — add a shot tracer'
            p['sources'] = [{'title': 'Hudl sports listing from the keyword source', 'url': ctx['source_url']}]
        else:
            p = workflow_page(samples[0], row['Keyword'], mode)
        p.update(slug=slug, keyword=row['Keyword'], intent='hudl-query-'+slug, status='approved')
        if mode == 'school-alias': p = saved_hudl_copy(p)
        p = json.loads(re.sub(r'\b(basketball) basketball\b', r'\1', json.dumps(p), flags=re.I))
        p.pop('localReviewBatch', None)
        p['demandEvidence'] = {'source': 'User-provided Semrush Hudl US export', 'file': row.get('_SourceFile') or args.csv.name, 'keyword': row['Keyword'], 'searchVolume': row['Search Volume'], 'keywordDifficulty': row['Keyword Difficulty'], 'competitorUrl': row['URL'], 'dataTimestamp': row['Timestamp'], 'market': 'US', 'note': 'Historical export estimate, not measured HoopCut demand or a traffic forecast.'}
        p['exampleEvidence'] = {'url': '/videos/basketball-shot-tracer-example', 'scope': 'Shared basketball demonstration, not footage of the named school or a Hudl account.'}
        p['reviewedBy'] = 'Owner approved shared Tracer workflow and explicitly authorized another 2000 pages on 2026-11-18; automated validation recorded separately.'
        p['releaseApproval'] = {'batch_id': args.batch, 'publication_authorized': True, 'user_instruction': args.approval}
        cat = 'fan-basketball' if mode == 'school-alias' else 'basketball-video'
        taxonomy['pages'][slug] = {'category': cat, 'relatedGroup': args.batch+'-'+mode}
        pages.append(p); selected.append({'keyword': row['Keyword'], 'slug': slug, 'mode': mode, 'source_ordinal': ordinal, 'source_url': row['URL']})
    dump(target, pages); dump(taxonomy_file, taxonomy)
    dump(ROOT / 'content/shot-tracer/keyword-profiles' / (args.batch+'-selection.json'), selected)
    manifest = {'batchId': args.batch, 'status': 'approved_for_publication', 'publicationAuthorized': True, 'newPages': len(pages), 'requestedPages': args.count, 'sourceFile': args.csv.name, 'sourceSha256': hashlib.sha256(args.csv.read_bytes()).hexdigest(), 'urls': ['https://hoopcut.ai/shot-tracer/'+p['slug'] for p in pages], 'previewSlugs': [p['slug'] for p in pages], 'categories': dict(Counter(s['mode'] for s in selected)), 'approval': args.approval, 'selectionPolicy': 'Unused pool terms only; Hudl basketball file workflows first, then school aliases with a school source. Explicit other-sport, administrative, account and malformed terms remain unselected.', 'limitations': 'Shared product and reviewed templates; school identities and footage are not independently verified. No indexing or traffic guarantee.'}
    dump(ROOT / 'content/shot-tracer/batch-manifests' / (args.batch+'.json'), manifest)
    print(json.dumps({'batch': args.batch, 'pages': len(pages), 'categories': manifest['categories'], 'eligibleUnused': len(candidates)}, indent=2))

if __name__ == '__main__': main()
