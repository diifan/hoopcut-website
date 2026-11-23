"""Offline incremental-cache regressions; HTTP is always a test double."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
HERE = Path(__file__).parent

def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

cache = load('source_cache')
engine = load('content_engine')

class CacheRefresh(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pool = self.root / 'pool.csv'
        self.export = self.root / 'export.csv'
        self.manifest = self.root / 'sources.json'
        self.cache = self.root / 'cache.json'
        self.cache.write_text('[]')
        self.scripts = self.root / 'scripts'; self.scripts.mkdir()
        # Minimal policy interface isolates evidence/cache behavior from site policy changes.
        (self.scripts / 'tracer_keyword_policy.py').write_text("def rejection_reason(keyword):\n return 'other intent' if 'obituary' in keyword else None\ndef identity_aligned(keyword,title):\n return keyword.casefold() in title.casefold()\n")
        (self.scripts / 'prepare_hudl_tracer_batch.py').write_text("import re\ndef slugify(keyword):\n return re.sub(r'[^a-z0-9]+','-',keyword.lower()).strip('-')\n")
        self.url = 'https://www.hudl.com/team/123/pine-ridge'
        self.fixture([('Pine Ridge', self.url)])
        self.fetch = Mock(return_value={'http':200, 'title':'Pine Ridge High School - Hudl'})
        self.network_guard = patch.object(cache, '_session', side_effect=AssertionError('Real HTTP forbidden'))
        self.network_guard.start(); self.addCleanup(self.network_guard.stop)

    def fixture(self, rows):
        with self.pool.open('w', newline='') as f:
            writer=csv.writer(f);writer.writerow(['keyword','status']);writer.writerows((k,'available') for k,u in rows)
        with self.export.open('w', newline='') as f:
            writer=csv.writer(f);writer.writerow(['Keyword','URL','Search Volume']);writer.writerows((k,u,100) for k,u in rows)
        digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        self.manifest.write_text(json.dumps({'sha256':digest(self.pool),'sources':[{'local_path':str(self.export),'sha256':digest(self.export)}]}))

    def refresh(self, **kwargs):
        params=dict(now=1000000, max_workers=3, fetch=self.fetch)
        params.update(kwargs)
        return cache.refresh_cache(self.pool,self.manifest,self.cache,params.pop('occupied_keywords',set()),params.pop('occupied_slugs',set()),self.root,**params)

    def select(self):
        return engine.select_candidates(self.pool,self.manifest,self.cache,set(),set(),self.root)

    def test_missing_evidence_becomes_eligible_after_incremental_refresh(self):
        before,counts=self.select()
        self.assertEqual(before,[])
        self.assertEqual(counts['unresolved_source_fetch'],1)
        result=self.refresh()
        self.fetch.assert_called_once_with(self.url,proxy='http://192.168.0.120:10808',now=1000000.0)
        self.assertEqual(result['fetch_success'],1)
        after,counts=self.select()
        self.assertEqual([r['keyword'] for r in after],['Pine Ridge'])
        self.assertEqual(after[0]['context_type'],'school-sports-source')
        self.assertEqual(counts['eligible'],1)

    def test_new_registered_sources_are_fetched_and_selected(self):
        for host in ['www.ncsasports.org', 'xbotgo.com', 'www.sportsvisio.com']:
            with self.subTest(host=host):
                url='https://'+host+'/basketball/pine-ridge'
                self.fixture([('Pine Ridge basketball',url)])
                self.cache.write_text('[]')
                self.fetch.return_value={'http':200,'title':'Pine Ridge basketball'}
                result=self.refresh()
                self.assertEqual(result['fetch_success'],1)
                self.assertEqual(len(self.select()[0]),1)

    def test_new_sources_do_not_accept_arbitrary_domains_or_non_basketball_context(self):
        self.fixture([('Pine Ridge','https://www.ncsasports.org/baseball/pine-ridge'),('Pine Ridge basketball','https://example.com/basketball')])
        result=self.refresh()
        self.fetch.assert_not_called()
        self.assertEqual(result['eligible_urls'],0)

    def test_successful_cache_is_reused_without_fetch_and_preserved(self):
        record={'source_url':self.url,'http':200,'title':'Pine Ridge High School - Hudl','checked_at':1,'custom_evidence':'preserve'}
        self.cache.write_text(json.dumps([record]))
        result=self.refresh(now=9999999999)
        self.fetch.assert_not_called()
        self.assertEqual(result['reused_success'],1)
        self.assertEqual(json.loads(self.cache.read_text()),[record])

    def test_failed_cache_waits_until_ttl_then_retries_preserving_failure(self):
        for status,ttl in [(404,86400),(403,86400),(429,60),(503,60),(None,60)]:
            with self.subTest(http=status):
                self.fetch.reset_mock()
                old={'source_url':self.url,'http':status,'checked_at':1000000,'error':'prior actual failure'}
                self.cache.write_text(json.dumps([old]))
                result=self.refresh(now=1000000+ttl-1)
                self.fetch.assert_not_called()
                self.assertEqual(result['cached_failure_waiting_ttl'],1)
                result=self.refresh(now=1000000+ttl)
                self.fetch.assert_called_once()
                self.assertEqual(result['fetch_success'],1)
                saved=json.loads(self.cache.read_text())[0]
                self.assertEqual(saved['failure_history'],[old])
                self.assertEqual(saved['checked_at'],1000000+ttl)

    def test_occupied_and_explicitly_unrelated_rows_never_fetch(self):
        self.fixture([('Pine Ridge',self.url),('Birch School','https://hudl.com/team/2/birch'),('football highlights','https://hudl.com/team/3/football'),('local obituary','https://hudl.com/team/4/local')])
        result=self.refresh(occupied_keywords={'PINE RIDGE'},occupied_slugs={'birch-school'})
        self.fetch.assert_not_called()
        self.assertEqual(result['eligible_urls'],0)
        self.assertEqual(result['unavailable_or_occupied'],2)
        self.assertEqual(result['excluded_intent'],2)

    def test_transport_retries_six_times_before_recording_failure(self):
        with patch.object(cache,'_session',side_effect=TimeoutError('temporary TLS timeout')) as session, patch.object(cache.time,'sleep'):
            result=cache.fetch_one(self.url)
        self.assertEqual(session.call_count,6)
        self.assertEqual(len(result['attempts']),6)
        self.assertIsNone(result['http'])

    def test_hash_mismatch_fails_before_any_fetch_or_cache_change(self):
        for target in ('pool','export'):
            with self.subTest(target=target):
                self.fixture([('Pine Ridge',self.url)])
                path=getattr(self,target)
                path.write_text(path.read_text()+'\n')
                before=self.cache.read_bytes()
                self.fetch.reset_mock()
                with self.assertRaisesRegex(ValueError,'SHA256'):
                    self.refresh()
                self.fetch.assert_not_called()
                self.assertEqual(self.cache.read_bytes(),before)

    def test_fetch_error_is_unresolved_and_saved_not_promoted(self):
        self.fetch.side_effect=TimeoutError('mock timeout')
        result=self.refresh()
        self.assertEqual(result['fetch_failed'],1)
        saved=json.loads(self.cache.read_text())[0]
        self.assertIsNone(saved['http'])
        self.assertIn('mock timeout',saved['error'])
        eligible,counts=self.select()
        self.assertEqual(eligible,[])
        self.assertEqual(counts['unresolved_source_fetch'],1)

if __name__ == '__main__':
    unittest.main()
