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
from test_bridge import b,CFG,A
from test_recovery import metadata,search,MB

OTHER='11111111-2222-3333-4444-555555555555'
EXTRA='11111111-2222-3333-4444-666666666666'
class GlobalMatching(unittest.TestCase):
    def setUp(self):
        for name,value in [('MB_CACHE',{}),('MB_FAILURES',{}),('record',None),('request',None)]:
            p=patch.object(b,name,value) if value is not None else patch.object(b,name,return_value=(503,{}))
            p.start(); self.addCleanup(p.stop)
    def test_direct_deezer_alias_and_zero_albums(self):
        for name,display,pid,count in [('Original Name','Translated Name','123',262),('Project','Project','456',0)]:
            with self.subTest(name=name):
                b.MB_CACHE[MB]=metadata(name,['https://www.deezer.com/artist/'+pid],[display])
                with patch.object(b,'search_artists',return_value=('deezer',[])),patch.object(b,'request',return_value=(200,{'id':int(pid),'name':display,'nb_album':count})) as req:
                    plan=[]; self.assertEqual(b.process(CFG,dict(A,artistName=name),[],False,plan=plan),'new'); self.assertEqual(plan[0][1],'deezer:'+pid)
                    self.assertEqual(req.call_args.args[0],'https://api.deezer.com'); self.assertNotIn('Authorization',req.call_args.args[1])
    def test_direct_itunes(self):
        b.MB_CACHE[MB]=metadata(links=['https://music.apple.com/us/artist/example/123'])
        with patch.object(b,'search_artists',return_value=('itunes',[])),patch.object(b,'request',return_value=(200,{'results':[{'wrapperType':'artist','artistId':123,'artistName':'Example'}]})):
            self.assertEqual(b.process(CFG,A,[],False),'new')
    def test_direct_musicbrainz(self):
        b.MB_CACHE[MB]=metadata()
        with patch.object(b,'search_artists',return_value=('musicbrainz',[])):
            self.assertEqual(b.process(CFG,A,[],False),'new')
    def test_direct_wrong_name_or_id_or_error_rejected(self):
        b.MB_CACHE[MB]=metadata(links=['https://www.deezer.com/artist/123'])
        for body in [{'id':123,'name':'Wrong'},{'id':999,'name':'Example'},{'id':123,'name':'Example','error':{'code':1}}]:
            with patch.object(b,'search_artists',return_value=('deezer',[])),patch.object(b,'request',return_value=(200,body)):
                self.assertEqual(b.process(CFG,A,[],False),'review')
    def test_no_implicit_provider_switch(self):
        b.MB_CACHE[MB]=metadata(links=['https://www.deezer.com/artist/123','https://open.spotify.com/artist/AbC123'])
        with patch.object(b,'search_artists',return_value=('spotify',[])),patch.object(b,'request') as req:
            self.assertEqual(b.process(CFG,A,[],False),'review'); req.assert_not_called()
    def test_multiple_unseen_catalogs_not_guessed(self):
        b.MB_CACHE[MB]=metadata(links=['https://www.deezer.com/artist/123','https://www.deezer.com/artist/456'])
        with patch.object(b,'search_artists',return_value=('deezer',[])),patch.object(b,'request') as req:
            self.assertEqual(b.process(CFG,A,[],False),'review'); req.assert_not_called()
    def setup_collision(self):
        b.MB_CACHE[MB]=metadata(links=['https://www.deezer.com/artist/123','https://open.spotify.com/artist/Target1'])
        b.MB_CACHE[OTHER]=dict(metadata('Other Artist',['https://www.deezer.com/artist/456','https://open.spotify.com/artist/Other1']),id=OTHER)
        return {'artist_name':'Other Artist','musicbrainz_artist_id':MB+', '+OTHER,'deezer_artist_id':'456','spotify_artist_id':'Other1','include_albums':False}
    def test_unrelated_association_preview_and_apply(self):
        row=self.setup_collision(); new={'artist_name':'Example','deezer_artist_id':'123','musicbrainz_artist_id':MB}
        with patch.object(b,'search_artists',return_value=('deezer',[{'id':'123','name':'Example'}])),patch.object(b,'ss_data',return_value={'success':True}) as req,patch.object(b,'watchlist',side_effect=[[row],[row,new]]):
            self.assertEqual(b.process(CFG,A,[row],False),'new'); req.assert_not_called()
            self.assertEqual(b.process(CFG,A,[row],True),'added'); self.assertEqual(req.call_count,1); self.assertFalse(row['include_albums'])
            self.assertEqual(b.process(CFG,A,[row,new],False),'existing')
    def test_uncorroborated_or_overlapping_association_blocked(self):
        row=self.setup_collision()
        for bad in [dict(row,spotify_artist_id=None),dict(row,musicbrainz_artist_id=MB),dict(row,spotify_artist_id='Target1'),dict(row,musicbrainz_artist_id=MB+', '+EXTRA)]:
            with patch.object(b,'search_artists',return_value=('deezer',[{'id':'123','name':'Example'}])),patch.object(b,'ss_data') as req,patch.object(b,'mb_metadata',side_effect=lambda mid:(b.MB_CACHE.get(mid,{}),'test')):
                self.assertEqual(b.process(CFG,A,[bad],True),'review'); req.assert_not_called()
    def test_false_success_not_accepted_for_collision(self):
        row=self.setup_collision()
        with patch.object(b,'search_artists',return_value=('deezer',[{'id':'123','name':'Example'}])),patch.object(b,'ss_data',return_value={'success':True}),patch.object(b,'watchlist',side_effect=[[row],[row]]):
            with self.assertRaisesRegex(RuntimeError,'could not verify'): b.process(CFG,A,[row],True)
    def test_source_change_blocks_direct_fallback(self):
        b.MB_CACHE[MB]=metadata('Canonical',['https://www.deezer.com/artist/123'])
        with patch.object(b,'search_artists',side_effect=[('deezer',[]),('spotify',[])]),patch.object(b,'request') as req:
            self.assertEqual(b.process(CFG,A,[],False),'review'); req.assert_not_called()
    def test_no_links_no_search_is_review(self):
        b.MB_CACHE[MB]=metadata()
        with patch.object(b,'search_artists',return_value=('deezer',[])),patch.object(b,'ss_data') as req:
            self.assertEqual(b.process(CFG,A,[],True),'review'); req.assert_not_called()

class OwnerRecovery(unittest.TestCase):
    setUp=GlobalMatching.setUp
    setup_collision=GlobalMatching.setup_collision
    # Reuse fixture only; do not inherit the existing test cases below.
    def test_missing_owner_id_reverse_lookup(self):
        row=dict(self.setup_collision(),source='spotify',musicbrainz_artist_id=MB+', '+EXTRA)
        response={'resource':'https://open.spotify.com/artist/Other1','relations':[{'artist':{'id':OTHER}}]}
        with patch.object(b,'request',return_value=(200,response)),patch.object(b,'time') as clock,patch.object(b,'mb_metadata',side_effect=lambda mid:(b.MB_CACHE.get(mid,{}),'test')):
            self.assertTrue(b.unrelated_mbid_associations([row],MB,'Example',('deezer','123')))
    def test_recovery_wrong_provider_or_ambiguous_blocked(self):
        row=dict(self.setup_collision(),source='spotify',musicbrainz_artist_id=MB+', '+EXTRA)
        b.MB_CACHE[EXTRA]=dict(b.MB_CACHE[OTHER],id=EXTRA)
        for ids in [[MB],[OTHER,EXTRA],[]]:
            response={'resource':'https://open.spotify.com/artist/Other1','relations':[{'artist':{'id':i}} for i in ids]}
            with patch.object(b,'request',return_value=(200,response)),patch.object(b,'time'),patch.object(b,'mb_metadata',side_effect=lambda mid:(b.MB_CACHE.get(mid,{}),'test')):
                self.assertFalse(b.recover_owner_identity(row,MB,{('deezer','123'),('spotify','Target1')}))
    def test_owner_search_fallback(self):
        row=dict(self.setup_collision(),source='spotify',musicbrainz_artist_id=MB+', '+EXTRA)
        with patch.object(b,'request',side_effect=[(404,{}),(200,{'count':1,'artists':[{'id':OTHER}]})]),patch.object(b,'time'),patch.object(b,'mb_metadata',side_effect=lambda mid:(b.MB_CACHE.get(mid,{}),'test')):
            self.assertTrue(b.recover_owner_identity(row,MB,{('deezer','123')}))
    def test_owner_lookup_outage_blocked(self):
        row=dict(self.setup_collision(),source='spotify',musicbrainz_artist_id=MB+', '+EXTRA)
        with patch.object(b,'request',return_value=(503,{})),patch.object(b,'time'),patch.object(b,'mb_metadata',side_effect=lambda mid:(b.MB_CACHE.get(mid,{}),'test')):
            self.assertFalse(b.unrelated_mbid_associations([row],MB,'Example',('deezer','123')))

    def test_recovered_owner_preview_and_apply(self):
        row=dict(self.setup_collision(),source='spotify',musicbrainz_artist_id=MB+', '+EXTRA)
        new={'artist_name':'Example','deezer_artist_id':'123','musicbrainz_artist_id':MB}
        response={'resource':'https://open.spotify.com/artist/Other1','relations':[{'artist':{'id':OTHER}}]}
        with patch.object(b,'request',return_value=(200,response)),patch.object(b,'time'),patch.object(b,'mb_metadata',side_effect=lambda mid:(b.MB_CACHE.get(mid,{}),'test')),patch.object(b,'search_artists',return_value=('deezer',[{'id':'123','name':'Example'}])),patch.object(b,'ss_data',return_value={'success':True}) as write,patch.object(b,'watchlist',side_effect=[[row],[row,new]]):
            self.assertEqual(b.process(CFG,A,[row],False),'new'); write.assert_not_called()
            self.assertEqual(b.process(CFG,A,[row],True),'added'); self.assertEqual(write.call_count,1)
            self.assertEqual(row['musicbrainz_artist_id'],MB+', '+EXTRA)
            self.assertEqual(b.process(CFG,A,[row,new],False),'existing')
