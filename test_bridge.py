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

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).parent
spec=importlib.util.spec_from_file_location('bridge',ROOT/'lidarr-to-soulsync.py')
b=importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
ss=importlib.util.spec_from_file_location('setup_wizard',ROOT/'setup.py')
w=importlib.util.module_from_spec(ss); ss.loader.exec_module(w)
CFG={'SOULSYNC_PROFILE_ID':'2','SYNC_MODE':'both','ARTIST_SCOPE':'all','LIDARR_URL':'http://lidarr','LIDARR_API_KEY':'fake','SOULSYNC_URL':'http://ss','SOULSYNC_API_KEY':'fake'}
A={'id':1,'artistName':'Example','foreignArtistId':'12345678-1234-1234-1234-123456789abc','monitored':True,'tags':[]}
ROW={'profile_id':2,'artist_name':'Example','deezer_artist_id':'123','musicbrainz_artist_id':'12345678-1234-1234-1234-123456789abc','include_albums':False}
SEARCH={'success':True,'data':{'source':'deezer','artists':[{'name':'Example','id':123}]}}
def _fake_save(path,cfg):
 path.write_text("".join(f"{k}={v}\n" for k,v in cfg.items())); path.chmod(0o600)

class Tests(unittest.TestCase):
 def setUp(self):
  logger=patch.object(b,"record"); logger.start(); self.addCleanup(logger.stop)
  mb=patch.object(b,"mb_metadata",return_value=({},"no links")); mb.start(); self.addCleanup(mb.stop)
 def test_existing_mbid_no_requests(self):
  with patch.object(b,'ss_data') as req:
   self.assertEqual(b.process(CFG,A,[ROW.copy()],True),'existing'); req.assert_not_called()
 def test_existing_provider_no_write(self):
  row=dict(ROW,musicbrainz_artist_id=None)
  with patch.object(b,'ss_data',return_value=SEARCH) as req:
   self.assertEqual(b.process(CFG,A,[row],True),'existing'); self.assertEqual(req.call_count,1)
 def test_preview(self):
  with patch.object(b,'ss_data',return_value=SEARCH) as req:
   self.assertEqual(b.process(CFG,A,[],False),'new'); self.assertEqual(req.call_count,1)
 def test_add_then_skip(self):
  rows=[]
  with patch.object(b,'ss_data',side_effect=[SEARCH,{'success':True}]) as req,patch.object(b,'watchlist',side_effect=[[],[ROW.copy()]]):
   self.assertEqual(b.process(CFG,A,rows,True),'added'); self.assertEqual(b.process(CFG,A,rows,True),'existing'); self.assertEqual(req.call_count,2); self.assertEqual(rows[0]['include_albums'],False)
 def test_ambiguous(self):
  with patch.object(b,'ss_data',return_value={'data':{'source':'deezer','artists':[{'name':'Example','id':1},{'name':'Example','id':2}]}}) as req:
   self.assertEqual(b.process(CFG,A,[],True),'review'); self.assertEqual(req.call_count,1)
 def test_name_conflict(self):
  with patch.object(b,'ss_data',return_value=SEARCH) as req:
   self.assertEqual(b.process(CFG,A,[dict(ROW,deezer_artist_id='999',musicbrainz_artist_id=None)],True),'review'); self.assertEqual(req.call_count,1)
 def test_fresh_duplicate(self):
  with patch.object(b,'ss_data',return_value=SEARCH) as req,patch.object(b,'watchlist',return_value=[ROW.copy()]):
   self.assertEqual(b.process(CFG,A,[],True),'existing'); self.assertEqual(req.call_count,1)
 def test_watchlist_wrong_profile(self):
  with patch.object(b,'ss_data',return_value={'data':{'artists':[dict(ROW,profile_id=1)]}}):
   with self.assertRaises(RuntimeError): b.watchlist(CFG)
 def test_503(self):
  with self.assertRaisesRegex(RuntimeError,'503.*Service unavailable'): b.check(503,{},'SoulSync')
 def test_scope(self):
  self.assertTrue(b.eligible(CFG,dict(A,monitored=False),{})); self.assertFalse(b.eligible(dict(CFG,ARTIST_SCOPE='monitored'),dict(A,monitored=False),{})); self.assertFalse(b.eligible(dict(CFG,REQUIRE_TAG='test'),A,{'1':'test'}))
 def test_modes(self):
  with patch.object(b,'config',return_value=dict(CFG,SYNC_MODE='future')),patch('sys.argv',['bridge','--bulk']): self.assertEqual(b.main(),1)
  with patch.object(b,'config',return_value=dict(CFG,SYNC_MODE='bulk')),patch.object(b,'env',return_value='ArtistAdd'),patch('sys.argv',['bridge']): self.assertEqual(b.main(),0)
 def test_wizard(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'config.env'
   with patch.object(w,'CONFIG',path),patch.object(w,'BASE',Path(tmp)),patch.object(w.install,'destination',return_value=Path(tmp)),patch.object(w.install,'save',side_effect=lambda source,target,cfg: _fake_save(path,cfg)),patch('sys.argv',['setup.py']),patch.object(w,'register',return_value=0),patch.object(w,'initial_import',return_value=0),patch.object(w.sys.stdin,'isatty',return_value=True),patch.object(w,'url',side_effect=['http://lidarr','http://ss']),patch.object(w,'ask',side_effect=['fake-l','fake-s','2','3','2','no','yes']),patch.object(w.bridge,'lidarr',return_value=[A]),patch.object(w.bridge,'profiles',return_value=[{'id':1,'name':'Main'},{'id':2,'name':'Test'}]),patch.object(w.bridge,'watchlist',return_value=[]),patch.object(w.bridge,'ss_data',return_value=SEARCH):
    self.assertEqual(w.main(),0); self.assertIn('SYNC_MODE=both',path.read_text()); self.assertIn('SOULSYNC_PROFILE_ID=2',path.read_text()); self.assertEqual(path.stat().st_mode&0o777,0o600); self.assertEqual(w.main(),1)
 def test_wizard_failure(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'config.env'
   with patch.object(w,'CONFIG',path),patch.object(w,'BASE',Path(tmp)),patch.object(w.install,'destination',return_value=Path(tmp)),patch.object(w.install,'save',side_effect=lambda source,target,cfg: _fake_save(path,cfg)),patch('sys.argv',['setup.py']),patch.object(w,'register',return_value=0),patch.object(w.sys.stdin,'isatty',return_value=True),patch.object(w,'url',side_effect=['http://lidarr','http://ss']),patch.object(w,'ask',side_effect=['fake-l','fake-s']),patch.object(w.bridge,'lidarr',return_value=[A]),patch.object(w.bridge,'profiles',side_effect=RuntimeError('SoulSync: HTTP 503')):
    self.assertEqual(w.main(),1); self.assertFalse(path.exists())
 def test_wizard_rejects_remote_profile_config_injection(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'config.env'
   malicious={'id':'2\x85LIDARR_URL=https://collector.example','name':'Example profile'}
   with patch.object(w,'CONFIG',path),patch.object(w,'BASE',Path(tmp)),patch.object(w.install,'destination',return_value=Path(tmp)),patch.object(w.install,'save') as save,patch('sys.argv',['setup.py']),patch.object(w.sys.stdin,'isatty',return_value=True),patch.object(w,'url',side_effect=['http://lidarr','http://ss']),patch.object(w,'ask',side_effect=['fake-l','fake-s']),patch.object(w.bridge,'lidarr',return_value=[A]),patch.object(w.bridge,'profiles',return_value=[malicious]),patch.object(w.bridge,'watchlist') as watchlist:
    self.assertEqual(w.main(),1)
    save.assert_not_called(); watchlist.assert_not_called(); self.assertFalse(path.exists())
 def test_soulsync_default_address(self):
  with patch('builtins.input', return_value='') as prompt:
   self.assertEqual(w.url('SoulSync address','http://localhost:8008'),'http://localhost:8008')
   prompt.assert_called_once_with('SoulSync address [http://localhost:8008]: ')
if __name__=='__main__': unittest.main()
