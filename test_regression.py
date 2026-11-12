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

"""Generic regression fixtures; no artist-specific production rules."""
import unittest
from unittest.mock import patch
from test_bridge import b, CFG, A
from test_recovery import metadata, MB

class Regression(unittest.TestCase):
    def setUp(self):
        for attr,value in [('MB_CACHE',{}),('MB_FAILURES',{})]:
            p=patch.object(b,attr,value);p.start();self.addCleanup(p.stop)
        p=patch.object(b.time,'sleep');p.start();self.addCleanup(p.stop)
        p=patch.object(b,'record');p.start();self.addCleanup(p.stop)
        p=patch.object(b,'request',return_value=(503,{}));p.start();self.addCleanup(p.stop)
    def test_unicode_hyphen_existing(self):
        a=dict(A,artistName='Example‐Band'); row={'artist_name':'EXAMPLE-BAND','musicbrainz_artist_id':MB}
        with patch.object(b,'search_artists') as req:
            self.assertEqual(b.process(CFG,a,[row],False),'existing');req.assert_not_called()
        self.assertNotEqual(b.provider_key('spotify','ABc'),b.provider_key('spotify','abc'))
    def test_primary_identity_with_contaminated_secondary_and_duplicate(self):
        b.MB_CACHE[MB]=metadata(links=['https://open.spotify.com/artist/AbC','https://www.deezer.com/artist/123'])
        rows=[{'artist_name':'Example','source':'spotify','spotify_artist_id':'AbC'},
              {'artist_name':'Other','source':'spotify','spotify_artist_id':'Other','deezer_artist_id':'123'},
              {'artist_name':'Example','source':'deezer','deezer_artist_id':'123'}]
        with patch.object(b,'search_artists',return_value=('deezer',[])),patch.object(b,'ss_data') as write:
            self.assertEqual(b.process(CFG,A,rows,True),'existing');write.assert_not_called()
            self.assertEqual(b.linked_keys_for(MB,rows,'Example'),({('spotify','AbC'),('deezer','123')},False))
    def test_secondary_only_unrelated_not_duplicate(self):
        b.MB_CACHE[MB]=metadata(links=['https://www.deezer.com/artist/123'])
        for row in [{'artist_name':'Various Artists','source':'spotify','spotify_artist_id':'Other','deezer_artist_id':'123'},
                    {'artist_name':'Example & Another','source':'deezer','deezer_artist_id':'123'}]:
            with patch.object(b,'search_artists',return_value=('deezer',[{'name':'Example','id':'123'}])),patch.object(b,'ss_data') as write:
                self.assertEqual(b.process(CFG,A,[row],True),'review');write.assert_not_called()
    def test_standalone_before_popularity(self):
        b.MB_CACHE[MB]=metadata(links=['https://www.deezer.com/artist/123','https://www.deezer.com/artist/456'])
        with patch.object(b,'search_artists',return_value=('deezer',[{'name':'Example','id':'123','followers':100},{'name':'Example and Other','id':'456','followers':1000000}])):
            plan=[];self.assertEqual(b.process(CFG,A,[],False,plan=plan),'new');self.assertEqual(plan[0][1],'deezer:123')
            self.assertEqual(b.process(CFG,A,[],False,manual='deezer:456'),'review')
    def test_cold_and_warm_cache_same_verified_id(self):
        data=metadata(links=['https://www.deezer.com/artist/123'])
        with patch.object(b,'request',return_value=(200,data)) as req,patch.object(b,'search_artists',return_value=('deezer',[{'name':'Example','id':'999'},{'name':'Alternate','id':'123'}])):
            for _ in range(2):
                plan=[];self.assertEqual(b.process(CFG,A,[],False,plan=plan),'new');self.assertEqual(plan[0][1],'deezer:123')
            self.assertEqual(req.call_count,1)
    def test_exact_name_outage_deferred_not_added(self):
        with patch.object(b,'search_artists',return_value=('deezer',[{'name':'Example','id':'123'}])),patch.object(b,'ss_data') as write:
            self.assertEqual(b.process(CFG,A,[],True),'review');write.assert_not_called()
            self.assertEqual(b.record.call_args.args[2],'deferred')
    def test_reverse_retry(self):
        other='11111111-2222-3333-4444-555555555555'
        b.MB_CACHE[other]=dict(metadata('Other',['https://open.spotify.com/artist/Other1']),id=other)
        row={'artist_name':'Other','source':'spotify','spotify_artist_id':'Other1'}
        response={'resource':'https://open.spotify.com/artist/Other1','relations':[{'artist':{'id':other}}]}
        with patch.object(b,'request',side_effect=[(503,{}),(429,{}),(200,response)]) as req:
            self.assertTrue(b.recover_owner_identity(row,MB,{('deezer','123')}));self.assertEqual(req.call_count,3)
    def test_fresh_alias_and_post_add_verification(self):
        b.MB_CACHE[MB]=metadata('Canonical',['https://www.deezer.com/artist/123'],['Alias'])
        row={'artist_name':'Canonical','source':'deezer','deezer_artist_id':'123'}
        with patch.object(b,'search_artists',return_value=('deezer',[{'name':'Canonical','id':'123'}])),patch.object(b,'watchlist',side_effect=[[],[row]]),patch.object(b,'ss_data',return_value={'success':True}) as write:
            self.assertEqual(b.process(CFG,A,[],True),'added');self.assertEqual(write.call_count,1)
        with patch.object(b,'search_artists',return_value=('deezer',[{'name':'Canonical','id':'123'}])),patch.object(b,'watchlist',return_value=[row]),patch.object(b,'ss_data') as write:
            self.assertEqual(b.process(CFG,A,[],True),'existing');write.assert_not_called()
    def test_bulk_order_does_not_change_identity(self):
        other='11111111-2222-3333-4444-555555555555'
        data={MB:metadata(links=['https://www.deezer.com/artist/123']),other:dict(metadata('Other',['https://www.deezer.com/artist/456']),id=other)}
        artists=[A,dict(A,id=2,artistName='Other',foreignArtistId=other)]
        def request(url,headers,method,path):
            mid=path.split('/artist/')[1].split('?')[0];return 200,data[mid]
        def search(cfg,name,limit=10):
            return 'deezer',[{'name':name,'id':'999'},{'name':name+' Alternate','id':'123' if name=='Example' else '456'}]
        with patch.object(b,'request',side_effect=request),patch.object(b,'search_artists',side_effect=search):
            for order in (artists,list(reversed(artists))):
                b.MB_CACHE.clear();plan=[]
                for a in order: self.assertEqual(b.process(CFG,a,[],False,plan=plan),'new')
                self.assertEqual({a['artistName']:pid for a,pid in plan},{'Example':'deezer:123','Other':'deezer:456'})
    def test_owner_retry_exhaustion_explained_and_deferred(self):
        other='11111111-2222-3333-4444-555555555555'
        b.MB_CACHE[MB]=metadata(links=['https://www.deezer.com/artist/123','https://open.spotify.com/artist/Target1'])
        b.MB_CACHE[other]=dict(metadata('Wrong'),id=other)
        row={'artist_name':'Other','source':'spotify','spotify_artist_id':'Other1','deezer_artist_id':'456','musicbrainz_artist_id':MB+', '+other}
        with patch.object(b,'search_artists',return_value=('deezer',[{'name':'Example','id':'123'}])),patch.object(b,'ss_data') as write:
            self.assertEqual(b.process(CFG,A,[row],True),'review');write.assert_not_called()
            self.assertEqual(b.record.call_args.args[2],'deferred')
            self.assertIn('MusicBrainz owner lookup for Other: HTTP 503',b.record.call_args.args[3])
