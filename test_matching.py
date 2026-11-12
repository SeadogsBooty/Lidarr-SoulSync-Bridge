# ==============================================================================
#
#                              |    |    |
#                             )_)  )_)  )_)
#                            )___))___))___)\
#                           )____)____)_____)\\
#                         _____|____|____|____\\\__
#                    ~~~~~\                   /~~~~~
#                     ~~~~~~^~~~~~~~~^^^^~~~~~~~~~~
#
#   ____                 _                   ____              _
#  / ___|  ___  __ _  __| | ___   __ _ ___  | __ )  ___   ___ | |_ _   _
#  \___ \ / _ \/ _` |/ _` |/ _ \ / _` / __| |  _ \ / _ \ / _ \| __| | | |
#   ___) |  __/ (_| | (_| | (_) | (_| \__ \ | |_) | (_) | (_) | |_| |_| |
#  |____/ \___|\__,_|\__,_|\___/ \__, |___/ |____/ \___/ \___/ \__|\__, |
#                               |___/                             |___/
#
# ==============================================================================
#
#                        NOT ALL BOOTY COMES IN A CHEST.
#
#                           github.com/SeadogsBooty
#
# ==============================================================================

import unittest, tempfile, json, io
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout
from test_bridge import b, CFG

MB='10000000-0000-4000-8000-000000000001'
A={'id':101,'artistName':'Example Artist','foreignArtistId':MB,'monitored':True,'tags':[]}
C=[{'name':'Example Artist','id':'20001','followers':233},{'name':'Example Artist','id':'20002','followers':4800000},{'name':'Example Artist','id':'20003','followers':12}]
SEARCH={'data':{'source':'deezer','artists':C}}
class Matching(unittest.TestCase):
 def setUp(self):
  b.MB_CACHE.clear(); self.addCleanup(b.MB_CACHE.clear); b.MB_FAILURES.clear(); self.addCleanup(b.MB_FAILURES.clear)
  # No network in tests; tests exercising request handling override this mock.
  req=patch.object(b,"request",return_value=(503,{})); req.start(); self.addCleanup(req.stop)
  sleep=patch.object(b.time,"sleep"); sleep.start(); self.addCleanup(sleep.stop)
  self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
  self.base=patch.object(b,'BASE',Path(self.tmp.name)); self.base.start(); self.addCleanup(self.base.stop)
 def test_musicbrainz_links_parsed(self):
  body={'id':MB,'relations':[{'url':{'resource':'https://www.deezer.com/us/artist/20002'}},{'url':{'resource':'https://www.deezer.com/artist/20001'}},{'url':{'resource':'https://evil.example/artist/9'}},{'ended':True,'url':{'resource':'https://www.deezer.com/artist/88'}}]}
  with patch.object(b,'request',return_value=(200,body)) as req,patch.object(b.time,'sleep'):
   self.assertEqual(b.linked_ids(MB,'deezer')[0],{'20002','20001'}); self.assertNotIn('Authorization',req.call_args.args[1]); self.assertIn('url-rels',req.call_args.args[3])
 def test_three_synthetic_examples(self):
  cases=[('Example Artist',C,{'20002','20001'},'20002'),('Example DJ',[{'name':'Example DJ','id':'20004','followers':2200000},{'name':'Example DJ','id':'20005','followers':1}],{'20004'},'20004'),('Example Producer',[{'name':'Example Producer','id':'20006','followers':4100000},{'name':'Example Producer','id':'20007','followers':11000},{'name':'Example Producer','id':'20008','followers':122}],{'20006','20007'},'20006')]
  for name,candidates,links,expected in cases:
   with self.subTest(name=name),patch.object(b,'ss_data',return_value={'data':{'source':'deezer','artists':candidates}}),patch.object(b,'linked_ids',return_value=(links,'links')),redirect_stdout(io.StringIO()) as out:
    self.assertEqual(b.process(CFG,dict(A,artistName=name),[],False),'new'); self.assertIn('WOULD ADD: '+name+' (deezer:'+expected+')',out.getvalue())
 def test_no_links_no_popularity_guess(self):
  with patch.object(b,'ss_data',return_value=SEARCH),patch.object(b,'linked_ids',return_value=(set(),'no links')):
   self.assertEqual(b.process(CFG,A,[],True),'review')
   row=json.loads((b.BASE/'activity.jsonl').read_text()); self.assertEqual(row['status'],'review'); self.assertIn('deezer:20002',row['candidates'])
 def test_close_linked_profiles_review(self):
  candidates=[dict(C[0],followers=40000),dict(C[1],followers=50000)]
  with patch.object(b,'ss_data',return_value={'data':{'source':'deezer','artists':candidates}}),patch.object(b,'linked_ids',return_value=({'20002','20001'},'links')):
   self.assertEqual(b.process(CFG,A,[],False),'review')
 def test_existing_alternate_linked_catalog(self):
  with patch.object(b,'ss_data',return_value=SEARCH),patch.object(b,'linked_ids',return_value=({'20002','20001'},'links')):
   self.assertEqual(b.process(CFG,A,[{'deezer_artist_id':'20001','artist_name':'Example Artist'}],True),'existing')
 def test_manual_choice_without_links(self):
  with patch.object(b,'ss_data',return_value=SEARCH),patch.object(b,'linked_ids',return_value=(set(),'no links')):
   self.assertEqual(b.process(CFG,A,[],False,'deezer:20002'),'new')
 def test_manual_conflict_rejected(self):
  with patch.object(b,'ss_data',return_value=SEARCH),patch.object(b,'linked_ids',return_value=({'20002'},'links')):
   self.assertEqual(b.process(CFG,A,[],False,'deezer:20003'),'review')
 def test_review_resolved_after_retry(self):
  b.record(CFG,A,'review','ambiguous',['deezer:20002']); b.record(CFG,A,'added','verified')
  with redirect_stdout(io.StringIO()) as out: b.show_review(CFG)
  self.assertIn('0 unresolved',out.getvalue()); self.assertEqual((b.BASE/'activity.jsonl').stat().st_mode&0o777,0o600)
 def test_503_returns_no_links(self):
  with patch.object(b,'request',return_value=(503,{})),patch.object(b.time,'sleep'):
   ids,detail=b.linked_ids(MB,'deezer'); self.assertFalse(ids); self.assertIn('503',detail)
 def test_single_artist_preview_and_apply(self):
  with patch.object(b,'config',return_value=dict(CFG,SYNC_MODE='future')),patch.object(b,'lidarr',return_value=[A]),patch.object(b,'watchlist',return_value=[]),patch.object(b,'process',return_value='new') as proc,patch('sys.argv',['bridge','--artist','101']):
   self.assertEqual(b.main(),0); self.assertFalse(proc.call_args.args[3])
  with patch.object(b,'config',return_value=dict(CFG,SYNC_MODE='future')),patch.object(b,'lidarr',return_value=[A]),patch.object(b,'watchlist',return_value=[]),patch.object(b,'process',return_value='added') as proc,patch('sys.argv',['bridge','--artist','101','--apply']):
   self.assertEqual(b.main(),0); self.assertTrue(proc.call_args.args[3])
if __name__=='__main__': unittest.main()
