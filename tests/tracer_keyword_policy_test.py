import sys, pathlib, unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"scripts"))
from tracer_keyword_policy import rejection_reason, identity_aligned
BAD=['4.2gpa', 'actor reema lagoo', '3.3gpa', '3.7gpa', 'aidra fox gif', 'colin hurley actor', '3.1gpa', 'how tall was actor james arness', '43/50 grade', 'actress ariyan johnson', 'aidra fox creampie', 'aidra fox brandi love', '3.9gpa', 'aidra fox hookup hotshot', 'pierson fode naked', 'aidra fox twitter', 'ohiya casino resort', 'taylee wood anal', 'akih hentai', '192lbs to kg', 'aidra fox deepthroat', 'aidra fox naked', '3.75gpa', 'ary vilchis onlyfans']
class PolicyTest(unittest.TestCase):
 def test_reported_unrelated_intents(self):
  for keyword in BAD:
   with self.subTest(keyword=keyword):self.assertTrue(rejection_reason(keyword))
 def test_valid_sports_identity_retained(self):
  for keyword in ['john smith','viewmont high','school basketball highlights','hudl video editing']:
   self.assertIsNone(rejection_reason(keyword))
 def test_whole_identity_required(self):
  self.assertTrue(identity_aligned('john smith','John Smith - Hudl'))
  self.assertFalse(identity_aligned('john smith unrelated modifier','John Smith - Hudl'))
if __name__=='__main__':unittest.main()
