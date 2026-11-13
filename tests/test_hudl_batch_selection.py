import csv
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import prepare_hudl_tracer_batch as batch

class SelectionTests(unittest.TestCase):
    def test_reviewed_apostrophe_urls_are_preserved(self):
        self.assertEqual(batch.slugify("Gannon men's basketball"),'gannon-mens-basketball')
        self.assertEqual(batch.slugify("LSU women's basketball roster"),'lsu-womens-basketball-roster')

    def test_source_actions_are_not_treated_as_entity_names(self):
        ctx=batch.context({'Keyword':'example high school','URL':'https://fan.hudl.com/usa/mi/town/organization/5416/tickets'})
        self.assertEqual(ctx['entity'],'')

    def test_current_batch_is_reproducible_and_other_published_urls_protected(self):
        rows=[{'Keyword':f'fixture basketball {i}','URL':f'https://www.hudl.com/team/{i}','Search Volume':'1000'} for i in range(1004)]
        existing=[{'slug':'fixture-basketball-0','keyword':'fixture basketball 0'},
                  {'slug':'fixture-basketball-1','keyword':'fixture basketball 1','releaseApproval':{'batch_id':batch.BATCH}}]
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'source.csv'
            with f.open('w') as stream:
                writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
            with patch.object(batch.tracer,'load_pages',return_value=existing):
                _,first,pending,reused=batch.select(f)
                _,second,_,_=batch.select(f)
        self.assertEqual(first,second)
        self.assertEqual(len(first),1000);self.assertEqual(len(pending),3);self.assertEqual(len(reused),1)
        self.assertNotIn('fixture basketball 0',[x['row']['Keyword'] for x in first])
        self.assertEqual(first[0]['slug'],'fixture-basketball-1')

if __name__=='__main__':unittest.main()
