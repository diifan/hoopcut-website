"""Build clean cropped reels from the original 52-second traced highlights.
No captions, selection animations, transitions, speed changes or new effects.
Each player reel contains only that player's verified makes.
Usage: python3 scripts/render_banner.py --source /path/all_makes.mp4
"""
import argparse,json,subprocess,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--source',required=True);a=p.parse_args()
out=ROOT/'assets/video/players';out.mkdir(parents=True,exist_ok=True)
lengths=[128,182,157,162,146,148,159,134,148,196]
# Windows retain the entire shot arc. Tighter on the close-range blue player;
# wider on the red player's high jump shot and the black player's long arc.
crops={i:'1920:960:0:0' for i in range(1,11)}
# Remove 220px of ceiling in close-range plays, retaining the shooter and arc.
crops.update({i:'1520:760:360:220' for i in [1,3,4,5,6,7,9]})
# The long jumper needs extra vertical room above the hoop.
crops[10]='1760:880:80:120' 
reels={'all':list(range(1,11)),'blue':[4,5,6,7,9],'red':[2,3],'black':[10]}
with tempfile.TemporaryDirectory(prefix='hoopcut-clean-') as td:
 td=Path(td);start=0
 for i,length in enumerate(lengths,1):
  subprocess.run(['ffmpeg','-y','-v','error','-ss',str(start/30),'-i',a.source,'-frames:v',str(length),'-vf',f'crop={crops[i]},scale=1600:800:flags=lanczos,setsar=1','-an','-c:v','libx264','-preset','medium','-crf','21','-pix_fmt','yuv420p','-threads','4',str(td/f'{i}.mp4')],check=True)
  start+=length;print(f'Cropped shot {i}/10',flush=True)
 for key,shots in reels.items():
  manifest=td/f'{key}.txt';manifest.write_text(''.join(f"file '{td / (str(i)+'.mp4')}'\n" for i in shots))
  staging=out/f'{key}.next.mp4'
  subprocess.run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(manifest),'-c','copy','-movflags','+faststart',str(staging)],check=True)
  staging.replace(out/f'{key}.mp4')
  poster_time={'all':1,'blue':2.53,'red':2.5,'black':2.8}[key]
  subprocess.run(['ffmpeg','-y','-v','error','-ss',str(poster_time),'-i',str(out/f'{key}.mp4'),'-frames:v','1','-q:v','2',str(out/f'{key}.jpg')],check=True)
  print(f'Built {key}: {len(shots)} makes',flush=True)
(ROOT/'production/banner-edit.json').write_text(json.dumps({'source':'http://192.168.0.112:8132/media/all_makes.mp4?v=5m','reels':reels,'crop_windows':crops,'output':'1600x800 / 30fps','treatment':'Spatial crop only. No added titles, transitions, selection effects or speed changes. Original shot trails retained.','attribution':'Shot 1 has known incorrect attribution and shot 8 is unassigned: both are available only in All.'},indent=2)+'\n')

# Keep the previously shared standalone link on the clean default reel.
shutil.copyfile(out/'blue.mp4',ROOT/'assets/video/hoopcut-banner.mp4')
shutil.copyfile(out/'blue.jpg',ROOT/'assets/video/hoopcut-banner-poster.jpg')
