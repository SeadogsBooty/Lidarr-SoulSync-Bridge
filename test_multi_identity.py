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
from unittest.mock import patch
from test_bridge import b, CFG

AFRO = '10000000-0000-4000-8000-000000000002'
ALAN = '10000000-0000-4000-8000-000000000003'
SHARED = '10000000-0000-4000-8000-000000000004'
EXTRA = '10000000-0000-4000-8000-000000000005'
ROWS = [
    {'artist_name':'EXAMPLE DJ','source':'spotify','deezer_artist_id':'20009',
     'musicbrainz_artist_id':f'{AFRO}, {SHARED}, {EXTRA}', 'include_albums':False},
    {'artist_name':'Example Producer','source':'spotify','deezer_artist_id':'20010',
     'musicbrainz_artist_id':f'{ALAN}, {SHARED}, 10000000-0000-4000-8000-000000000006, 10000000-0000-4000-8000-000000000007'},
]

def artist(name, mid):
    return {'id':1,'artistName':name,'foreignArtistId':mid,'monitored':True}

def search(name, source='deezer', pid='999'):
    return {'data':{'source':source,'artists':[{'name':name,'id':pid}]}}

class MultiIdentity(unittest.TestCase):
    def setUp(self):
        self.rec=patch.object(b,'record'); self.rec.start(); self.addCleanup(self.rec.stop)
        self.mb=patch.object(b,"mb_metadata",return_value=({},"no links")); self.mb.start(); self.addCleanup(self.mb.stop)
    def test_parse_valid_ids(self):
        self.assertEqual(b.musicbrainz_ids(f' {AFRO.upper()}, {SHARED}, nonsense, {AFRO}, '), {AFRO,SHARED})
        self.assertEqual(b.musicbrainz_ids([AFRO,SHARED]),{AFRO,SHARED})
        self.assertEqual(b.musicbrainz_ids(None),set())
    def test_synthetic_examples_skip_without_search_or_write(self):
        with patch.object(b,'ss_data') as req:
            for name,mid in [('Example DJ',AFRO),('Example Producer',ALAN)]:
                self.assertEqual(b.process(CFG,artist(name,mid),ROWS,False),'existing')
                self.assertEqual(b.process(CFG,artist(name,mid),ROWS,True),'existing')
            req.assert_not_called()
        self.assertFalse(ROWS[0]['include_albums'])
    def test_shared_id_requires_review(self):
        with patch.object(b,'ss_data',return_value=search('Unrelated')) as req:
            self.assertEqual(b.process(CFG,artist('Unrelated',SHARED),ROWS,True),'review')
            self.assertEqual(req.call_count,1)
    def test_multi_id_different_name_requires_review(self):
        with patch.object(b,'ss_data',return_value=search('Different')) as req:
            self.assertEqual(b.process(CFG,artist('Different',EXTRA),ROWS,True),'review')
            self.assertEqual(req.call_count,1)
    def test_shared_id_even_with_name_requires_corroboration(self):
        self.assertFalse(b.verified_mbid(ROWS,SHARED,'Example DJ'))
        self.assertTrue(b.verified_keys(ROWS,{('deezer','20009')},'Example DJ'))
    def test_fresh_multi_id_no_write(self):
        with patch.object(b,'ss_data',return_value=search('Example DJ')) as req, patch.object(b,'watchlist',return_value=ROWS.copy()):
            self.assertEqual(b.process(CFG,artist('Example DJ',AFRO),[],True),'existing')
            self.assertEqual(req.call_count,1)
    def test_fresh_shared_id_no_write(self):
        with patch.object(b,'ss_data',return_value=search('Unrelated')) as req, patch.object(b,'watchlist',return_value=ROWS.copy()):
            self.assertEqual(b.process(CFG,artist('Unrelated',SHARED),[],True),'review')
            self.assertEqual(req.call_count,1)
    def test_musicbrainz_provider_does_not_bypass_shared_id(self):
        with patch.object(b,'ss_data',return_value=search('Unrelated','musicbrainz',SHARED)) as req:
            self.assertEqual(b.process(CFG,artist('Unrelated',SHARED),ROWS,True),'review')
            self.assertEqual(req.call_count,1)
