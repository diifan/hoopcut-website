import sys,tempfile,concurrent.futures,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from assignment import assign
styles=json.loads((Path(__file__).resolve().parents[1]/'catalog.json').read_text())['styles']
with tempfile.TemporaryDirectory() as tmp:
 db=Path(tmp)/'test.sqlite'
 def run(i):return assign(str(i),styles,'test',database=db)
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:out=list(pool.map(run,range(100)))
 for cycle in range(1,5):assert len({r['style_id'] for r in out if r['cycle']==cycle})==25
 for i,r in enumerate(out):assert run(i)==r
 assert len({assign('same',styles,'test',database=db)['style_id'] for _ in range(20)})==1
print('100 concurrent assignments: each block of 25 unique; retries stable')
