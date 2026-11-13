import copy,json,unittest
from pathlib import Path
from build_videos import validate
class Gate(unittest.TestCase):
 def setUp(self):
  self.r=json.loads((Path(__file__).resolve().parents[1]/'content/videos/manifest.json').read_text())[0]
  self.r['status']='unlisted_playback_verified';vid=self.r['video_id']
  self.r['youtube_api_status']={'privacyStatus':'unlisted','uploadStatus':'processed','embeddable':True}
  self.r['anonymous_playback']={'anonymous':True,'video_id':vid,'watch_video_id':vid,'embed_video_id':vid,'watch_ad_free':True,'watch_played_seconds':4,'embed_played_seconds':4,'checked_at':'2026-11-13T09:00:00Z'}
 def test_valid(self):self.assertEqual(validate(self.r)['status'],'unlisted_playback_verified')
 def test_api_not_enough(self):
  self.r.pop('anonymous_playback')
  with self.assertRaises(ValueError):validate(self.r)
 def test_wrong_id_ad_or_short_play_rejected(self):
  for field,value in [('watch_ad_free',False),('embed_video_id','wrong'),('watch_video_id','wrong'),('embed_played_seconds',0)]:
   r=copy.deepcopy(self.r);r['anonymous_playback'][field]=value
   with self.assertRaises(ValueError):validate(r)
 def test_private_rejected(self):
  self.r['youtube_api_status']['privacyStatus']='private'
  with self.assertRaises(ValueError):validate(self.r)
if __name__=='__main__':unittest.main()
