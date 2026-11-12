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

import io, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout
from test_bridge import b, CFG, A, ROW

MB=A['foreignArtistId']

def search(source, candidates):
    return {'data':{'source':source,'artists':candidates}}

def metadata(name='Example', links=(), aliases=()):
    return {'id':MB,'name':name,'aliases':[{'name':n} for n in aliases], 'relations':[{'url':{'resource':u}} for u in links]}

class Recovery(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        for obj,name,value in [(b,'BASE',Path(self.tmp.name)),(b,'MB_CACHE',{}),(b,'MB_FAILURES',{}),(b.time,'sleep',None),(b,'request',None)]:
            p=patch.object(obj,name,value) if value is not None else patch.object(obj,name,return_value=(503,{})) if name=='request' else patch.object(obj,name)
            p.start(); self.addCleanup(p.stop)
    def test_all_sources_write_and_verify(self):
        b.MB_CACHE[MB]=metadata()  # successful lookup, no provider links; exact-name fallback
        for source,pid in [('deezer','123'),('spotify','AbC123'),('itunes','456'),('discogs','789'),('amazon','B00ABC'),('musicbrainz',MB)]:
            with self.subTest(source=source):
                row={'artist_name':'Example','profile_id':2,source+'_artist_id':pid}
                with patch.object(b,'ss_data',side_effect=[search(source,[{'name':'Example','id':pid}]),{'success':True}]) as req,patch.object(b,'watchlist',side_effect=[[],[row]]):
                    self.assertEqual(b.process(CFG,A,[],True),'added')
                    self.assertEqual(req.call_args.args[3],{'artist_id':pid,'artist_name':'Example','source':source})
    def test_unknown_provider_fails_closed(self):
        with patch.object(b,'ss_data',return_value=search('new-provider',[{'name':'Example','id':'1'}])) as req:
            with self.assertRaisesRegex(RuntimeError,'unsupported artist-search provider'): b.process(CFG,A,[],True)
            self.assertEqual(req.call_count,1)
    def test_cross_provider_verified(self):
        existing={'artist_name':'Example','spotify_artist_id':'AbC123','deezer_artist_id':'999','include_albums':False}
        b.MB_CACHE[MB]=metadata(links=['https://open.spotify.com/artist/AbC123','https://www.deezer.com/artist/123'])
        with patch.object(b,'ss_data',return_value=search('deezer',[{'name':'Example','id':'123'}])) as req:
            self.assertEqual(b.process(CFG,A,[existing],True),'existing'); self.assertEqual(req.call_count,1); self.assertFalse(existing['include_albums'])
    def test_cross_provider_alias(self):
        b.MB_CACHE[MB]=metadata('Example',['https://open.spotify.com/artist/AbC123'],['Old Name'])
        with patch.object(b,'ss_data',return_value=search('deezer',[{'name':'Example','id':'123'}])):
            self.assertEqual(b.process(CFG,A,[{'artist_name':'Old Name','spotify_artist_id':'AbC123'}],False),'existing')
    def test_alias_search_verified(self):
        b.MB_CACHE[MB]=metadata('Canonical',['https://www.deezer.com/artist/123'],['Alternate'])
        with patch.object(b,'ss_data',side_effect=[search('deezer',[{'name':'Example','id':'999'},{'name':'Example','id':'998'}]),search('deezer',[{'name':'Canonical','id':'123'}])]) as req:
            plan=[]; self.assertEqual(b.process(CFG,A,[],False,plan=plan),'new'); self.assertEqual(plan[0][1],'deezer:123'); self.assertEqual(req.call_args.args[3]['query'],'Canonical')
    def test_nonexact_candidate_verified_link(self):
        b.MB_CACHE[MB]=metadata('Canonical',['https://www.deezer.com/artist/123'])
        with patch.object(b,'ss_data',return_value=search('deezer',[{'name':'Canonical','id':'123'}])):
            self.assertEqual(b.process(CFG,A,[],False),'new')
    def test_nonexact_musicbrainz_match(self):
        with patch.object(b,'ss_data',return_value=search('musicbrainz',[{'name':'Canonical','id':MB}])):
            self.assertEqual(b.process(CFG,A,[],False),'new')
    def test_conflicting_link_not_added(self):
        b.MB_CACHE[MB]=metadata('Example',['https://www.deezer.com/artist/123'])
        with patch.object(b,'ss_data',return_value=search('deezer',[{'name':'Example','id':'999'}])):
            self.assertEqual(b.process(CFG,A,[],False),'review')
    def test_retry_then_cache(self):
        with patch.object(b,'request',side_effect=[(503,{}),(429,{}),(200,metadata(links=['https://open.spotify.com/artist/AbC123']))]) as req:
            self.assertEqual(b.linked_ids(MB,'spotify')[0],{'AbC123'}); self.assertEqual(b.linked_ids(MB,'spotify')[0],{'AbC123'}); self.assertEqual(req.call_count,3)
    def test_deferred(self):
        with patch.object(b,'ss_data',return_value=search('deezer',[{'name':'Example','id':'1'},{'name':'Example','id':'2'}])):
            self.assertEqual(b.process(CFG,A,[],True),'review'); row=json.loads((b.BASE/'activity.jsonl').read_text()); self.assertEqual(row['status'],'deferred'); self.assertIn('MusicBrainz HTTP 503',row['detail'])
    def test_retry_by_name_and_current_id(self):
        with patch.object(b,'config',return_value=CFG),patch.object(b,'lidarr',return_value=[dict(A,id=99)]),patch.object(b,'watchlist',return_value=[]),patch.object(b,'process',return_value='new') as proc,patch('sys.argv',['bridge','--artist-name','example']):
            self.assertEqual(b.main(),0); self.assertEqual(proc.call_args.args[1]['id'],99); self.assertFalse(proc.call_args.args[3])
    def test_retry_all_tracks_new_id(self):
        b.record(CFG,A,'review','ambiguous');
        with patch.object(b,'config',return_value=CFG),patch.object(b,'lidarr',return_value=[dict(A,id=99)]),patch.object(b,'watchlist',return_value=[]),patch.object(b,'process',return_value='new') as proc,patch('sys.argv',['bridge','--retry-all']):
            self.assertEqual(b.main(),0); self.assertEqual(proc.call_args.args[1]['id'],99); self.assertFalse(proc.call_args.args[3])
        b.record(CFG,dict(A,id=99),'added','verified'); self.assertEqual(b.pending_reviews(CFG),[])
    def test_select_confirmed_only(self):
        artists=[A,dict(A,id=2,artistName='Other',foreignArtistId='')]
        def process(cfg,a,rows,apply,manual=None,plan=None):
            if not apply:
                plan.append((a,'deezer:'+str(a['id']))); return 'new'
            self.assertEqual(a['id'],2); self.assertEqual(manual,'deezer:2'); return 'added'
        with patch.object(b,'config',return_value=CFG),patch.object(b,'lidarr',return_value=artists),patch.object(b,'watchlist',return_value=[]),patch.object(b,'process',side_effect=process) as proc,patch('sys.argv',['bridge','--bulk','--select']),patch.object(b.sys.stdin,'isatty',return_value=True),patch('builtins.input',side_effect=['2','yes']):
            self.assertEqual(b.main(),0); self.assertEqual(proc.call_count,3)
    def test_select_cancel_no_write(self):
        def process(cfg,a,rows,apply,manual=None,plan=None):
            self.assertFalse(apply); plan.append((a,'deezer:1')); return 'new'
        with patch.object(b,'config',return_value=CFG),patch.object(b,'lidarr',return_value=[A]),patch.object(b,'watchlist',return_value=[]),patch.object(b,'process',side_effect=process) as proc,patch('sys.argv',['bridge','--bulk','--select']),patch.object(b.sys.stdin,'isatty',return_value=True),patch('builtins.input',side_effect=['1','no']):
            self.assertEqual(b.main(),0); self.assertEqual(proc.call_count,1)
    def test_conflicting_cross_provider_owners_review(self):
        b.MB_CACHE[MB]=metadata('Example',['https://open.spotify.com/artist/AbC123','https://www.deezer.com/artist/123'])
        rows=[{'artist_name':'Wrong Name','spotify_artist_id':'AbC123'}]
        with patch.object(b,'ss_data',return_value=search('deezer',[{'name':'Example','id':'123'}])) as req:
            self.assertEqual(b.process(CFG,A,rows,True),'review'); self.assertEqual(req.call_count,1)
    def test_legacy_history_clears_after_retry(self):
        (b.BASE/'activity.jsonl').write_text(json.dumps({'profile':'2','lidarr_id':'1','artist':'Example','status':'review','detail':'old','candidates':[]})+'\n')
        b.record(CFG,A,'added','verified'); self.assertEqual(b.pending_reviews(CFG),[])
    def test_source_change_alias_query_does_not_use_wrong_namespace(self):
        b.MB_CACHE[MB]=metadata('Canonical',['https://www.deezer.com/artist/123'])
        with patch.object(b,'ss_data',side_effect=[search('deezer',[]),search('spotify',[{'name':'Canonical','id':'123'}])]):
            self.assertEqual(b.process(CFG,A,[],False),'review')
