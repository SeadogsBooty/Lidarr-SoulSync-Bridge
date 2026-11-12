#!/usr/bin/env python3
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

"""Lidarr -> SoulSync Watchlist bridge v1.1. Python 3 standard library, Linux."""
import argparse
import re
import shlex
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlencode
import fcntl
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
PROVIDERS = {'deezer', 'spotify', 'musicbrainz', 'amazon', 'itunes', 'discogs'}
LINK_PROVIDERS = ('deezer', 'spotify', 'discogs', 'itunes', 'amazon')
MB_CACHE = {}
MB_FAILURES = {}

def provider_source(value):
    source = norm(value)
    return {'apple_music':'itunes', 'apple music':'itunes', 'applemusic':'itunes'}.get(source, source)


def norm(v):
    return unicodedata.normalize('NFKC', str(v or '')).strip().casefold()


def name_key(v):
    # Unicode punctuation equivalence for names only, never provider IDs.
    return ' '.join(norm(v).translate(str.maketrans({c:'-' for c in '‐‑‒–—−'})).split())


def config():
    path = Path(os.environ.get('BRIDGE_CONFIG', str(BASE / 'config.env')))
    return dict((k.strip(), v.strip().strip('"').strip("'")) for k,v in
                (line.split('=',1) for line in path.read_text().splitlines()
                 if '=' in line and not line.lstrip().startswith('#')))


def request(url, headers, method, path, payload=None):
    headers = dict(headers)
    data = None if payload is None else json.dumps(payload).encode()
    if data is not None:
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url.rstrip('/') + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read()
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        return exc.code, {}
    except (OSError, ValueError) as exc:
        raise RuntimeError(f'{path}: connection or response failure ({type(exc).__name__}). Check service availability and network.') from None


def check(status, body, label, codes=(200,)):
    if status not in codes:
        hint = {401:'Check API key.',403:'Check API permissions.',404:'Check server address and API version.',429:'Rate limited; retry later.',503:'Service unavailable; retry after SoulSync/Lidarr recovers.'}.get(status,'Check server status and API compatibility.')
        raise RuntimeError(f'{label}: HTTP {status}. {hint}')
    return body


def ss(cfg, method, path, payload=None, profile=True):
    headers = {'Authorization': 'Bearer ' + cfg['SOULSYNC_API_KEY']}
    if profile:
        headers['X-Profile-Id'] = cfg['SOULSYNC_PROFILE_ID']
    return request(cfg['SOULSYNC_URL'], headers, method, path, payload)


def ss_data(cfg, method, path, payload=None, profile=True, codes=(200,)):
    status, body = ss(cfg, method, path, payload, profile)
    check(status, body, 'SoulSync ' + path, codes)
    if not isinstance(body, dict) or body.get('success') is not True:
        raise RuntimeError(f'SoulSync {path}: unsuccessful or unexpected API response')
    return body


def lidarr(cfg, path):
    status, body = request(cfg['LIDARR_URL'], {'X-Api-Key':cfg['LIDARR_API_KEY']}, 'GET', path)
    check(status, body, 'Lidarr ' + path)
    if path == '/api/v1/system/status':
        if not isinstance(body, dict):
            raise RuntimeError('Lidarr system status: unexpected object response')
    elif not isinstance(body, list) or any(not isinstance(a,dict) for a in body):
        raise RuntimeError('Lidarr: unexpected list response')
    return body


def profiles(cfg):
    body = ss_data(cfg,'GET','/api/v1/profiles',profile=False)
    rows = (body.get('data') or {}).get('profiles')
    if not isinstance(rows,list) or not rows or any(not isinstance(r,dict) or not r.get('id') or not r.get('name') for r in rows):
        raise RuntimeError('SoulSync: no usable profiles returned. Use a key allowed to list profiles.')
    return rows


def watchlist(cfg):
    body = ss_data(cfg,'GET','/api/v1/watchlist')
    data = body.get('data') or {}
    rows = data.get('artists')
    if not isinstance(rows,list):
        raise RuntimeError('SoulSync: unexpected watchlist response; refusing to write')
    if body.get('pagination') or data.get('pagination'):
        raise RuntimeError('SoulSync: paginated watchlist not supported; refusing to write rather than miss duplicates')
    for row in rows:
        if not isinstance(row,dict) or str(row.get('profile_id')) != str(cfg['SOULSYNC_PROFILE_ID']) or not row.get('artist_name'):
            raise RuntimeError('SoulSync: watchlist profile or artist data unexpected; refusing to write')
    return rows


def env(*names):
    return next((os.environ.get(n) or os.environ.get(n.lower()) for n in names if os.environ.get(n) or os.environ.get(n.lower())), '')


def tag_map(cfg):
    return {str(t['id']):norm(t['label']) for t in lidarr(cfg,'/api/v1/tag')} if cfg.get('REQUIRE_TAG') else {}


def eligible(cfg,a,tags):
    return (cfg.get('ARTIST_SCOPE','monitored') != 'monitored' or a.get('monitored') is True) and (not cfg.get('REQUIRE_TAG') or norm(cfg['REQUIRE_TAG']) in {tags.get(str(t)) for t in a.get('tags',[])})


def provider_key(source, value):
    return str(value or '').strip() if source in ('spotify','amazon') else norm(value)


def musicbrainz_ids(value):
    # SoulSync can return multiple comma-separated IDs, or a single UUID.
    values = value if isinstance(value, list) else [value]
    tokens = {norm(part) for item in values for part in str(item or '').split(',')}
    return {token for token in tokens
            if re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', token)}


def identities(row):
    keys = {(p,provider_key(p,row.get(p+'_artist_id'))) for p in PROVIDERS
            if p != 'musicbrainz' and provider_key(p,row.get(p+'_artist_id'))}
    return keys | {('musicbrainz', mid) for mid in musicbrainz_ids(row.get('musicbrainz_artist_id'))}


def mbid_rows(rows, mbid):
    return [r for r in rows if mbid and mbid in musicbrainz_ids(r.get('musicbrainz_artist_id'))]


def verified_mbid(rows, mbid, name):
    owners = mbid_rows(rows, mbid)
    if len(owners) != 1:
        return False
    row = owners[0]
    # Even a single stored ID can be wrong. Require name agreement and
    # uniqueness; alternate names can be corroborated by provider links.
    return name_key(row.get('artist_name')) == name_key(name)


def verified_keys(rows, keys, name):
    return any(verified_mbid(rows, value, name) if source == 'musicbrainz'
               else any((source,value) in identities(r) and name_key(r.get('artist_name')) == name_key(name) for r in rows)
               for source,value in keys)


def dominant_linked(matches):
    # Only rank independently verified profiles for the same identity.
    counts=[a.get('followers') for a in matches]
    if len(matches)<2 or any(type(n) is not int or n<0 for n in counts): return None
    ranked=sorted(matches,key=lambda a:a['followers'],reverse=True)
    top,second=ranked[:2]
    return top if top['followers']>=10000 and top['followers']>=20*max(1,second['followers']) else None


def mb_get(path):
    """Apply the same rate spacing and bounded retries to all MusicBrainz reads."""
    for delay in (1.1, 3, 6):
        time.sleep(delay)
        try:
            status, body = request('https://musicbrainz.org',
                {'User-Agent':'Lidarr-SoulSync-Watchlist-Bridge/1.1','Accept':'application/json'}, 'GET', path)
        except (RuntimeError,OSError,ValueError,TypeError,AttributeError):
            status,body=0,{}
        if status not in (0,429,500,502,503,504): return status,body
    return status,body


def mb_metadata(mbid):
    """Cache successful reads; temporary failures are never identity evidence."""
    if not musicbrainz_ids(mbid) or mbid not in musicbrainz_ids(mbid):
        return {}, 'no valid MusicBrainz ID'
    if mbid in MB_CACHE:
        return MB_CACHE[mbid], 'MusicBrainz identity verified'
    if mbid in MB_FAILURES and time.monotonic()-MB_FAILURES[mbid][0]<30:
        return {}, MB_FAILURES[mbid][1]
    status,body=mb_get('/ws/2/artist/'+mbid+'?inc=url-rels+aliases&fmt=json')
    if status in (0,429,500,502,503,504):
        detail=('MusicBrainz HTTP '+str(status)+'; temporary lookup failure after retries' if status else 'MusicBrainz connection or response unavailable after retries')
        MB_FAILURES[mbid]=(time.monotonic(),detail)
        return {},detail
    if status!=200: return {},f'MusicBrainz HTTP {status}; lookup not available'
    if not isinstance(body,dict) or norm(body.get('id'))!=mbid:
        return {},'MusicBrainz identity response did not match'
    MB_CACHE[mbid]=body
    return body,'MusicBrainz identity verified'


def linked_ids(mbid, source):
    if source == 'musicbrainz': return ({mbid} if mbid in musicbrainz_ids(mbid) else set()), 'Lidarr MusicBrainz ID'
    if source not in LINK_PROVIDERS: return set(), 'provider link lookup not supported for '+source
    body, detail = mb_metadata(mbid)
    if not body: return set(), detail
    patterns={
        'deezer':({'deezer.com','www.deezer.com'},r'/(?:[a-z]{2}/)?artist/(\d+)'),
        'spotify':({'open.spotify.com'},r'/(?:intl-[a-z-]+/)?artist/([A-Za-z0-9]+)'),
        'discogs':({'discogs.com','www.discogs.com'},r'/artist/(\d+)(?:-[^/]+)?'),
        'itunes':({'music.apple.com','itunes.apple.com'},r'/(?:[a-z]{2}/)?artist/(?:[^/]+/)?(?:id)?(\d+)'),
        'amazon':({'music.amazon.com','music.amazon.co.uk','music.amazon.de','music.amazon.co.jp','music.amazon.ca','music.amazon.fr','music.amazon.it','music.amazon.es'},r'/artists/([A-Za-z0-9]+)(?:/[^/]+)?')}
    ids=set()
    for rel in body.get('relations',[]):
        if not isinstance(rel,dict) or rel.get('ended') is True: continue
        try: u=urlsplit((rel.get('url') or {}).get('resource',''))
        except (ValueError,TypeError,AttributeError): continue
        hosts,pattern=patterns[source]
        m=re.fullmatch(pattern,u.path.rstrip('/')) if u.scheme in ('http','https') and (u.hostname or '').lower() in hosts else None
        if m: ids.add(provider_key(source,m.group(1)))
    return ids, 'MusicBrainz linked provider IDs: '+(', '.join(sorted(ids)) or 'none')


def original_key(row):
    source=provider_source(row.get('source'))
    pid=provider_key(source,row.get(source+'_artist_id'))
    return (source,pid) if source in LINK_PROVIDERS and pid else None


def linked_keys_for(mbid, rows, name):
    """A corroborated original identity proves presence, not uniqueness.
    Unrelated secondary overlaps never prove presence by themselves.
    """
    body,_=mb_metadata(mbid)
    if not body: return set(),False
    names=metadata_names(body,name)
    keys={(p,v) for p in LINK_PROVIDERS for v in linked_ids(mbid,p)[0]}
    owners=[r for r in rows if identities(r)&keys]
    if not owners: return set(),False
    primary=[r for r in owners if original_key(r) in keys and name_key(r.get('artist_name')) in names]
    if primary:
        if len(owners)>1:
            print(f'WARNING: {name}: verified existing artist; {len(owners)} Watchlist rows have overlapping provider links; left unchanged.',flush=True)
        return {original_key(r) for r in primary},False
    # Legacy rows without an original source can still be recognized by a
    # unique name-corroborated provider link; do not treat unrelated rows as matches.
    if len(owners)==1 and name_key(owners[0].get('artist_name')) in names:
        return identities(owners[0])&keys,False
    return set(),True


def metadata_names(meta, name=''):
    return {name_key(n) for n in [name, meta.get('name'), meta.get('sort-name')]
            + [a.get('name') for a in meta.get('aliases',[]) if isinstance(a,dict)] if name_key(n)}


def direct_artist(source, pid, mbid, name):
    """Verify a linked catalog without name search; no private credentials sent."""
    meta,_=mb_metadata(mbid)
    if not meta or pid not in linked_ids(mbid,source)[0]:
        return None, 'no independently verified provider link'
    try:
        if source=='musicbrainz' and pid==mbid:
            body={'id':meta.get('id'),'name':meta.get('name')}
            status=200
        elif source=='deezer' and re.fullmatch(r'\d+',pid):
            status,body=request('https://api.deezer.com',{'Accept':'application/json'},'GET','/artist/'+pid)
        elif source=='itunes' and re.fullmatch(r'\d+',pid):
            status,data=request('https://itunes.apple.com',{'Accept':'application/json'},'GET','/lookup?id='+pid+'&entity=musicArtist')
            results=data.get('results',[]) if isinstance(data,dict) else []
            found=[r for r in results if isinstance(r,dict) and r.get('wrapperType')=='artist' and str(r.get('artistId'))==pid]
            body={'id':found[0].get('artistId'),'name':found[0].get('artistName')} if len(found)==1 else {}
        else:
            return None, 'direct lookup not available for '+source+'; verified link needs search or manual review'
    except (RuntimeError,OSError,ValueError,TypeError,AttributeError):
        return None, source+' direct lookup unavailable'
    if status!=200 or not isinstance(body,dict) or body.get('error'):
        return None, source+' direct lookup unavailable (HTTP '+str(status)+')'
    if provider_key(source,body.get('id'))!=pid or name_key(body.get('name')) not in metadata_names(meta,name):
        return None, source+' direct lookup returned an unverified identity'
    result={'id':pid,'name':body['name']}
    if type(body.get('nb_album')) is int: result['album_count']=body['nb_album']
    return result, 'MusicBrainz-linked direct provider lookup'


def recover_owner_identity(row, target_mbid, target_keys, issues=None):
    """Find a distinct owner's missing MBID using its original provider key.

    Name search only discovers candidates; it is never identity evidence.
    A unique candidate must independently link to the original provider ID.
    Incomplete searches, conflicting identities and failures stay in review.
    """
    name=name_key(row.get('artist_name'))
    source=provider_source(row.get('source'))
    key=(source,provider_key(source,row.get(source+'_artist_id')))
    if not name or source not in LINK_PROVIDERS or not key[1]: return False
    def get(path):
        status,body=mb_get(path)
        if status in (0,429,500,502,503,504):
            message=f"MusicBrainz owner lookup for {row.get('artist_name')}: {'HTTP '+str(status) if status else 'connection failure'}; temporary lookup failure after retries"
            if issues is not None: issues.append(message)
            print("WARNING: "+message,flush=True)
        return status,body
    # Exact reverse link is preferable to a broad name search. Some providers
    # have variable URL paths, so use bounded name discovery when necessary.
    bases={'spotify':'https://open.spotify.com/artist/',
           'deezer':'https://www.deezer.com/artist/',
           'discogs':'https://www.discogs.com/artist/',
           'amazon':'https://music.amazon.com/artists/'}
    candidates=None
    if source in bases and re.fullmatch(r'[A-Za-z0-9]+',key[1]):
        url=bases[source]+key[1]
        status,body=get('/ws/2/url?'+urlencode({'resource':url,'inc':'artist-rels','fmt':'json'}))
        if status==200:
            if not isinstance(body,dict) or body.get('resource')!=url or not isinstance(body.get('relations'),list): return False
            candidates=[r['artist'] for r in body['relations'] if isinstance(r,dict) and not r.get('ended') and isinstance(r.get('artist'),dict)]
        elif status!=404: return False
    if not candidates:
        phrase=str(row['artist_name']).replace('\\','\\\\').replace('"','\\"')
        status,body=get('/ws/2/artist?'+urlencode({'query':'artist:"'+phrase+'"','limit':10,'fmt':'json'}))
        if status!=200 or not isinstance(body,dict): return False
        candidates=body.get('artists'); count=body.get('count')
        if not isinstance(candidates,list) or type(count) is not int or count!=len(candidates): return False
    if len(candidates)>10: return False
    found=set()
    for candidate in candidates:
        if not isinstance(candidate,dict): return False
        mid=norm(candidate.get('id'))
        if mid not in musicbrainz_ids(mid): return False
        # Examine exact names and aliases. A matching source key is required.
        meta,detail=mb_metadata(mid)
        if not meta:
            if issues is not None: issues.append(detail)
            return False
        if name not in metadata_names(meta): continue
        keys={(p,v) for p in LINK_PROVIDERS for v in linked_ids(mid,p)[0]}
        if key not in keys: continue
        if mid==target_mbid or keys & target_keys: return False
        found.add(mid)
    return len(found)==1


def unrelated_mbid_associations(rows, mbid, name, key, issues=None):
    """Only disregard a foreign multi-ID association with positive evidence.
    The target must have a verified provider key, and each other owner must
    have a different name, two disjoint provider namespaces, and its own
    independently corroborated MusicBrainz identity. Never mutate owners.
    """
    owners=mbid_rows(rows,mbid)
    if not owners: return True
    target,_=mb_metadata(mbid)
    if not target or key[0] not in LINK_PROVIDERS or key[1] not in linked_ids(mbid,key[0])[0]: return False
    target_names=metadata_names(target,name)
    target_keys={(p,v) for p in LINK_PROVIDERS for v in linked_ids(mbid,p)[0]}
    for row in owners:
        mids=musicbrainz_ids(row.get('musicbrainz_artist_id'))
        if len(mids)<2 or name_key(row.get('artist_name')) in target_names: return False
        keys={k for k in identities(row) if k[0] in LINK_PROVIDERS}
        if keys & target_keys: return False
        if len({p for p,v in keys}&{p for p,v in target_keys})<2: return False
        # Confirm a different artist using its own authoritative ID and its
        # original provider identity (or another independently linked key).
        corroborated=False
        for other in sorted(mids-{mbid})[:5]:
            other_meta,_=mb_metadata(other)
            if not other_meta or name_key(row.get('artist_name')) not in metadata_names(other_meta): continue
            other_keys={(p,v) for p in LINK_PROVIDERS for v in linked_ids(other,p)[0]}
            if keys & other_keys and not other_keys & target_keys:
                corroborated=True; break
        if not corroborated and not recover_owner_identity(row,mbid,target_keys,issues): return False
    return True


def search_artists(cfg, query, limit=10):
    body=ss_data(cfg,'POST','/api/v1/search/artists',{'query':query,'limit':limit})
    data=body.get('data') or {}
    source=provider_source(data.get('source'))
    candidates=data.get('artists')
    if source not in PROVIDERS:
        raise RuntimeError('SoulSync returned unsupported artist-search provider: '+(source or '(missing)')+'; no writes. Check SoulSync API compatibility.')
    if not isinstance(candidates,list): raise RuntimeError('SoulSync: unexpected search result format')
    return source,[a for a in candidates if isinstance(a,dict) and norm(a.get('id')) and norm(a.get('name'))]

def record(cfg, artist, status, detail, candidates=()):
    row={'time':datetime.now(timezone.utc).isoformat(),'profile':str(cfg['SOULSYNC_PROFILE_ID']),
         'lidarr_id':str(artist.get('id','')),'artist':str(artist.get('artistName','')),
         'mbid':norm(artist.get('foreignArtistId')),'status':status,'detail':detail,'candidates':list(candidates)}
    try:
        with os.fdopen(os.open(BASE/'activity.jsonl',os.O_WRONLY|os.O_APPEND|os.O_CREAT,0o600),'a',encoding='utf-8') as f:
            f.write(json.dumps(row,ensure_ascii=True)+'\n')
    except OSError:
        print('WARNING: Could not write activity.jsonl; check directory permissions.',file=sys.stderr)


def pending_reviews(cfg):
    path=BASE/'activity.jsonl'; latest={}; history=[]
    if path.exists():
        for line in path.read_text().splitlines():
            try: row=json.loads(line)
            except ValueError: continue
            if isinstance(row,dict) and row.get('profile')==str(cfg['SOULSYNC_PROFILE_ID']): history.append(row)
    # Upgrade legacy records (without an MBID) if a later entry for the same
    # local ID supplies an identity. Never coalesce different MBIDs by name.
    mids={str(r.get('lidarr_id')):r['mbid'] for r in history if r.get('lidarr_id') and r.get('mbid')}
    for row in history:
        key=row.get('mbid') or mids.get(str(row.get('lidarr_id'))) or row.get('lidarr_id') or row.get('artist')
        latest[key]=row
    return [r for r in latest.values() if r.get('status') in ('review','error','deferred')]

def show_review(cfg):
    path=BASE/'activity.jsonl'; pending=pending_reviews(cfg)
    print(f'{len(pending)} unresolved artist attempts in recorded history (profile {cfg["SOULSYNC_PROFILE_ID"]}).')
    for row in pending:
        print(f'{row["artist"]} (Lidarr ID {row["lidarr_id"]}): {row["status"].upper()} — {row["detail"]}')
        if row.get('candidates'): print('  Candidates: '+', '.join(row['candidates']))
        if row.get('artist'): print('  Retry preview: python3 lidarr-to-soulsync.py --artist-name '+shlex.quote(row['artist']))
    print('History: '+str(path))
    return 0


def process(cfg,artist,rows,apply,manual=None,plan=None):
    name = str(artist.get('artistName') or '').strip()
    mbid = norm(artist.get('foreignArtistId'))
    def finish(status, message, candidates=()):
        print(message,flush=True)
        if apply: record(cfg,artist,'deferred' if status=='review' and ('temporary lookup failure' in message or 'unavailable after retries' in message) else status,message,candidates)
        return status
    if not name:
        return finish('review','REVIEW: missing artist name')
    if verified_mbid(rows,mbid,name):
        return finish('existing','ALREADY WATCHED: '+name)
    source, candidates = search_artists(cfg,name)
    def candidate_mbid(a):
        return norm(a.get('id') if source=='musicbrainz' else a.get('musicbrainz_artist_id') or a.get('musicbrainz_id'))
    def compatible(a):
        mids=musicbrainz_ids(candidate_mbid(a))
        return not (mbid and mids and mbid not in mids)
    def dedup(items): return list({provider_key(source,a['id']):a for a in items}.values())
    exact=dedup(a for a in candidates if name_key(a['name'])==name_key(name) and compatible(a))
    confirmed=dedup(a for a in candidates if mbid and musicbrainz_ids(candidate_mbid(a))=={mbid})
    matches=confirmed or exact
    reason='MusicBrainz ID' if confirmed else 'exact name'
    candidate_ids=[source+':'+str(a['id']) for a in matches]
    linked=set(); verified=[]; cross_keys=set(); detail=''
    # A direct, unique provider match needs no external lookup.
    if len(matches)==1 and not manual and verified_keys(rows,{(source,provider_key(source,matches[0]['id']))},name):
        return finish('existing','ALREADY WATCHED: '+name)
    if rows:
        cross_keys,cross_conflict=linked_keys_for(mbid,rows,name)
        if cross_keys: return finish('existing','ALREADY WATCHED: '+name+' (MusicBrainz cross-provider identity)')
        if cross_conflict: return finish('review',f'REVIEW: {name}: MusicBrainz provider links overlap existing Watchlist entries without unique corroboration; no change',candidate_ids)
    if not confirmed:
        linked, detail=linked_ids(mbid,source)
        verified=dedup(a for a in candidates if compatible(a) and provider_key(source,a['id']) in linked)
        # Search canonical names and aliases only when identity can be verified.
        if not verified and linked:
            meta,_=mb_metadata(mbid)
            aliases=[a for a in meta.get('aliases',[]) if isinstance(a,dict)]
            aliases.sort(key=lambda a:(not bool(a.get('primary')), ',' in str(a.get('name','')), not str(a.get('name','')).isascii()))
            queries=[meta.get('name')]+[a.get('name') for a in aliases]+[meta.get('sort-name')]
            seen={norm(name)}
            for query in queries:
                if not query or norm(query) in seen: continue
                seen.add(norm(query))
                if len(seen)>9: break
                other,more=search_artists(cfg,query,25)
                if other!=source:
                    return finish('review',f'REVIEW: {name}: SoulSync search provider changed during matching; no change',candidate_ids)
                verified=dedup(verified+[a for a in more if compatible(a) and provider_key(source,a['id']) in linked])
                if verified: break
        # A missing search result is not a missing artist. Only attempt a
        # unique linked ID, never choose among unseen alternate catalogs.
        direct_reason=''
        if not verified and len(linked)==1:
            direct, direct_reason=direct_artist(source,next(iter(linked)),mbid,name)
            if direct:
                verified=[direct]
                if direct.get('album_count')==0:
                    print(f'WARNING: {name}: {source} reports zero albums; future releases may still be monitored.',flush=True)
        if len(verified)>1:
            # Prefer a verified standalone exact-name match over related projects.
            # If no exact match exists, use corroborated canonical/alias names.
            meta,_=mb_metadata(mbid)
            standalone=[a for a in verified if name_key(a['name'])==name_key(name)]
            aliases=[a for a in verified if name_key(a['name']) in metadata_names(meta,name)]
            if standalone or aliases:
                verified=standalone or aliases
        if verified_keys(rows,{(source,provider_key(source,a['id'])) for a in verified},name):
            return finish('existing','ALREADY WATCHED: '+name+' (MusicBrainz-linked provider catalog)')
        if len(verified)==1:
            matches=verified; reason=direct_reason or 'MusicBrainz provider link'
        elif len(verified)>1:
            matches=verified; reason=detail+'; multiple linked catalogs without clear dominant profile'
            if not manual:
                dominant=dominant_linked(verified)
                if dominant: matches=[dominant]; reason='MusicBrainz-linked catalog; dominant follower count'
        elif linked:
            matches=[]; reason=detail+'; no matching provider catalog in search results'+('; '+direct_reason if direct_reason else '')
        elif len(matches)!=1:
            reason=detail
        elif 'temporary lookup failure' in detail or 'unavailable after retries' in detail:
            return finish('review',f'REVIEW: {name}: {detail}; exact-name identity not independently verified; no change',candidate_ids)
        if manual and len(matches)!=1:
            chosen=[a for a in matches if source+':'+str(a['id'])==manual]
            if len(chosen)==1: matches=chosen; reason='user-confirmed provider ID'
        candidate_ids=list(dict.fromkeys(candidate_ids+[source+':'+str(a['id']) for a in verified]))
    if manual and (len(matches)!=1 or source+':'+str(matches[0]['id'])!=manual):
        return finish('review',f'REVIEW: {name}: requested provider ID not uniquely eligible or conflicts with verified identity; no change',candidate_ids)
    if len(matches)!=1:
        return finish('review',f'REVIEW: {name}: {len(matches)} eligible artist matches; {reason}; no change. Candidates: '+', '.join(candidate_ids),candidate_ids)
    match=matches[0]; pid=str(match['id']); key=(source,provider_key(source,pid))
    print(f'MATCH: {name} ({source}:{pid}) via {reason}',flush=True)
    if verified_keys(rows,{key},name):
        return finish('existing','ALREADY WATCHED: '+name)
    if any(name_key(r.get('artist_name'))==name_key(name) or name_key(r.get('artist_name'))==name_key(match['name']) for r in rows):
        return finish('review',f'REVIEW: {name}: same name already watched but identity not verified; {detail+"; " if detail else ""}no change',candidate_ids)
    if mbid_rows(rows,mbid):
        issues=[]
        if not unrelated_mbid_associations(rows,mbid,name,key,issues):
            explanation='; '.join(x for x in [detail,*issues] if x)
            return finish('review',f'REVIEW: {name}: stored MusicBrainz ID is shared or lacks corroborating name; {explanation+"; " if explanation else ""}no change',candidate_ids)
        print(f'WARNING: {name}: independently verified unrelated Watchlist association; existing artist left unchanged.',flush=True)
    if not apply:
        if plan is not None: plan.append((artist,source+':'+pid))
        return finish('new',f'WOULD ADD: {name} ({source}:{pid})')
    # Re-read before every write; local lock serializes bridge invocations.
    fresh=watchlist(cfg)
    linked_keys={(source,provider_key(source,a['id'])) for a in verified} | {key}
    if fresh and mbid:
        fresh_keys,fresh_conflict=linked_keys_for(mbid,fresh,name)
        if fresh_conflict:
            rows[:]=fresh; return finish('review',f'REVIEW: {name}: conflicting provider association appeared; no change',candidate_ids)
        if fresh_keys:
            rows[:]=fresh; return finish('existing','ALREADY WATCHED: '+name+' (MusicBrainz cross-provider identity)')
        linked_keys |= fresh_keys
    if verified_keys(fresh,linked_keys | {key} | cross_keys,name) or verified_mbid(fresh,mbid,name):
        rows[:]=fresh; return finish('existing','ALREADY WATCHED: '+name)
    if any(name_key(r.get('artist_name')) in {name_key(name),name_key(match['name'])} for r in fresh):
        rows[:]=fresh; return finish('review',f'REVIEW: {name}: same-name entry appeared; no change',candidate_ids)
    foreign_association=bool(mbid_rows(fresh,mbid))
    issues=[]
    if foreign_association and not unrelated_mbid_associations(fresh,mbid,name,key,issues):
        explanation='; '.join(issues)
        rows[:]=fresh; return finish('review',f'REVIEW: {name}: unverified MusicBrainz association appeared; {explanation+"; " if explanation else ""}no change',candidate_ids)
    ss_data(cfg,'POST','/api/v1/watchlist',{'artist_id':pid,'artist_name':match['name'],'source':source},codes=(200,201))
    rows[:]=watchlist(cfg)
    # A contaminated MBID alone cannot prove a successful new addition.
    if foreign_association:
        verified_add=any(key in identities(r) and name_key(r.get('artist_name')) in {name_key(name),name_key(match['name'])} for r in rows)
    else:
        verified_add=verified_keys(rows,{key},name) or verified_keys(rows,{key},match['name']) or verified_mbid(rows,mbid,name)
    if not verified_add:
        raise RuntimeError(f'Add returned success for {name}, but could not verify identity in watchlist. Check manually before retrying.')
    return finish('added',f'ADDED: {name} ({source}:{pid}; {reason})')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bulk',action='store_true'); p.add_argument('--apply',action='store_true',help='write changes (bulk or single artist)')
    p.add_argument('--artist',type=int,help='preview/retry a single Lidarr artist ID'); p.add_argument('--provider-id',help='explicitly verified provider:ID for a single artist'); p.add_argument('--review',action='store_true',help='show unresolved recorded attempts'); p.add_argument('--limit',type=int); p.add_argument('--delay',type=float,default=1)
    p.add_argument('--artist-name',help='preview/retry exact Lidarr artist name'); p.add_argument('--retry-all',action='store_true',help='preview/retry recorded unresolved artists')
    p.add_argument('--select',action='store_true',help='preview bulk and choose specific proposed additions interactively')
    args=p.parse_args()
    if args.select and (not args.bulk or args.apply): p.error('--select requires --bulk without --apply')
    if args.select and not sys.stdin.isatty(): p.error('--select requires an interactive terminal')
    single=bool(args.artist or args.artist_name); explicit=bool(args.bulk or single or args.retry_all)
    if sum(bool(x) for x in (args.bulk,args.artist,args.artist_name,args.retry_all,args.review))>1: p.error('Choose one operation')
    if (args.limit is not None and args.limit<1) or args.delay<0 or (not explicit and args.apply) or (not args.bulk and args.limit is not None) or (args.artist and args.bulk) or (args.provider_id and not single) or (args.review and (args.bulk or args.artist or args.apply or args.provider_id)) or (args.artist is not None and args.artist<1):
        p.error('Invalid arguments; --apply requires --bulk or --artist; --limit requires --bulk')
    event=norm(env('Lidarr_EventType'))
    if not explicit and not args.review and event not in ('test','artistadd'):
        print('Ignoring non-ArtistAdd event. Use --bulk to preview existing artists.'); return 0
    cfg=None; active=None; logged_error=False
    try:
        cfg=config()
        for k in ('LIDARR_URL','LIDARR_API_KEY','SOULSYNC_URL','SOULSYNC_API_KEY','SOULSYNC_PROFILE_ID'):
            if not cfg.get(k): raise RuntimeError('Missing configuration: '+k+'; run setup.py')
        if args.review: return show_review(cfg)
        mode=cfg.get('SYNC_MODE')
        if mode not in ('bulk','future','both'): raise RuntimeError('Invalid SYNC_MODE; run setup.py in a fresh folder')
        if cfg.get('ARTIST_SCOPE') not in ('all','monitored'): raise RuntimeError('Invalid ARTIST_SCOPE')
        if args.bulk and mode=='future': raise RuntimeError('Bulk import disabled in future-only mode')
        if not explicit and mode=='bulk': print('Future sync disabled (bulk-only mode).'); return 0
        if event=='test' and not explicit:
            rows=watchlist(cfg); lidarr(cfg,'/api/v1/artist'); print(f'Connection test passed. {len(rows)} watched artists. No writes.'); return 0
        lockpath=BASE/'bridge.lock'
        with os.fdopen(os.open(lockpath,os.O_CREAT|os.O_RDWR,0o600),'w') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            artists=lidarr(cfg,'/api/v1/artist'); tags=tag_map(cfg)
            if cfg.get('REQUIRE_TAG') and norm(cfg['REQUIRE_TAG']) not in tags.values(): raise RuntimeError('Required Lidarr tag not found')
            unresolved_selection=0
            if args.bulk:
                selected=sorted((a for a in artists if eligible(cfg,a,tags)),key=lambda a:norm(a.get('artistName')))
                if args.limit is not None: selected=selected[:args.limit]
            elif args.retry_all:
                selected=[]
                for r in pending_reviews(cfg):
                    mid=norm(r.get('mbid')); old=str(r.get('lidarr_id') or '')
                    found=[a for a in artists if (norm(a.get('foreignArtistId'))==mid if mid else str(a.get('id'))==old and norm(a.get('artistName'))==norm(r.get('artist')))]
                    if len(found)==1 and eligible(cfg,found[0],tags):
                        if found[0] not in selected: selected.append(found[0])
                    else:
                        unresolved_selection+=1
                        print('REVIEW: '+str(r.get('artist'))+': no unique eligible current Lidarr record; remains pending')
            else:
                lid=str(args.artist) if args.artist else env('Lidarr_Artist_Id'); mb=norm(env('Lidarr_Artist_MBId')); name=norm(args.artist_name or env('Lidarr_Artist_Title','Lidarr_Artist_Name'))
                if args.artist_name: lid=''; mb=''
                selected=[a for a in artists if (str(a.get('id'))==lid if lid else norm(a.get('foreignArtistId'))==mb if mb else name_key(a.get('artistName'))==name_key(name))]
                if len(selected)!=1: raise RuntimeError('Cannot uniquely identify Lidarr artist; check current artist ID or use --artist-name with the exact Lidarr name')
                if not eligible(cfg,selected[0],tags):
                    print('SKIP: artist outside configured scope/tag');
                    if not explicit or args.apply: record(cfg,selected[0],'skipped','outside configured scope/tag')
                    return 0
            if len(selected)==1: active=selected[0]
            rows=watchlist(cfg); apply=args.apply if explicit else True
            print(f'{"APPLY" if apply else "PREVIEW"}: {len(selected)} eligible artists; {len(rows)} currently watched. Profile {cfg["SOULSYNC_PROFILE_ID"]}.')
            if not apply: print('No watchlist changes will be made.')
            counts={k:0 for k in ('existing','new','added','review')}
            counts['review']=unresolved_selection
            plan=[]
            for i,a in enumerate(selected,1):
                print(f'[{i}/{len(selected)}]',flush=True)
                try:
                    counts[process(cfg,a,rows,apply,args.provider_id,plan=plan) if args.select else process(cfg,a,rows,apply,args.provider_id)]+=1
                except (OSError,RuntimeError,ValueError,KeyError,TypeError) as exc:
                    if apply:
                        record(cfg,a,'error',str(exc) if isinstance(exc,RuntimeError) else type(exc).__name__); logged_error=True
                    raise
                if i<len(selected): time.sleep(args.delay)
            print('Summary: '+', '.join(f'{v} {k}' for k,v in counts.items()))
            if args.select and plan:
                print('\nProposed additions (choose individual artists):')
                for n,(a,pid) in enumerate(plan,1): print(f'{n}. {a["artistName"]} ({pid})')
                try: raw=input('Enter comma-separated numbers, or Enter to cancel: ').strip()
                except (EOFError,KeyboardInterrupt): return 0
                if not raw: print('Cancelled. No writes.'); return 0
                try: chosen=sorted({int(x.strip()) for x in raw.split(',')})
                except ValueError: print('Invalid selection. No writes.'); return 2
                if not chosen or any(n<1 or n>len(plan) for n in chosen): print('Invalid selection. No writes.'); return 2
                print('Selected: '+', '.join(plan[n-1][0]['artistName'] for n in chosen))
                try: confirm=input('Type yes to add these artists to the selected SoulSync profile: ').strip().lower()
                except (EOFError,KeyboardInterrupt): confirm=''
                if confirm!='yes': print('Cancelled. No writes.'); return 0
                applied={k:0 for k in counts}
                current=lidarr(cfg,'/api/v1/artist'); current_tags=tag_map(cfg)
                for n in chosen:
                    a,pid=plan[n-1]
                    current_matches=[r for r in current if str(r.get('id'))==str(a.get('id')) and norm(r.get('foreignArtistId'))==norm(a.get('foreignArtistId')) and norm(r.get('artistName'))==norm(a.get('artistName')) and eligible(cfg,r,current_tags)]
                    if len(current_matches)!=1:
                        print('REVIEW: '+a['artistName']+': Lidarr artist changed since preview; no change'); applied['review']+=1; continue
                    a=current_matches[0]; active=a
                    try: applied[process(cfg,a,rows,True,pid)]+=1
                    except (OSError,RuntimeError,ValueError,KeyError,TypeError) as exc:
                        record(cfg,a,'error',str(exc) if isinstance(exc,RuntimeError) else type(exc).__name__); logged_error=True; raise
                print('Selected import summary: '+', '.join(f'{v} {k}' for k,v in applied.items()))
                return 2 if applied['review'] else 0
            if counts['review']:
                print('Manual review required; no unresolved artist was added. For recorded apply attempts run --review.',file=sys.stderr)
                return 2
            return 0
    except (OSError,RuntimeError,ValueError,KeyError,TypeError) as exc:
        if cfg and cfg.get('SOULSYNC_PROFILE_ID') and not logged_error and ((event=='artistadd' and not explicit) or (single and args.apply)):
            record(cfg,active or {'id':args.artist or env('Lidarr_Artist_Id'),'artistName':args.artist_name or env('Lidarr_Artist_Title','Lidarr_Artist_Name')},'error',str(exc) if isinstance(exc,RuntimeError) else type(exc).__name__)
        print('ERROR: '+(str(exc) if isinstance(exc,RuntimeError) else type(exc).__name__)+'; stopped. Earlier successful adds may remain.',file=sys.stderr); return 1

if __name__=='__main__': sys.exit(main())
