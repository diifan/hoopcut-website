#!/usr/bin/env python3
"""Select unused school keywords and build the owner-reviewed basketball workflow.

No publishing or network access. The caller supplies a specific release approval.
The source export identifies keyword provenance, not current school sporting facts.
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
from build_shot_tracer import load_pages

ROOT = Path(__file__).resolve().parents[1]
def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def eligible(keyword):
    if len(keyword) > 60:
        return False
    return bool(re.search(r'\b(school|academy|college|university|prep)\b', keyword, re.I)) and not re.search(
        r'\b(football|soccer|hockey|baseball|softball|volleyball|lacrosse|wrestling|tuition|jobs|calendar|login|powerschool|address|weather|salary|employment|application|admission|admissions|transcript|graduation|lunch|menu)\b', keyword, re.I)

def label(keyword):
    s = keyword.title()
    return re.sub(r'\b(Nba|Ncaa|Usa|Ucla|Usc|Mit|Nyu|Ucf|Uab|Ucsd|Uconn)\b', lambda m: m[0].upper(), s)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pool', type=Path, required=True)
    ap.add_argument('--csv', type=Path, required=True)
    ap.add_argument('--batch', required=True)
    ap.add_argument('--count', type=int, default=2000)
    ap.add_argument('--approval', required=True)
    args = ap.parse_args()
    target = ROOT / 'content/shot-tracer/batches' / args.batch / 'pages.json'
    if target.exists():
        raise SystemExit('Batch exists. Resume from its manifest; do not reselect.')
    with args.pool.open(encoding='utf-8-sig') as f:
        pool = {normalized(r['keyword']): r for r in csv.DictReader(f)}
    existing = load_pages(ROOT)
    keys = {normalized(p.get('keyword', '')) for p in existing}
    slugs = {p['slug'] for p in existing}
    with args.csv.open(encoding='utf-8-sig') as f:
        source = list(csv.DictReader(f))
    candidates = []
    for ordinal, row in enumerate(source):
        key = normalized(row['Keyword'])
        state = pool.get(key, {})
        permitted = state.get('status') == 'available' or state.get('batch_id') == 'hudl-20261117-samples'
        if key in keys or not permitted or not eligible(key):
            continue
        candidates.append((ordinal, row))
    samples = json.loads((ROOT / 'content/shot-tracer/editorial-templates/school-basketball-v2.json').read_text())
    approved_samples = {normalized(p['keyword']): p for p in samples}
    candidates.sort(key=lambda x: (normalized(x[1]['Keyword']) not in approved_samples,
                                   -float(x[1]['Search Volume'] or 0), x[0]))
    if len(candidates) < args.count:
        raise SystemExit(f'Only {len(candidates)} eligible unused school terms; requested {args.count}')
    taxonomy_file = ROOT / 'content/shot-tracer/internal-link-taxonomy.json'
    taxonomy = json.loads(taxonomy_file.read_text())
    pages, selection = [], []
    for i, (ordinal, row) in enumerate(candidates[:args.count]):
        key = normalized(row['Keyword']); name = label(row['Keyword']); slug = slugify(key)
        if slug in slugs:
            slug += '-' + hashlib.sha256(key.encode()).hexdigest()[:8]
        slugs.add(slug); ctx = context(row)
        # School-level basketball use is conditional: no claim of school affiliation,
        # an actual fixture, a named athlete in the demo, or non-basketball support.
        school_type = 'college' if re.search(r'\b(college|university)\b', key) else 'school'
        mode = 'practice' if re.search(r'\b(training|practice|academy|prep)\b', key) else 'game'
        if key in approved_samples:
            p = deepcopy(approved_samples[key])
        else:
            template = samples[1 if mode == 'practice' else 0]
            old = template['label']
            p = json.loads(json.dumps(template).replace(old, name))
            p['label'] = name
            p['title'] = f'{name} Basketball Shot Tracer | HoopCut'
            p['heading'] = f'{name} basketball highlights — add a shot tracer'
            p['sources'] = [{'title': f'{name} sports on Hudl', 'url': ctx['source_url']}]
            if school_type == 'college':
                p['sections'][0]['text'] = ('For a personal college basketball highlight, keep the build-up to the shot in view. '
                    'Start before the catch or final dribble and end after the ball reaches the hoop. '
                    'Add the tracer to make the flight visible while preserving the pace and context of the possession.')
            # A practical clip plan is selected by recording intent, not invented
            # team data. No example is represented as footage from this school.
            if mode == 'practice':
                p['sections'].insert(1, {'heading': f'A practice clip plan for {name} basketball',
                    'text': 'Before recording, frame the shooter and basket together. Leave space above the rim for the arc, record one complete attempt and keep the camera steady through the follow-through. In the editor, select that attempt and review the trail before export.',
                    'subsections': [{'heading': 'What to keep in the frame', 'text': 'Keep the ball visible at release and on its approach to the rim. If a wall, another player or the camera crop hides part of the flight, choose a clearer take.'}]})
            else:
                p['sections'].insert(1, {'heading': f'A game clip plan for {name} basketball',
                    'text': 'Find the possession in your recording and note its timestamp. Include the pass or last dribble, the release and the finish. Use that continuous section in the uploader, then watch the tracer at both ends of the shot before saving.',
                    'subsections': [{'heading': 'When to choose a different possession', 'text': 'A crowded lane, a sudden zoom or a camera pan can hide the ball. Preview the full shot and choose a clearer recording if the trail does not follow the visible flight.'}]})
        p.update(slug=slug, keyword=row['Keyword'], intent='hudl-query-'+slug, status='approved')
        p.pop('localReviewBatch', None)
        p['demandEvidence'] = {'source': 'User-provided Semrush Hudl US export', 'file': args.csv.name,
            'keyword': row['Keyword'], 'searchVolume': row['Search Volume'], 'keywordDifficulty': row['Keyword Difficulty'],
            'competitorUrl': row['URL'], 'dataTimestamp': row['Timestamp'], 'market': 'US',
            'note': 'Historical export estimate, not measured HoopCut demand or a traffic forecast.'}
        p['exampleEvidence'] = {'url': '/videos/basketball-shot-tracer-example', 'scope': 'Shared demo, not school-specific footage.'}
        p['reviewedBy'] = 'Owner approved school-basketball copy-v2 samples and authorized this 2000-page release on 2026-11-17.'
        p['releaseApproval'] = {'batch_id': args.batch, 'user_instruction': args.approval}
        taxonomy['pages'][slug] = {'category': 'fan-basketball', 'relatedGroup': args.batch+'-'+school_type+'-'+mode}
        selection.append({'keyword': row['Keyword'], 'slug': slug, 'source_ordinal': ordinal,
                          'source_url': row['URL'], 'mode': mode, 'school_type': school_type})
        pages.append(p)
    dump(target, pages); dump(taxonomy_file, taxonomy)
    dump(ROOT / 'content/shot-tracer/keyword-profiles' / (args.batch+'-selection.json'), selection)
    manifest = {'batchId': args.batch, 'status': 'approved_for_publication', 'newPages': len(pages),
        'sourceFile': args.csv.name, 'sourceSha256': hashlib.sha256(args.csv.read_bytes()).hexdigest(),
        'urls': ['https://hoopcut.ai/shot-tracer/'+p['slug'] for p in pages], 'previewSlugs': [p['slug'] for p in pages],
        'selectionPolicy': 'Unused school/academy/college terms; reviewed samples included; other sports and administrative queries left in pool.',
        'categories': dict(Counter(x['mode'] for x in selection)), 'approval': args.approval,
        'limitations': 'Shared editing product and school-use templates; no claim of unique school footage or guaranteed indexing/traffic.'}
    dump(ROOT / 'content/shot-tracer/batch-manifests' / (args.batch+'.json'), manifest)
    print(json.dumps({'batch': args.batch, 'pages': len(pages), 'modes': manifest['categories']}, indent=2))

if __name__ == '__main__':
    main()
