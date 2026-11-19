#!/usr/bin/env python3
"""After controller-confirmed promotion only, fast-forward main to the deployed commit."""
import argparse, json, pathlib, subprocess, os, hashlib
ROOT=pathlib.Path(__file__).resolve().parent

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--receipt',required=True,type=pathlib.Path);ap.add_argument('--confirm-promoted',action='store_true',required=True);a=ap.parse_args();r=json.loads(a.receipt.read_text());cfg=json.loads((ROOT/'config.json').read_text());w=pathlib.Path(r['worktree'])
 def run(cmd):return subprocess.check_output(cmd,cwd=w,text=True).strip()
 def api(path):return json.loads(run([cfg['vercel'],'api',path,'--scope',cfg['scope']]))
 if not r.get('published'):raise ValueError('Controller must first verify live promotion and set published=true')
 d=api('/v13/deployments/'+r['prepared_deployment_id'])
 if d.get('readyState')!='READY' or d.get('target')!='production' or d.get('projectId')!=cfg['project_id']:raise ValueError('Wrong deployment state/project/environment')
 if d.get('meta',{}).get('swieBatch')!=r['batch_id'] or d.get('meta',{}).get('swieCommit')!=r['commit']:raise ValueError('Wrong promoted batch/commit')
 for host in ['hoopcut.ai','www.hoopcut.ai']:
  if api('/v4/aliases/'+host).get('deploymentId')!=r['prepared_deployment_id']:raise ValueError('Live domain does not point at prepared deployment')
 if hashlib.sha256(pathlib.Path(r['pages_path']).read_bytes()).hexdigest()!=r['pages_sha256']:raise ValueError('Prepared pages changed')
 git=['git','-c','http.proxy='+cfg['proxy'],'-c','http.version=HTTP/1.1','-c','http.postBuffer=524288000']
 run(git+['fetch','origin','main']);head=run(['git','rev-parse','origin/main'])
 if head!=r['commit']:
  if head!=r['base_commit']:raise ValueError('main advanced; refuse to overwrite concurrent changes. Reconcile via reviewed merge/rebuild.')
  if run(['git','rev-parse',r['commit']+'^'])!=r['base_commit']:raise ValueError('Prepared commit is not a direct child of recorded baseline')
  run(git+['push','origin',r['commit']+':refs/heads/main'])
  remote=run(git+['ls-remote','origin','refs/heads/main']).split()[0]
  if remote!=r['commit']:raise ValueError('Remote main reconciliation not confirmed')
 r['checks']['git_finalized']={'commit':r['commit'],'fast_forward':True};t=a.receipt.with_suffix('.tmp');t.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');os.replace(t,a.receipt);print(json.dumps(r['checks']['git_finalized']))
if __name__=='__main__':main()
