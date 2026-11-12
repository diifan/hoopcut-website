import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from html.parser import HTMLParser
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('tracer',ROOT/'scripts/build_shot_tracer.py')
tracer=importlib.util.module_from_spec(spec);spec.loader.exec_module(tracer)
class Page(HTMLParser):
    def __init__(self,text):super().__init__();self.links=[];self.ids=[];self.canonical=[];self.feed(text)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        if tag=='a':self.links.append(a.get('href',''))
        if tag=='link' and a.get('rel')=='canonical':self.canonical.append(a['href'])
class Tests(unittest.TestCase):
    def setUp(self):
        self.pages=json.loads((ROOT/'content/shot-tracer/pages.json').read_text())
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        shutil.copytree(ROOT/'content/shot-tracer',self.root/'content/shot-tracer')
        # Test draft isolation independently of the real site's release state.
        fixture_files=[self.root/'content/shot-tracer/pages.json',*list((self.root/'content/shot-tracer/batches').glob('*/*.json'))]
        for file in fixture_files:
            data=json.loads(file.read_text())
            for p in data:
                if p['slug']:
                    p['status']='draft';p['reviewedBy']=None;p['exampleEvidence']=None
            file.write_text(json.dumps(data))
        self.pages=json.loads((self.root/'content/shot-tracer/pages.json').read_text())
        (self.root/'sitemap.xml').write_text('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://hoopcut.ai/</loc><lastmod>2026-10-01</lastmod></url></urlset>')
    def test_tool_contract_and_idempotence(self):
        tracer.build(self.root);first=(self.root/'shot-tracer.html').read_bytes();sitemap=(self.root/'sitemap.xml').read_bytes()
        tracer.build(self.root);self.assertEqual(first,(self.root/'shot-tracer.html').read_bytes());self.assertEqual(sitemap,(self.root/'sitemap.xml').read_bytes())
        shell=Page((self.root/'content/shot-tracer/tool.html').read_text());page=Page(first.decode())
        self.assertEqual(shell.ids,page.ids);self.assertEqual(len(page.ids),len(set(page.ids)))
        self.assertEqual(page.canonical,['https://hoopcut.ai/shot-tracer']);self.assertIn('/assets/shot-tracer-tool.js?v=',first.decode())
    def test_drafts_not_shipped(self):
        routes=tracer.build(self.root);self.assertEqual(routes,{'/shot-tracer'});self.assertFalse((self.root/'shot-tracer').exists())
    def test_keyword_previews_share_tool_and_do_not_enter_sitemap(self):
        slugs=['home-court-basketball-training-app','hot-shot-basketball','nba-scout']
        routes=tracer.build(self.root,preview_slugs=slugs)
        self.assertEqual(len(routes),5)  # hub + three requested pages + local directory
        shell=(self.root/'content/shot-tracer/tool.html').read_text()
        import re
        shared_tool=re.search(r'<div class="workspace".*?</div><section class="tracer-walkthrough"',shell,re.S)[0].split('<section class="tracer-walkthrough"')[0]
        for slug in slugs:
            source=(self.root/f'shot-tracer/{slug}.html').read_text()
            page=Page(source)
            self.assertEqual(len(page.ids),len(set(page.ids)))
            self.assertEqual(page.canonical,[tracer.BASE+'/shot-tracer/'+slug])
            self.assertIn(shared_tool,source)
            self.assertIn('content="noindex,follow"',source)
            self.assertIn('id="keyword-guide"',source)
            self.assertIn('id="keyword-questions"',source)
            self.assertIn('6824860341',source)
            self.assertNotIn('{{',source)
        self.assertNotIn('hot-shot-basketball',(self.root/'sitemap.xml').read_text())
        self.assertFalse((self.root/'shot-tracer/free-throws.html').exists())
        tracer.build(self.root)
        for slug in slugs:self.assertFalse((self.root/f'shot-tracer/{slug}.html').exists())
    def test_unknown_preview_slug_rejected(self):
        with self.assertRaises(ValueError):tracer.build(self.root,preview_slugs=['not-requested'])
    def test_batch_drafts_need_explicit_preview_and_stay_out_of_sitemap(self):
        p=copy.deepcopy(self.pages[-1]);p.update(slug='batch-fixture',intent='batch-fixture',title='Batch fixture',description='A separate fixture description')
        folder=self.root/'content/shot-tracer/batches/qa-batch';folder.mkdir(parents=True)
        (folder/'pages.json').write_text(json.dumps([p]))
        manifests=self.root/'content/shot-tracer/batch-manifests';manifests.mkdir(exist_ok=True)
        (manifests/'qa-batch.json').write_text(json.dumps({'previewSlugs':['batch-fixture']}))
        self.assertEqual(tracer.build(self.root),{'/shot-tracer'})
        routes=tracer.build(self.root,preview_batch='qa-batch')
        self.assertEqual(routes,{'/shot-tracer','/shot-tracer/batch-fixture','/shot-tracer/scenarios'})
        self.assertIn('noindex,follow',(self.root/'shot-tracer/scenarios.html').read_text())
        self.assertNotIn('batch-fixture',(self.root/'sitemap.xml').read_text())
        tracer.build(self.root)
        self.assertFalse((self.root/'shot-tracer/batch-fixture.html').exists())
        with self.assertRaises(ValueError):tracer.build(self.root,preview_batch='../qa-batch')
    def test_duplicate_page_between_source_files_is_rejected(self):
        folder=self.root/'content/shot-tracer/batches/duplicate';folder.mkdir(parents=True)
        (folder/'pages.json').write_text(json.dumps([self.pages[-1]]))
        with self.assertRaisesRegex(ValueError,'Duplicate slug'):tracer.load_pages(self.root)
    def test_source_links_reject_script_protocol(self):
        p=copy.deepcopy(self.pages[0]);p['sources']=[{'title':'Unsafe','url':'javascript:alert(1)'}]
        with self.assertRaises(ValueError):tracer.validate([p])
    def test_evidence_and_duplicate_intent(self):
        pages=copy.deepcopy(self.pages);pages[1]['status']='approved'
        with self.assertRaises(ValueError):tracer.validate(pages)
        pages=copy.deepcopy(self.pages);pages[1]['intent']=pages[0]['intent'].upper()
        with self.assertRaises(ValueError):tracer.validate(pages)
    def test_safe_output(self):
        p=copy.deepcopy(self.pages[0]);p['heading']='<script>alert(1)</script>'
        out=tracer.render(p,[p],(ROOT/'content/shot-tracer/tool.html').read_text());self.assertIn('&lt;script&gt;',out)
        p['examples']=[['javascript:alert(1)','bad','bad']]
        with self.assertRaises(ValueError):tracer.validate([p])
    def test_link_patch_idempotent(self):
        source='<main><h1>Guide</h1></main>';updated=tracer.add_tool_link(source)
        self.assertEqual(updated,tracer.add_tool_link(updated));self.assertIn('href="/shot-tracer"',updated)
    def test_thousand_pages_reachable_and_reversible(self):
        pages=[self.pages[0]]
        for i in range(1000):
            p=copy.deepcopy(self.pages[1]);p.update(slug=f'fixture-{i}',intent=f'fixture-{i}',title=f'Fixture {i}',description=f'Fixture description {i}',status='approved',reviewedBy='test fixture',demandEvidence={'source':'synthetic test only'},exampleEvidence={'url':'/demo/shot-tracer'},examples=[['/demo/shot-tracer','Fixture evidence','Synthetic test only']]);pages.append(p)
        (self.root/'content/shot-tracer/pages.json').write_text(json.dumps(pages))
        routes=tracer.build(self.root);self.assertEqual(len(routes),1043)
        graph={route:Page((self.root/(route.lstrip('/')+'.html')).read_text()) for route in routes}
        reached={'/shot-tracer'};queue=list(reached)
        while queue:
            for link in graph[queue.pop()].links:
                if link in graph and link not in reached:reached.add(link);queue.append(link)
        self.assertEqual(reached,routes)
        for route,p in graph.items():self.assertEqual(p.canonical,[tracer.BASE+route]);self.assertLess(len(p.links),45)
        xml=ET.parse(self.root/'sitemap.xml');self.assertEqual(len(xml.getroot()),1044);self.assertEqual(xml.findtext('.//{*}lastmod'),'2026-10-01')
        (self.root/'content/shot-tracer/pages.json').write_text(json.dumps(self.pages))
        tracer.build(self.root);self.assertEqual(list((self.root/'shot-tracer').rglob('*.html')),[])
        self.assertEqual(len(ET.parse(self.root/'sitemap.xml').getroot()),2)
if __name__=='__main__':unittest.main()
