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

import unittest
from pathlib import Path
from unittest.mock import Mock
import connect

SCRIPT = Path(__file__).parent / 'lidarr-to-soulsync.py'
CFG = {'SYNC_MODE':'both','LIDARR_URL':'http://lidarr','LIDARR_API_KEY':'fake'}
SCHEMA = {'implementation':'CustomScript','configContract':'CustomScriptSettings','supportsOnArtistAdd':True,'onArtistAdd':False,'onGrab':True,'onReleaseImport':True,'fields':[{'name':'path','value':''},{'name':'arguments','value':'old'}]}
SAVED = {'id':9,'name':'SoulSync','implementation':'CustomScript','onArtistAdd':True,'onGrab':False,'onReleaseImport':False,'tags':[],'fields':[{'name':'path','value':str(SCRIPT.resolve())},{'name':'arguments','value':''}]}

class ConnectionTests(unittest.TestCase):
    def bridge(self, rows):
        b=Mock(); b.lidarr.side_effect=rows; b.request.side_effect=[(200,{}),(201,{'id':9})]; return b
    def test_preview(self):
        b=self.bridge([[],[SCHEMA]])
        self.assertEqual(connect.configure(b,CFG,SCRIPT),'preview'); b.request.assert_not_called()
    def test_bulk(self):
        b=self.bridge([])
        self.assertEqual(connect.configure(b,dict(CFG,SYNC_MODE='bulk'),SCRIPT,True),'bulk'); b.lidarr.assert_not_called(); b.request.assert_not_called()
    def test_existing(self):
        b=self.bridge([[SAVED]])
        self.assertEqual(connect.configure(b,CFG,SCRIPT,True),'existing'); b.request.assert_not_called()
    def test_conflict(self):
        b=self.bridge([[dict(SAVED,name='Old SoulSync',fields=[{'name':'path','value':'/opt/old.py'}])]])
        self.assertEqual(connect.configure(b,CFG,SCRIPT,True),'conflict'); b.request.assert_not_called()
    def test_create(self):
        b=self.bridge([[],[SCHEMA],[],[SAVED]])
        self.assertEqual(connect.configure(b,CFG,SCRIPT,True),'created')
        calls=b.request.call_args_list
        self.assertEqual([c.args[3] for c in calls],['/api/v1/notification/test','/api/v1/notification'])
        payload=calls[1].args[4]; self.assertEqual(payload['name'],'SoulSync'); self.assertTrue(payload['onArtistAdd']); self.assertFalse(payload['onGrab']); self.assertFalse(payload['onReleaseImport']); self.assertEqual(payload['tags'],[]); self.assertEqual(connect.field(payload,'path'),str(SCRIPT.resolve())); self.assertEqual(connect.field(payload,'arguments'),'')
    def test_failed_test(self):
        b=self.bridge([[],[SCHEMA]]); b.request.side_effect=None; b.request.return_value=(400,{})
        b.check.side_effect=RuntimeError('test failed')
        with self.assertRaisesRegex(RuntimeError,'test failed'): connect.configure(b,CFG,SCRIPT,True)
        self.assertEqual(b.request.call_count,1)
    def test_concurrent_existing(self):
        b=self.bridge([[],[SCHEMA],[SAVED]])
        self.assertEqual(connect.configure(b,CFG,SCRIPT,True),'existing'); self.assertEqual(b.request.call_count,1)
    def test_unsupported_schema(self):
        b=self.bridge([[],[dict(SCHEMA,supportsOnArtistAdd=False)]])
        with self.assertRaises(RuntimeError): connect.configure(b,CFG,SCRIPT,True)
        b.request.assert_not_called()
    def test_unverified_create(self):
        b=self.bridge([[],[SCHEMA],[],[]])
        with self.assertRaisesRegex(RuntimeError,'could not be verified'): connect.configure(b,CFG,SCRIPT,True)

if __name__=='__main__': unittest.main()
