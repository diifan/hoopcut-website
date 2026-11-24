"""Read-only export joining tracer choices to actual platform/page receipts.
No platform polling, publishing or inferred engagement counts.
"""
import csv,json,argparse
from pathlib import Path
from collections import Counter
BASE=Path('/var/lib/swi-codex/xcut-seo-agent')
def report(out):
 source=BASE/'data/hoopcut-daily/materials.json';data=json.loads(source.read_text());items=data if isinstance(data,list) else data.get('materials',data.get('records',[]))
 rows=[]
 for item in items:
  style=item.get('tracer_style');receipt=item.get('tracer_style_receipt')
  if not style and receipt and Path(receipt).is_file():
   s=json.loads(Path(receipt).read_text());style=s.get('style',{}).get('id')
  rows.append({'task_id':item.get('task_id'),'day':item.get('batch_date'),'tracer_style':style or 'unknown-legacy','youtube_url':item.get('video_url'),'instagram_url':item.get('instagram_url'),'page_urls':' '.join(item.get('page_urls') or []),'upload_status':item.get('upload_status'),'instagram_status':item.get('instagram_status'),'views':None,'likes':None,'comments':None})
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 result={'note':'Style exposure mapping only. Missing platform engagement is null, not zero. Compare rates with matching publication windows and platform; content/source differences remain confounders.','style_counts':dict(Counter(r['tracer_style'] for r in rows)),'rows':rows}
 (out/'tracer-style-exposure.json').write_text(json.dumps(result,indent=2))
 with (out/'tracer-style-exposure.csv').open('w') as f:
  fields=['task_id','day','tracer_style','youtube_url','instagram_url','page_urls','upload_status','instagram_status','views','likes','comments'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 print(json.dumps({'records':len(rows),'known_styles':sum(r['tracer_style']!='unknown-legacy' for r in rows),'output':str(out)}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',default=str(BASE/'data/hoopcut-daily/style-report'));report(p.parse_args().out)
