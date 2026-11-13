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
        for route,p in graph.items():
            self.assertEqual(p.canonical,[tracer.BASE+route])
            self.assertLess(len(p.links),65 if '/scenarios' in route else 45)
        xml=ET.parse(self.root/'sitemap.xml');self.assertEqual(len(xml.getroot()),1044);self.assertEqual(xml.findtext('.//{*}lastmod'),'2026-10-01')
        (self.root/'content/shot-tracer/pages.json').write_text(json.dumps(self.pages))
        tracer.build(self.root);self.assertEqual(list((self.root/'shot-tracer').rglob('*.html')),[])
        self.assertEqual(len(ET.parse(self.root/'sitemap.xml').getroot()),2)
    def test_navigation_respects_topics_and_approved_visibility(self):
        pages=tracer.load_pages(ROOT);taxonomy=tracer.load_link_taxonomy(ROOT)
        approved=[p for p in pages if p['status']=='approved'];mapped=taxonomy['pages']
        self.assertEqual({p['slug'] for p in approved if p['slug']},set(mapped))
        for p in approved:
            if not p['slug']:continue
            related=tracer.related_pages(p,approved,taxonomy)
            if mapped[p['slug']]['relatedGroup'] is None:self.assertEqual(related,[])
            for other in related:
                self.assertNotEqual(p['slug'],other['slug'])
                self.assertEqual(mapped[p['slug']]['relatedGroup'],mapped[other['slug']]['relatedGroup'])
        self.assertEqual(tracer.category_catalog(self.pages,taxonomy),[])
        shell=(ROOT/'content/shot-tracer/tool.html').read_text()
        categories=tracer.category_catalog(approved,taxonomy)
        all_links=Page(tracer.directory(1,[p for p in approved if p['slug']],shell,taxonomy)).links
        total=(len(approved)-1+tracer.PAGE_SIZE-1)//tracer.PAGE_SIZE
        for n in range(1,min(total,3)+1):self.assertIn(tracer.directory_path(n),all_links)
        self.assertIn(tracer.directory_path(total),all_links)
        for category in categories:
            self.assertIn(tracer.category_path(category),all_links)
            for n in range(1,tracer.category_page_count(category)+1):
                self.assertIn(tracer.category_path(category,n),all_links)
                rendered=Page(tracer.directory(n,approved,shell,taxonomy,category))
                self.assertEqual(rendered.canonical,[tracer.BASE+tracer.category_path(category,n)])
                actual={url for url in rendered.links if url in {tracer.route(p) for p in category['pages']}}
                expected={tracer.route(p) for p in category['pages'][(n-1)*tracer.PAGE_SIZE:n*tracer.PAGE_SIZE]}
                self.assertEqual(actual,expected)
    def test_category_pagination_ships_all_lists_and_excludes_drafts(self):
        import re
        published=[]
        for i in range(2*tracer.PAGE_SIZE+5):
            p=copy.deepcopy(self.pages[1])
            p.update(slug=f'category-fixture-{i}',intent=f'category-fixture-{i}',title=f'Category fixture {i}',description=f'Category fixture description {i}',status='approved',reviewedBy='Synthetic test approval',demandEvidence={'source':'Synthetic test only'},exampleEvidence={'url':'/demo/shot-tracer'},examples=[['/demo/shot-tracer','Fixture example','Synthetic test only']])
            published.append(p)
        draft=copy.deepcopy(published[-1]);draft.update(slug='category-draft',intent='category-draft',title='Category draft',description='Category draft description',status='draft',reviewedBy=None,exampleEvidence=None)
        draft_only=copy.deepcopy(draft);draft_only.update(slug='unlisted-draft',intent='unlisted-draft',title='Unlisted draft',description='Unlisted draft description')
        data=[self.pages[0],*published,draft,draft_only]
        (self.root/'content/shot-tracer/pages.json').write_text(json.dumps(data))
        taxonomy={'categories':[{'id':'test-basketball','label':'Test basketball','description':'Synthetic basketball video list.'},{'id':'unlisted','label':'Unlisted','description':'Draft-only fixture.'}],
                  'pages':{p['slug']:{'category':'test-basketball','relatedGroup':'test-group'} for p in [*published,draft]},'featured':[]}
        taxonomy['pages'][draft_only['slug']]={'category':'unlisted','relatedGroup':None}
        (self.root/'content/shot-tracer/internal-link-taxonomy.json').write_text(json.dumps(taxonomy))
        routes=tracer.build(self.root)
        category=tracer.category_catalog(data,taxonomy)[0]
        expected_lists={tracer.category_path(category,n) for n in range(1,4)}
        self.assertTrue(expected_lists.issubset(routes))
        sitemap={node.text for node in ET.parse(self.root/'sitemap.xml').getroot().findall('{*}url/{*}loc')}
        self.assertEqual({tracer.BASE+p for p in routes}|{tracer.BASE+'/'},sitemap)
        self.assertNotIn(tracer.BASE+'/shot-tracer/category-draft',sitemap)
        self.assertFalse(any('/unlisted' in p or '/page-1' in p for p in routes))
        graph={path:Page((self.root/(path.lstrip('/')+'.html')).read_text()) for path in routes}
        root_links=graph['/shot-tracer/scenarios'].links
        self.assertTrue(expected_lists.issubset(root_links))
        titles=set();descriptions=set();found=[]
        for n in range(1,4):
            path=tracer.category_path(category,n);file=self.root/(path.lstrip('/')+'.html');source=file.read_text();page=graph[path]
            self.assertEqual(page.canonical,[tracer.BASE+path])
            self.assertIn('content="index,follow"',source)
            self.assertNotIn('/shot-tracer/category-draft',page.links)
            targets=[x for x in page.links if x in {tracer.route(p) for p in published}]
            self.assertEqual(targets,[tracer.route(p) for p in published[(n-1)*tracer.PAGE_SIZE:n*tracer.PAGE_SIZE]])
            found.extend(targets)
            self.assertTrue(expected_lists.issubset(page.links))
            if n>1:self.assertIn(f'href="{tracer.category_path(category,n-1)}" rel="prev"',source)
            if n<3:self.assertIn(f'href="{tracer.category_path(category,n+1)}" rel="next"',source)
            titles.add(re.search(r'<title>(.*?)</title>',source)[1])
            descriptions.add(re.search(r'<meta name="description" content="(.*?)">',source)[1])
        self.assertEqual(len(titles),3);self.assertEqual(len(descriptions),3)
        self.assertEqual(found,[tracer.route(p) for p in published])
        reached={'/shot-tracer/scenarios'};queue=list(reached)
        while queue:
            for target in graph[queue.pop()].links:
                if target in graph and target not in reached:reached.add(target);queue.append(target)
        self.assertTrue({tracer.route(p) for p in published}.issubset(reached))
        # A local draft preview must not noindex category lists of approved pages.
        tracer.build(self.root,preview_slugs=[draft['slug']])
        for path in expected_lists:self.assertIn('content="index,follow"',(self.root/(path.lstrip('/')+'.html')).read_text())
        # Shrinking a category removes obsolete list routes and sitemap entries.
        for p in published[tracer.PAGE_SIZE:]:p.update(status='draft',reviewedBy=None,exampleEvidence=None)
        (self.root/'content/shot-tracer/pages.json').write_text(json.dumps(data))
        tracer.build(self.root)
        for path in expected_lists-{tracer.category_path(category)}:
            self.assertFalse((self.root/(path.lstrip('/')+'.html')).exists())
            self.assertNotIn(tracer.BASE+path,(self.root/'sitemap.xml').read_text())
if __name__=='__main__':unittest.main()
