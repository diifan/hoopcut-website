#!/usr/bin/env python3
"""Build one local draft per distinct source keyword, preserving every CSV row.

Content profiles are authored inputs, not automatic keyword substitutions. Exact
duplicate ranking records share one keyword URL; synonyms do not get merged.
"""
import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from build_shot_tracer import ROOT, validate

FIT = {'direct', 'adjacent', 'ambiguous', 'unrelated'}


def normal(text):
    return ' '.join(text.strip().casefold().split())


def read_json(path):
    return json.loads(path.read_text())


def as_page(profile, batch_id):
    required = ('keyword', 'slug', 'title', 'description', 'heading', 'label',
                'intro', 'heroDetail', 'guideHeading', 'guideText', 'topic')
    if any(not isinstance(profile.get(k), str) or not profile[k].strip() for k in required):
        raise ValueError('Incomplete authored profile: ' + str(profile.get('keyword')))
    if profile.get('intentFit') not in FIT:
        raise ValueError('Missing intent fit: ' + profile['keyword'])
    if len(profile.get('tips', [])) != 2 or len(profile.get('faq', [])) != 2:
        raise ValueError('Two authored tips and questions required: ' + profile['keyword'])
    if any(not t.get('heading') or not t.get('text') for t in profile['tips']):
        raise ValueError('Incomplete authored tip: ' + profile['keyword'])
    if any(not isinstance(q, list) or len(q) != 2 or not all(q) for q in profile['faq']):
        raise ValueError('Incomplete authored FAQ: ' + profile['keyword'])
    p = {k: profile[k] for k in ('keyword', 'slug', 'title', 'description', 'heading',
                                'label', 'intro', 'heroDetail', 'topic', 'intentFit')}
    p.update({
        'status': 'draft', 'batchId': batch_id,
        'intent': 'keyword-query:' + normal(profile['keyword']),
        'note': profile.get('note', ''),
        'sources': profile.get('sources', []),
        'toolHeading': 'Add a shot tracer to your basketball clip',
        'workflowHeading': profile['label'] + ': from clip to shot trail',
        'sampleHeading': 'See the basketball shot tracer effect',
        'faqHeading': profile['label'] + ': questions and answers',
        'examplesHeading': 'Watch a basketball tracer example',
        'sections': [
            {'heading': profile['guideHeading'], 'text': profile['guideText'],
             'subsections': profile['tips']},
            {'heading': 'Prepare a clear basketball shot for the tracer',
             'text': 'Keep the basketball, shooting hand and target hoop in the frame. '
                     'Choose a short passage that starts before the release and ends after the ball reaches the basket. '
                     'A steady camera and a visible flight give you a clearer view of the added trail.',
             'steps': ['Use the original saved recording when possible, before social-media compression.',
                       'Select a passage of up to 30 seconds that includes the release and finish.',
                       'Choose the correct hoop when prompted, especially when several baskets are visible.']},
            {'heading': 'Review the basketball trail before sharing',
             'text': 'Play the preview through once at normal speed, then check the release, highest point and finish. '
                     'The effect should follow the visible ball without hiding the action. Keep an unedited copy '
                     'if you also want to review footwork, timing or the surrounding play.',
             'steps': ['Check any moment when another player or the backboard blocks the ball.',
                       'Export the free Firework effect once the preview is ready.',
                       'Save the edited clip separately from the original recording.']}
        ],
        'faq': profile['faq'] + [
            ['Which videos can I use?', 'Choose a saved MP4, MOV or WebM basketball video up to 512 MB. '
             'Select a segment of up to 30 seconds with the ball and hoop visible.'],
            ['What can I export on this page?', 'Firework is the free web export. You can preview the other '
             'effect styles and follow the HoopCut app link for more effects.'],
            ['Does the tracer measure shooting accuracy?', 'No. The tracer is a visual editing effect. '
             'It does not provide a shooting percentage, player rating or coaching assessment.']
        ],
        'workflowSteps': [
            {'title': 'Choose a basketball clip', 'text': 'Upload your saved recording and select a passage of up to 30 seconds.'},
            {'title': 'Preview the shot trail', 'text': 'Choose the target hoop when prompted and check the effect against the visible ball.'},
            {'title': 'Export your highlight', 'text': 'Download the free Firework export and keep the original recording.'}
        ],
        'examples': [['/videos/basketball-shot-tracer-example', 'Watch a HoopCut shot tracer example',
                      'A general basketball effect demonstration, separate from your own uploaded clip.']],
        'appCTA': {'heading': 'Give your next basketball shot a trail',
                   'text': 'Try Firework with your own clip here, then explore more basketball tracer effects in the HoopCut app.'},
        'demandEvidence': None, 'exampleEvidence': None, 'reviewedBy': None
    })
    return p


def prepare(source, profile_files, batch, root=ROOT):
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', batch):
        raise ValueError('Invalid batch name')
    raw = source.read_bytes()
    text = raw.decode('utf-8-sig')
    rows = list(csv.DictReader(text.splitlines(), dialect=csv.Sniffer().sniff(text[:4096])))
    grouped = defaultdict(list)
    for number, row in enumerate(rows, 2):
        if not normal(row.get('Keyword', '')):
            raise ValueError('Empty source keyword on row ' + str(number))
        grouped[normal(row['Keyword'])].append({'row': number, **row})

    destination = root/'content/shot-tracer/batches'/batch/'pages.json'
    previous_batch = {p['keyword']: p for p in read_json(destination)} if destination.exists() else {}
    existing = read_json(root/'content/shot-tracer/pages.json')
    for file in sorted((root/'content/shot-tracer/batches').glob('*/*.json')):
        if file.parent.name != batch:
            existing.extend(read_json(file))
    by_keyword = {}
    for p in existing:
        if p.get('keyword'):
            key = normal(p['keyword'])
            if key in by_keyword:
                raise ValueError('Existing keyword has multiple primary pages: ' + key)
            by_keyword[key] = p
    profiles = [p for file in profile_files for p in read_json(file)]
    authored = {normal(p['keyword']): p for p in profiles}
    if len(authored) != len(profiles):
        raise ValueError('Duplicate authored keyword')
    needed = set(grouped) - set(by_keyword)
    if set(authored) != needed:
        raise ValueError(f'Profile coverage mismatch: missing={sorted(needed-set(authored))}, extra={sorted(set(authored)-needed)}')

    batch_id = 'HC-TRACER-ONE-PER-KEYWORD-2026-11-12-01' if batch == 'homecourt-20261112-one-per-keyword' else 'HC-TRACER-' + batch.upper()
    pages = [as_page(authored[key], batch_id) for key in grouped if key in authored]
    validate(existing + pages)  # Validate all content before writing any output.
    all_by_keyword = {**by_keyword, **{normal(p['keyword']): p for p in pages}}
    source_info = {'file': source.name, 'sha256': hashlib.sha256(raw).hexdigest(), 'rows': len(rows),
                   'uniqueKeywords': len(grouped), 'duplicateRankingRows': len(rows)-len(grouped),
                   'market': 'US', 'provider': 'Semrush; estimates, not GSC',
                   'recordDates': sorted({r['Timestamp'] for r in rows if r.get('Timestamp')})}
    decisions = []
    for keyword, records in grouped.items():
        p = all_by_keyword[keyword]
        decision = {'keyword': keyword, 'action': 'create', 'targetPath': '/shot-tracer/' + p['slug'],
                    'intentFit': p.get('intentFit', 'adjacent'), 'retained': keyword in by_keyword,
                    'reason': '一词一页；仅完全相同关键词的重复排名记录共用该地址。同义词各有独立页面。',
                    'records': records}
        if decision['intentFit'] in ('ambiguous', 'unrelated'):
            decision['reason'] += '搜索意图与 Tracer 的匹配需审阅；页面已生成，不虚构功能或关联。'
        decisions.append(decision)
        if keyword in authored:
            p['targetKeywords'] = [keyword]
            p['demandEvidence'] = {'source': 'User-provided Semrush Organic Positions CSV',
                                   'file': source.name, 'sourceSha256': source_info['sha256'], 'market': 'US',
                                   'keyword': keyword, 'records': records,
                                   'note': 'Original estimates and dates retained. No traffic result or growth forecast inferred.'}
    paths = [d['targetPath'] for d in decisions]
    if len(paths) != len(set(paths)):
        raise ValueError('Two different keywords share a route')
    # Re-running an approved import must neither unpublish it nor silently change
    # reviewed copy. Content changes need a fresh review, with a new batch name.
    release_fields = {'status', 'reviewedBy', 'exampleEvidence', 'releaseApproval'}
    for p in pages:
        old = previous_batch.get(p['keyword'])
        if old and old['status'] == 'approved':
            if {k:v for k,v in old.items() if k not in release_fields} != {k:v for k,v in p.items() if k not in release_fields}:
                raise ValueError('Approved page changed; prepare a new review batch: ' + p['keyword'])
            for key in release_fields:
                if key in old:p[key] = old[key]
    validate(existing + pages)
    manifest = {'name': batch, 'batchId': batch_id, 'strategy': 'one-keyword-one-page',
                'source': source_info, 'previewSlugs': [all_by_keyword[k]['slug'] for k in grouped],
                'newSlugs': [p['slug'] for p in pages],
                'reusedSlugs': [all_by_keyword[k]['slug'] for k in grouped if k in by_keyword],
                'decisionCounts': dict(Counter(d['action'] for d in decisions)),
                'intentFitCounts': dict(Counter(d['intentFit'] for d in decisions)),
                'keywords': decisions}
    outputs = {destination: pages,
               root/'content/shot-tracer/batch-manifests'/f'{batch}.json': manifest,
               root/'content/shot-tracer/keyword-profiles'/f'{batch}.json': profiles}
    for file, value in outputs.items():
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', type=Path, required=True)
    parser.add_argument('--profiles', type=Path, nargs='+', required=True)
    parser.add_argument('--batch', required=True)
    args = parser.parse_args()
    result = prepare(args.csv, args.profiles, args.batch)
    print(json.dumps({'rows': result['source']['rows'], 'uniqueKeywords': result['source']['uniqueKeywords'],
                      'pages': len(result['previewSlugs']), 'new': len(result['newSlugs']),
                      'retained': len(result['reusedSlugs']), 'intentFit': result['intentFitCounts']}))
