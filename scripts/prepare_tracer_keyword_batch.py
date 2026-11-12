#!/usr/bin/env python3
"""Join reviewed keyword decisions to source records without inventing demand data."""
import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def prepare(source,mapping_file,batch,root=ROOT):
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',batch):raise ValueError('Invalid batch name')
    raw=source.read_bytes();text=raw.decode('utf-8-sig')
    rows=list(csv.DictReader(text.splitlines(),dialect=csv.Sniffer().sniff(text[:4096])))
    grouped=defaultdict(list)
    for number,row in enumerate(rows,2):
        key=' '.join(row['Keyword'].strip().casefold().split())
        grouped[key].append({'row':number,**row})
    mapping=json.loads(mapping_file.read_text())
    if isinstance(mapping,dict):mapping=mapping.get('entries',mapping.get('keywords',mapping.get('mapping',mapping.get('rows'))))
    if not isinstance(mapping,list):raise ValueError('Expected keyword decision array')
    decisions={x['keyword']:x for x in mapping}
    if len(decisions)!=len(mapping):raise ValueError('Duplicate keyword decisions')
    missing=set(grouped)-set(decisions);extra=set(decisions)-set(grouped)
    if missing or extra:raise ValueError(f'Unreconciled keywords: missing={sorted(missing)}, extra={sorted(extra)}')
    for d in mapping:
        if d['action'] not in {'create','existing','merge','defer'}:raise ValueError('Unknown decision')
        if not d.get('reason'):raise ValueError('Decision needs a rationale')
        if d['action']!='defer' and not (d.get('targetPath','').startswith('/') and not d['targetPath'].startswith('//')):raise ValueError('Decision needs a site path')
        # Preserve every source row, including keyword-level dates and differing positions.
        d['records']=grouped[d['keyword']]
    selected=sorted({d['targetPath'].split('/shot-tracer/',1)[1] for d in mapping if d['action']!='defer' and d.get('targetPath','').startswith('/shot-tracer/')})
    authored=[];updates=[];batch_ids=set()
    for file in sorted((root/'content/shot-tracer/batches'/batch).glob('*.json')):
        pages=json.loads(file.read_text())
        for p in pages:
            keyword=p['keyword'].casefold().strip()
            if keyword not in grouped:raise ValueError('Authored keyword missing from source: '+keyword)
            if p['slug'] not in selected:raise ValueError('Authored page absent from keyword map: '+p['slug'])
            p['targetKeywords']=sorted(d['keyword'] for d in mapping if d.get('targetPath')=='/shot-tracer/'+p['slug'])
            p['demandEvidence']={'source':'User-provided Semrush Organic Positions CSV','file':source.name,'sourceSha256':hashlib.sha256(raw).hexdigest(),'market':'US','keyword':keyword,'records':grouped[keyword],'note':'Original estimates and record dates retained. No search-volume summation, predicted traffic or organic results inferred.'}
            authored.append(p['slug'])
            if p.get('batchId'):batch_ids.add(p['batchId'])
        updates.append((file,pages))
    base=json.loads((root/'content/shot-tracer/pages.json').read_text())
    available={p['slug'] for p in base}|set(authored)
    if set(selected)-available:raise ValueError('Mapped draft is missing: '+', '.join(sorted(set(selected)-available)))
    source_info={'file':source.name,'sha256':hashlib.sha256(raw).hexdigest(),'rows':len(rows),'uniqueKeywords':len(grouped),'market':'US','provider':'Semrush; estimates, not GSC','recordDates':sorted({r['Timestamp'] for r in rows if r.get('Timestamp')})}
    if len(batch_ids)>1:raise ValueError('Mixed batch IDs in authored pages')
    batch_id=next(iter(batch_ids)) if batch_ids else 'HC-TRACER-'+batch.upper()
    manifest={'name':batch,'batchId':batch_id,'source':source_info,'previewSlugs':selected,'newSlugs':sorted(authored),'reusedSlugs':sorted(set(selected)-set(authored)),'decisionCounts':dict(Counter(d['action'] for d in mapping)),'keywords':mapping}
    for file,pages in updates:file.write_text(json.dumps(pages,ensure_ascii=False,indent=2)+'\n')
    dest=root/'content/shot-tracer/batch-manifests'/f'{batch}.json';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--csv',type=Path,required=True);parser.add_argument('--mapping',type=Path,required=True);parser.add_argument('--batch',required=True)
    args=parser.parse_args();result=prepare(args.csv,args.mapping,args.batch)
    print(json.dumps({'rows':result['source']['rows'],'uniqueKeywords':result['source']['uniqueKeywords'],'newPages':len(result['newSlugs']),'reusedPages':len(result['reusedSlugs']),'decisions':result['decisionCounts']}))
