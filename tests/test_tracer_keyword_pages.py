import copy
import csv
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
spec = importlib.util.spec_from_file_location('keyword_pages', ROOT/'scripts/prepare_tracer_keyword_pages.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class KeywordPageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        folder = self.root/'content/shot-tracer'
        folder.mkdir(parents=True)
        original = json.loads((ROOT/'content/shot-tracer/pages.json').read_text())
        (folder/'pages.json').write_text(json.dumps([original[0], next(p for p in original if p.get('keyword') == 'nba scout')]))
        self.csv = self.root/'rankings.csv'
        with self.csv.open('w') as stream:
            writer = csv.DictWriter(stream, fieldnames=['Keyword', 'Search Volume', 'Keyword Difficulty', 'Position', 'Timestamp'])
            writer.writeheader()
            for keyword, pos in [('basketball app', '3'), ('basketball app', '5'), ('basketball apps', '7'), ('nba scout', '8')]:
                writer.writerow({'Keyword': keyword, 'Search Volume': '100', 'Keyword Difficulty': '21', 'Position': pos, 'Timestamp': '2026-11-09'})
        self.profile = self.root/'profiles.json'
        self.profiles = [self.make_profile(k) for k in ('basketball app', 'basketball apps')]
        self.profile.write_text(json.dumps(self.profiles))

    def make_profile(self, keyword):
        return {'keyword': keyword, 'slug': keyword.replace(' ', '-'), 'title': keyword + ' | HoopCut',
                'description': 'A description for ' + keyword, 'heading': keyword + ' with a tracer',
                'label': keyword, 'intro': 'Introduction to ' + keyword, 'heroDetail': 'A saved shot for ' + keyword,
                'guideHeading': keyword + ' guide', 'guideText': 'Useful recording context.',
                'topic': 'apps', 'intentFit': 'direct', 'tips': [{'heading': 'Release', 'text': 'Keep the release visible.'},
                                                               {'heading': 'Finish', 'text': 'Keep the finish visible.'}],
                'faq': [['Can I upload?', 'Yes, use saved footage.'], ['Is it a statistic?', 'No, it is an effect.']]}

    def run_prepare(self):
        return module.prepare(self.csv, [self.profile], 'test-one-per-keyword', root=self.root)

    def test_synonyms_stay_separate_duplicate_rankings_keep_one_route(self):
        result = self.run_prepare()
        self.assertEqual(result['source']['rows'], 4)
        self.assertEqual(result['source']['uniqueKeywords'], 3)
        self.assertEqual(result['source']['duplicateRankingRows'], 1)
        self.assertEqual(len(set(x['targetPath'] for x in result['keywords'])), 3)
        duplicate = next(x for x in result['keywords'] if x['keyword'] == 'basketball app')
        self.assertEqual([x['Position'] for x in duplicate['records']], ['3', '5'])
        self.assertEqual(result['reusedSlugs'], ['nba-scout'])
        self.assertEqual(set(result['newSlugs']), {'basketball-app', 'basketball-apps'})
        pages = json.loads((self.root/'content/shot-tracer/batches/test-one-per-keyword/pages.json').read_text())
        self.assertTrue(all(p['status'] == 'draft' for p in pages))
        self.assertTrue(all(len(p['targetKeywords']) == 1 for p in pages))

    def test_rerun_keeps_identical_manifest_and_authored_pages(self):
        self.run_prepare()
        files = list((self.root/'content/shot-tracer').rglob('*.json'))
        before = {str(p): p.read_bytes() for p in files}
        self.run_prepare()
        self.assertEqual(before, {str(p): p.read_bytes() for p in files})

    def test_missing_profile_fails_before_writing_pages(self):
        self.profile.write_text(json.dumps(self.profiles[:1]))
        with self.assertRaisesRegex(ValueError, 'Profile coverage mismatch'):
            self.run_prepare()
        self.assertFalse((self.root/'content/shot-tracer/batches').exists())

    def test_approved_import_stays_approved_and_rejects_changed_copy(self):
        self.run_prepare()
        file=self.root/'content/shot-tracer/batches/test-one-per-keyword/pages.json'
        pages=json.loads(file.read_text())
        for p in pages:
            p['status']='approved';p['reviewedBy']='Test approval'
            p['exampleEvidence']={'url':p['examples'][0][0]}
            p['releaseApproval']={'batch':'test','version':'approved-fixture'}
        file.write_text(json.dumps(pages,ensure_ascii=False,indent=2)+'\n')
        before=file.read_bytes()
        self.run_prepare()
        self.assertEqual(before,file.read_bytes())
        self.profiles[0]['intro']='A new, not yet reviewed introduction.'
        self.profile.write_text(json.dumps(self.profiles))
        with self.assertRaisesRegex(ValueError,'Approved page changed'):
            self.run_prepare()
        self.assertEqual(before,file.read_bytes())

    def test_conflicting_slugs_fail_before_writing_pages(self):
        profiles = copy.deepcopy(self.profiles)
        profiles[1]['slug'] = profiles[0]['slug']
        self.profile.write_text(json.dumps(profiles))
        with self.assertRaisesRegex(ValueError, 'Duplicate slug'):
            self.run_prepare()
        self.assertFalse((self.root/'content/shot-tracer/batches').exists())


if __name__ == '__main__':
    unittest.main()
