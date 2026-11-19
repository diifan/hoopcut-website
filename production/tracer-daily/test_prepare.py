"""Offline safety regressions; no builds, credentials or network access."""
import ast
import contextlib
import importlib.util
import io
import json
import pathlib
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
SOURCE = pathlib.Path(__file__).with_name('prepare.py')
spec = importlib.util.spec_from_file_location('tracer_prepare_under_test', SOURCE)
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)

class Guards(unittest.TestCase):
    def test_calendar_date(self):
        self.assertEqual(prepare.validate_day('2028-02-29'), '2028-02-29')
        for bad in ['2026-02-29', '2026-13-01', '2026-11-31', '2026-1-01', '20261119', '../2026-11-19', '2026-11-19T00:00:00', '2026-11-19\n']:
            with self.subTest(day=bad), self.assertRaises(ValueError):
                prepare.validate_day(bad)

    def test_deployment_requires_correct_ready_production(self):
        valid = dict(projectId='prj_hoopcut', target='production', readyState='READY', alias=['prepared-123.vercel.app'])
        self.assertEqual(prepare.validate_deployment(valid, 'prj_hoopcut'), valid)
        for field, values in [('projectId', [None, 'prj_other']), ('target', [None, 'preview']), ('readyState', [None, 'BUILDING', 'ERROR', 'CANCELED'])]:
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    prepare.validate_deployment({**valid, field: value}, 'prj_hoopcut')
        for domain in ['hoopcut.ai', 'www.hoopcut.ai']:
            with self.subTest(domain=domain), self.assertRaises(ValueError):
                prepare.validate_deployment({**valid, 'alias': ['prepared.vercel.app', domain]}, 'prj_hoopcut')

    def test_exact_count_and_duplicate_identities(self):
        pages = [{'keyword':'First Shot', 'slug':'first-shot'}, {'keyword':'Second Shot', 'slug':'second-shot'}]
        prepare.validate_count(pages, 2)
        for sample in [pages[:1], pages + [{'keyword':'third', 'slug':'third'}], [pages[0], {'keyword':'first shot', 'slug':'another'}], [pages[0], {'keyword':'different', 'slug':'first-shot'}]]:
            with self.subTest(sample=sample), self.assertRaises(ValueError):
                prepare.validate_count(sample, 2)

    def test_other_batch_reservations_survive_resume(self):
        reservations = [dict(batch_id='yesterday', keywords=['SCHOOL Basketball'], slugs=['school-basketball']), dict(batch_id='today', keywords=['Own Draft'], slugs=['own-draft']), dict(batch_id='tomorrow', keywords=['Later Draft'], slugs=['later-draft'])]
        original = json.dumps(reservations)
        self.assertEqual(prepare.occupied(reservations, 'today'), ({'school basketball', 'later draft'}, {'school-basketball', 'later-draft'}))
        self.assertEqual(len(prepare.occupied(reservations)[0]), 3)
        self.assertEqual(json.dumps(reservations), original)

    def test_no_live_domain_mutation_commands(self):
        # Inspect executable command argument lists, not comments/read-only alias API keys.
        tree = ast.parse(SOURCE.read_text())
        prohibited = {'merge', 'promote', 'alias'}
        for node in ast.walk(tree):
            if isinstance(node, (ast.List, ast.Tuple)):
                words = [x.value for x in node.elts if isinstance(x, ast.Constant) and isinstance(x.value, str)]
                self.assertFalse(prohibited.intersection(words), words)
        deploy_lists = [n for n in ast.walk(tree) if isinstance(n, ast.List) and any(isinstance(x, ast.Constant) and x.value == 'deploy' for x in n.elts)]
        self.assertTrue(deploy_lists)
        for node in deploy_lists:
            self.assertIn('--skip-domain', [x.value for x in node.elts if isinstance(x, ast.Constant)])

    def test_shortfall_stops_before_build_commit_or_deploy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            toolroot = root / 'production' / 'tracer-daily'
            toolroot.mkdir(parents=True)
            repo = root / 'repository'; repo.mkdir()
            worktree = root / 'website-tracer-daily-20261119'; worktree.mkdir()
            (toolroot/'config.json').write_text(json.dumps(dict(repository=str(repo), project_id='prj_hoopcut', proxy='http://unused.invalid', cache_path='cache', vercel='never-vercel', scope='test')))
            pool = root/'pool.csv'; pool.write_text('keyword,status\nshot,available\n')
            manifest = root/'sources.json'; manifest.write_text('{}')
            receipt = root/'receipt.json'
            engine = types.ModuleType('content_engine')
            engine.select_candidates = lambda *a: ([{'keyword':'shot', 'slug':'shot'}], {'eligible':1})
            engine.build_shard = lambda *a: self.fail('Shortfall must not assemble')
            calls = []
            def fake_run(argv, **kwargs):
                calls.append(argv)
                if argv[:3] == ['git', 'rev-parse', 'origin/main']:
                    return types.SimpleNamespace(returncode=0, stdout='baseline-sha\n', stderr='')
                if argv == ['git', 'diff', '--name-only']:
                    return types.SimpleNamespace(returncode=0, stdout='', stderr='')
                if argv[:2] == ['git', 'show'] and argv[2].endswith(':sitemap.xml'):
                    return types.SimpleNamespace(returncode=0, stdout='<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://hoopcut.ai/</loc></url></urlset>', stderr='')
                if 'fetch' in argv:
                    return types.SimpleNamespace(returncode=0, stdout='', stderr='')
                self.fail('Unexpected command after shortfall: '+repr(argv))
            argv = ['prepare.py', '--day','2026-11-19','--pool',str(pool),'--source-manifest',str(manifest),'--receipt',str(receipt),'--target','2']
            with patch.object(prepare,'ROOT',toolroot), patch.object(prepare,'PROJECT_ROOT',root), patch.object(prepare,'collect_occupied',return_value=(set(),set())), patch.object(prepare.subprocess,'run',side_effect=fake_run), patch.dict(sys.modules, {'content_engine':engine}), patch.object(sys,'argv',argv), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(prepare.main(), 2)
            data = json.loads(receipt.read_text())
            self.assertEqual(data['stage'], 'insufficient_pool')
            self.assertEqual(data['shortfall'], 1)
            self.assertFalse(data['published'])
            self.assertFalse(data['ready_for_promotion'])
            self.assertEqual(data['blockers'][0]['type'], 'pool_shortfall')
            self.assertFalse(list((toolroot/'state').glob('*.reservation.json')))
            self.assertTrue(all(argv[0] == 'git' for argv in calls))

if __name__ == '__main__':
    unittest.main()
