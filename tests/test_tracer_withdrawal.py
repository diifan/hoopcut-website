"""A withdrawn page must not return via rebuilding, previewing or reimporting."""
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import build_shot_tracer as tracer
from tracer_keyword_policy import rejection_reason


class WithdrawalTests(unittest.TestCase):
    def test_rebuild_removes_page_links_and_sitemap_without_deleting_record(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            shutil.copytree(ROOT/'content/shot-tracer',root/'content/shot-tracer')
            for path in (root/'content/shot-tracer/batches').glob('*/*.json'):
                path.unlink()
            hub=json.loads((ROOT/'content/shot-tracer/pages.json').read_text())[0]
            original=next(p for p in json.loads((ROOT/'content/shot-tracer/batches/tracer-daily-20261120/pages.json').read_text()) if p['slug']=='jeana-cappolla')
            renamed=copy.deepcopy(original)
            renamed.update(slug='renamed-withdrawn-page',intent='renamed-withdrawn-page',title='Renamed withdrawn page',description='Renamed withdrawn description')
            active=copy.deepcopy(original)
            active.update(slug='active-fixture',keyword='active fixture',label='Active fixture',heading='Active fixture',intro='Active fixture',intent='active-fixture',title='Active fixture',description='Active fixture description')
            source=root/'content/shot-tracer/pages.json'
            source.write_text(json.dumps([hub,original,renamed,active]))
            before=source.read_bytes()
            (root/'shot-tracer/scenarios').mkdir(parents=True)
            (root/'shot-tracer/jeana-cappolla.html').write_text('Old public page')
            (root/'shot-tracer/scenarios.html').write_text('Old link to jeana-cappolla')
            (root/'sitemap.xml').write_text('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://hoopcut.ai/shot-tracer/jeana-cappolla</loc></url></urlset>')
            routes=tracer.build(root)
            self.assertEqual(routes,{'/shot-tracer','/shot-tracer/active-fixture','/shot-tracer/scenarios'})
            self.assertFalse((root/'shot-tracer/jeana-cappolla.html').exists())
            self.assertFalse((root/'shot-tracer/renamed-withdrawn-page.html').exists())
            self.assertNotIn('jeana-cappolla',(root/'sitemap.xml').read_text())
            self.assertNotIn('jeana-cappolla',(root/'shot-tracer/scenarios.html').read_text())
            self.assertEqual(source.read_bytes(),before)
            with self.assertRaisesRegex(ValueError,'Unknown preview slugs'):
                tracer.build(root,preview_slugs=['jeana-cappolla'])
            for keyword in ('jeana cappolla','Jeana Cappolla','  JEANA   CAPPOLLA  ','jeana-cappolla'):
                self.assertEqual(rejection_reason(keyword),'withdrawn from publication')
            self.assertIsNone(rejection_reason('active fixture'))


if __name__=='__main__':
    unittest.main()
