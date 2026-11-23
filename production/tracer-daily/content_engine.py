"""Offline, evidence-backed selection and independent Tracer shard assembly.

Does not change keyword state, build the site, attach a domain or publish.
"""
import csv
import hashlib
import importlib.util
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

EXCLUDE = re.compile(r'\b(weather|obituar\w*|funeral|death|dead|murder|arrest|jail|prison|porn|nude|sex|restaurant\w*|pizza|barber\w*|salon|real estate|realtor|auction\w*|financial|bank|loan|insurance|dentist|dental|hospital|clinic|veterinar\w*|church|bible|sermon|prayer|meaning|pronounce|recipe|menu|lyrics|movie|novel|book|wedding|divorce|wife|husband|net worth|salary|jobs|employment|tuition|admission\w*|calendar|lunch|powerschool|login|log in|tickets|scores?|live|stream\w*|rankings?|roster|vs|football|soccer|baseball|softball|hockey|volleyball|lacrosse|wrestling|rugby|cricket|golf|swimming|gymnastics|cheerleading|tennis)\b', re.I)


RESEARCH_HOSTS = {'ncsasports.org', 'www.ncsasports.org', 'xbotgo.com', 'www.xbotgo.com', 'sportsvisio.com', 'www.sportsvisio.com'}
def research_context(url, keyword):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in RESEARCH_HOSTS:
        return None
    route = parsed.path.lower()
    # New exports contain many other sports: require an explicit basketball context.
    if 'basketball' not in route and 'basketball' not in keyword.casefold():
        return None
    if parsed.hostname in {'ncsasports.org', 'www.ncsasports.org'}:
        return 'school-sports-source' if '/athletic-scholarships/' in route or '/recruiting/' in route else 'basketball-recruiting-source'
    return 'basketball-video-workflow'


def _load(path):
    path = Path(path).resolve()
    spec = importlib.util.spec_from_file_location('_tracer_' + hashlib.sha256(str(path).encode()).hexdigest()[:16], path)
    module = importlib.util.module_from_spec(spec)
    old_path = sys.path[:]
    try:
        sys.path.insert(0, str(path.parent))
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
    return module


def _scripts(root):
    root = Path(root)
    return root / 'scripts' if (root / 'scripts').is_dir() else root


def _verified(path, expected):
    path = Path(path)
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if not expected or actual != expected:
        raise ValueError('Source SHA256 mismatch or missing expected hash: ' + str(path))
    return actual


def select_candidates(pool_path, source_manifest_path, cache_path,
                      occupied_keywords: set, occupied_slugs: set, policy_root: Path):
    """Return all eligible rows and explicit classification counts; no network.

    Every pool row is classified. Missing/failed evidence remains unresolved.
    All original export hashes and the pool hash are mandatory and fail closed.
    """
    manifest_path = Path(source_manifest_path)
    manifest = json.loads(manifest_path.read_text())
    _verified(pool_path, manifest.get('sha256'))
    sources = {}
    if not manifest.get('sources'):
        raise ValueError('Source manifest has no original exports')
    for source in manifest['sources']:
        path = Path(source['local_path'])
        if not path.is_absolute():
            path = manifest_path.parent / path
        sha = _verified(path, source.get('sha256'))
        with path.open(encoding='utf-8-sig', newline='') as stream:
            for row in csv.DictReader(stream):
                key = row.get('Keyword', '').strip().casefold()
                if key:
                    sources.setdefault(key, []).append((row, str(path), sha))
    probes_data = json.loads(Path(cache_path).read_text())
    probes = {row['source_url']: row for row in probes_data}
    scripts = _scripts(policy_root)
    policy = _load(scripts / 'tracer_keyword_policy.py')
    slugify = _load(scripts / 'prepare_hudl_tracer_batch.py').slugify
    used = {str(k).strip().casefold() for k in occupied_keywords}
    slugs = set(occupied_slugs)
    counts = Counter()
    eligible = []
    with Path(pool_path).open(encoding='utf-8-sig', newline='') as stream:
        for pool in csv.DictReader(stream):
            counts['reviewed_candidates'] += 1
            keyword = pool.get('keyword', '').strip()
            key, slug = keyword.casefold(), slugify(keyword)
            if pool.get('status') != 'available':
                counts['unavailable'] += 1
                continue
            if key in used or slug in slugs or not slug:
                counts['occupied_or_duplicate'] += 1
                continue
            if EXCLUDE.search(keyword) or policy.rejection_reason(keyword):
                counts['explicit_unrelated_intent'] += 1
                continue
            evidence = sources.get(key, [])
            if not evidence:
                counts['unresolved_missing_export'] += 1
                continue
            selected = None
            failure = 'unresolved_context_or_alignment'
            for original, path, sha in evidence:
                url = original.get('URL', '')
                probe = probes.get(url, {})
                if probe.get('http') != 200:
                    failure = 'unresolved_source_fetch'
                    continue
                title = probe.get('title', '')
                parsed = urlparse(url)
                context = research_context(url, keyword)
                identity = title + (' ' + re.sub(r'[-_/]', ' ', parsed.path) if context else '')
                if not policy.identity_aligned(keyword, identity):
                    continue
                if parsed.hostname not in ('hudl.com', 'www.hudl.com', 'support.hudl.com', 'fan.hudl.com') and not context:
                    continue
                route = parsed.path
                context = context or ('school-sports-source' if '/organization/' in route or '/team/' in route
                           else 'sports-video-source' if '/video/' in route
                           else 'sports-profile-source' if '/profile/' in route
                           else 'editing-workflow' if 'hudl' in key and re.search(r'video|edit|highlight|clip|download|upload|library|camera|telestrat', key)
                           else None)
                if not context:
                    continue
                try:
                    volume = int(float(original.get('Search Volume', '0') or 0))
                except ValueError:
                    volume = 0
                selected = {'keyword': keyword, 'slug': slug, 'source_url': url, 'context_type': context,
                            'cached_title': title, 'clip_type': 'saved basketball clip',
                            'demandEvidence': dict(original), 'volume': volume,
                            'sourceEvidence': {'local_path': path, 'sha256': sha, 'http': 200,
                                               'checked_at': probe.get('checked_at')},
                            'priority': 0 if context == 'school-sports-source' else 1 if context == 'editing-workflow' else 2}
                break
            if selected is None:
                counts[failure] += 1
                continue
            eligible.append(selected)
            used.add(key)
            slugs.add(slug)
            counts['eligible'] += 1
    eligible.sort(key=lambda row: (row['priority'], -row['volume'], row['keyword'].casefold()))
    return eligible, dict(counts)


def build_shard(rows, worktree, batch_id, output_path):
    """Assemble an independent manifest for prebuild, never domain publication."""
    root = Path(worktree)
    workflow = _load(root / 'scripts/prepare_hudl_workflow_batch.py')
    slugify = _load(root / 'scripts/prepare_hudl_tracer_batch.py').slugify
    sample = json.loads((root / 'content/shot-tracer/editorial-templates/school-basketball-v2.json').read_text())[0]
    pages, seen = [], set()
    for row in rows:
        keyword = row['keyword']
        slug = slugify(keyword)
        if not slug or slug in seen:
            raise ValueError('Duplicate or invalid shard slug: ' + slug)
        seen.add(slug)
        if not row.get('demandEvidence') or not row.get('source_url'):
            raise ValueError('Missing selection evidence: ' + keyword)
        page = workflow.workflow_page(sample, keyword, 'highlights')
        page.update(slug=slug, keyword=keyword, status='approved', localReviewBatch=batch_id,
                    intent='basketball-clip-' + slug, label=keyword,
                    title=keyword + ' | Basketball Shot Tracer | HoopCut',
                    heading=keyword + ': a basketball shot-trail editing workflow',
                    description=keyword + ': Prepare your own authorized basketball video for a visible shot-trail effect. Upload a saved file, preview the trail and export with HoopCut.')
        page['intro'] = ('If your search for “' + keyword + '” is part of preparing your own basketball footage, start with a saved recording you own or have permission to edit. Select one continuous shot, preview a visible trail and keep the original alongside the exported copy. This page does not supply footage or claim any affiliation.')
        page['sections'][0].update(text=page['intro'], heading='Prepare your own basketball clip', subsections=[{'heading': 'Bring a local video file', 'text': 'Choose a saved recording you own or may edit. A search result or share URL is not a video file and does not grant access to the recording.'}])
        page['sources'] = [{'title': 'Keyword research source; not a HoopCut affiliation or supplied recording', 'url': row['source_url']}]
        page['note'] = 'Independent visual editing workflow. No supplied player footage, team endorsement, account connection or statistical analysis.'
        page['demandEvidence'] = row['demandEvidence']
        page['selectionEvidence'] = row
        page['reviewFlags'] = []
        page['reviewedBy'] = 'Standing daily batch publication authorization; automated evidence review, not individual human keyword approval.'
        page['releaseApproval'] = {'publication_authorized': True, 'batch_id': batch_id, 'scheduled_time': '12:30 Asia/Shanghai', 'source': 'User standing daily batch publication authorization; not individual keyword approval or immediate domain publication. Unaliased prebuild now; domain publication only at the authorized scheduled release.'}
        examples = page.get('examples', [])
        if not examples:
            raise ValueError('Template has no real example: ' + keyword)
        first = examples[0]
        url = first[0] if isinstance(first, list) else first.get('url')
        if not url:
            raise ValueError('First template example has no URL: ' + keyword)
        page['exampleEvidence'] = {'url': url, 'scope': 'Shared HoopCut example; not associated with the keyword subject.'}
        pages.append(page)
    output = Path(output_path)
    result = {'pages': pages, 'count': len(pages), 'pid': os.getpid(), 'output_path': str(output.resolve())}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + '.' + str(os.getpid()) + '.tmp')
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    os.replace(temporary, output)
    return result
