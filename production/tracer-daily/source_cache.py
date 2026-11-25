"""Incremental offline-selected Hudl cache refresh; never modifies batch artifacts."""
import csv
import importlib.util
import json
import os
import threading
import time
import random
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

ALLOWED = {'hudl.com', 'www.hudl.com', 'fan.hudl.com', 'support.hudl.com', 'ncsasports.org', 'www.ncsasports.org', 'xbotgo.com', 'www.xbotgo.com', 'sportsvisio.com', 'www.sportsvisio.com'}
ALLOWED.update(h for domain in ('homecourt.ai', 'shottracker.com', 'hoopsalytics.com',
    'noahbasketball.com', 'dribbleup.com', 'thehoopsgeek.com', 'hoopcoach.org', 'elitehoopsapp.com')
    for h in (domain, 'www.' + domain))
MAX_BODY = 1024 * 1024
_LOCAL = threading.local()


def _allowed(url):
    p = urlparse(url)
    return p.scheme == 'https' and p.hostname in ALLOWED and p.port in (None, 443) and not p.username and not p.password


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = []
        self.text = []
        self.in_title = False
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        if tag == 'title':
            self.in_title = True

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)
        if tag == 'title':
            self.in_title = False

    def handle_data(self, data):
        if not self.hidden:
            self.text.append(data)
            if self.in_title:
                self.title.append(data)


def _session(proxy):
    import requests
    if getattr(_LOCAL, 'proxy', None) != proxy or not hasattr(_LOCAL, 'session'):
        session = requests.Session()
        session.trust_env = False
        session.proxies = {'http': proxy, 'https': proxy}
        session.headers['User-Agent'] = 'HoopCutSourceReview/1.0'
        _LOCAL.session, _LOCAL.proxy = session, proxy
    return _LOCAL.session


def fetch_one(url, proxy='http://192.168.0.120:10808', now=None):
    """Retry transient failures up to six attempts; retain real HTTP outcomes."""
    checked = time.time() if now is None else now
    record = {'source_url': url, 'checked_at': checked, 'http': None, 'attempts': []}
    for attempt in range(6):
        if attempt:
            time.sleep(min(2 ** (attempt - 1), 8) + random.uniform(0, .5))
        try:
            current = url
            for redirects in range(6):
                if not _allowed(current):
                    raise ValueError('URL or redirect outside registered research HTTPS allowlist')
                with _session(proxy).get(current, timeout=(5, 15), stream=True, allow_redirects=False) as response:
                    status = response.status_code
                    if status in (301, 302, 303, 307, 308):
                        if redirects == 5:
                            raise ValueError('Redirect limit exceeded')
                        current = urljoin(current, response.headers.get('Location', ''))
                        continue
                    body = bytearray()
                    truncated = False
                    if status == 200:
                        for chunk in response.iter_content(chunk_size=16384):
                            remaining = MAX_BODY - len(body)
                            if len(chunk) > remaining:
                                body.extend(chunk[:remaining])
                                truncated = True
                                break
                            body.extend(chunk)
                            if len(body) == MAX_BODY:
                                truncated = True
                                break
                    record.update(http=status, final_url=current, body_bytes=len(body), body_truncated=truncated)
                    record['attempts'].append({'attempt': attempt + 1, 'http': status})
                    if status == 200:
                        parser = _Text()
                        parser.feed(body.decode(response.encoding or 'utf-8', errors='replace'))
                        record.update(title=' '.join(' '.join(parser.title).split()), text_excerpt=' '.join(' '.join(parser.text).split())[:30000])
                        record.pop('error', None)
                        return record
                    record['error'] = 'HTTP ' + str(status)
                    break
            if record['http'] not in (429,) and not (record['http'] and record['http'] >= 500):
                return record
        except Exception as exc:
            record.update(http=None, error=type(exc).__name__ + ': ' + str(exc)[:500])
            record['attempts'].append({'attempt': attempt + 1, 'error': record['error']})
            if isinstance(exc, ValueError):
                return record
    return record


def _engine():
    path = Path(__file__).with_name('content_engine.py')
    spec = importlib.util.spec_from_file_location('_tracer_cache_content', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def refresh_cache(pool_path, source_manifest_path, cache_path, occupied_keywords,
                  occupied_slugs, policy_root, proxy='http://192.168.0.120:10808',
                  max_workers=8, now=None, fetch=None):
    """Merge incremental results atomically; inject fetch(url,proxy,now) for tests."""
    started = time.monotonic()
    timestamp = time.time() if now is None else float(now)
    engine = _engine()
    manifest_path = Path(source_manifest_path)
    manifest = json.loads(manifest_path.read_text())
    engine._verified(pool_path, manifest.get('sha256'))
    if not manifest.get('sources'):
        raise ValueError('Missing original source exports')
    scripts = engine._scripts(policy_root)
    policy = engine._load(scripts / 'tracer_keyword_policy.py')
    slugify = engine._load(scripts / 'prepare_hudl_tracer_batch.py').slugify
    used = {str(k).strip().casefold() for k in occupied_keywords}
    counts = Counter()
    eligible = set()
    with Path(pool_path).open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            keyword = row.get('keyword', '').strip()
            if row.get('status') != 'available' or keyword.casefold() in used or slugify(keyword) in occupied_slugs:
                counts['unavailable_or_occupied'] += 1
            elif engine.EXCLUDE.search(keyword) or policy.rejection_reason(keyword):
                counts['excluded_intent'] += 1
            else:
                eligible.add(keyword.casefold())
    urls = set()
    for source in manifest['sources']:
        path = Path(source['local_path'])
        if not path.is_absolute():
            path = manifest_path.parent / path
        engine._verified(path, source.get('sha256'))
        with path.open(encoding='utf-8-sig', newline='') as stream:
            for row in csv.DictReader(stream):
                if row.get('Keyword', '').strip().casefold() not in eligible:
                    continue
                url = row.get('URL', '')
                if _allowed(url) and (urlparse(url).hostname.endswith('hudl.com') or engine.research_context(url, row.get('Keyword', ''))):
                    urls.add(url)
                else:
                    counts['excluded_url'] += 1
    path = Path(cache_path)
    cache = {r['source_url']: r for r in json.loads(path.read_text())} if path.exists() else {}
    pending = []
    for url in sorted(urls):
        old = cache.get(url)
        if old and old.get('http') == 200:
            counts['reused_success'] += 1
            continue
        ttl = 60 if old and (old.get('http') is None or old.get('http') == 429 or old.get('http', 0) >= 500) else 86400
        try:
            age = timestamp - float(old.get('checked_at', 0)) if old else ttl
        except (TypeError, ValueError):
            age = ttl
        if old and age < ttl:
            counts['cached_failure_waiting_ttl'] += 1
        else:
            pending.append(url)
    fetch = fetch or fetch_one

    def run(url):
        try:
            result = dict(fetch(url, proxy=proxy, now=timestamp))
        except Exception as exc:
            result = {'http': None, 'error': type(exc).__name__ + ': ' + str(exc)[:500]}
        result.update(source_url=url, checked_at=timestamp)
        return result

    def save():
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + '.' + str(os.getpid()) + '.tmp')
        temporary.write_text(json.dumps(list(cache.values()), ensure_ascii=False, indent=2) + '\n')
        os.replace(temporary, path)

    with ThreadPoolExecutor(max_workers=max(1, min(int(max_workers), 32))) as executor:
        futures = [executor.submit(run, url) for url in pending]
        for future in as_completed(futures):
            result = future.result()
            old = cache.get(result['source_url'], {})
            history = list(old.get('failure_history', []))
            if old and old.get('http') != 200:
                history.append({k: v for k, v in old.items() if k != 'failure_history'})
            for attempt in result.get('attempts', []):
                if attempt.get('http') != 200:
                    history.append(dict(attempt, checked_at=timestamp))
            if history:
                result['failure_history'] = history
            cache[result['source_url']] = result
            counts['fetched'] += 1
            counts['fetch_success' if result.get('http') == 200 else 'fetch_failed'] += 1
            if counts['fetched'] % 50 == 0:save()
    if pending:save()
    counts['elapsed_seconds'] = round(time.monotonic()-started, 3)
    counts['eligible_keywords'] = len(eligible)
    counts['eligible_urls'] = len(urls)
    counts['cache_entries'] = len(cache)
    return dict(counts)
