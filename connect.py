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

"""Create a Lidarr Custom Script connection from its live schema, never overwrite."""
import copy
import os
from pathlib import Path

NAME = 'SoulSync'
ROUTE = '/api/v1/notification'


def field(row, name):
    return next((f.get('value') for f in row.get('fields', []) if isinstance(f, dict) and f.get('name') == name), None)


def related(row, path):
    return 'soulsync' in str(row.get('name', '')).casefold() or 'soulsync' in str(field(row, 'path') or '').casefold() or field(row, 'path') == path


def matches(row, path):
    return (str(row.get('implementation', '')).casefold() == 'customscript' and field(row, 'path') == path
            and row.get('onArtistAdd') is True and not row.get('tags') and not field(row, 'arguments')
            and not any(v is True for k, v in row.items() if k.startswith('on') and k != 'onArtistAdd'))


def configure(bridge, cfg, script, apply=False):
    if cfg.get('SYNC_MODE') not in ('future', 'both'):
        print('Bulk-only mode: no Lidarr connection needed.')
        return 'bulk'
    path = str(Path(script).resolve())
    def get():
        return bridge.lidarr(cfg, ROUTE)
    def existing(rows):
        found = [r for r in rows if related(r, path)]
        if not found:
            return None
        if len(found) == 1 and matches(found[0], path):
            print('Existing matching connection: ' + str(found[0].get('name')) + '. Left unchanged.')
            return 'existing'
        print('Existing SoulSync-related connection(s): ' + ', '.join(str(r.get('name')) for r in found))
        print('No connection created or changed. Review existing connections in Lidarr Settings > Connect before switching.')
        return 'conflict'
    result = existing(get())
    if result:
        return result
    schemas = bridge.lidarr(cfg, ROUTE + '/schema')
    candidates = [r for r in schemas if str(r.get('implementation', '')).casefold() == 'customscript']
    if len(candidates) != 1 or candidates[0].get('supportsOnArtistAdd') is not True:
        raise RuntimeError('Lidarr Custom Script schema does not advertise Artist Add support.')
    schema = candidates[0]
    if not schema.get('configContract'):
        raise RuntimeError('Lidarr Custom Script schema missing config contract.')
    fields = copy.deepcopy(schema.get('fields'))
    if not isinstance(fields, list) or not any(isinstance(f, dict) and f.get('name') == 'path' for f in fields):
        raise RuntimeError('Lidarr Custom Script schema missing path field.')
    for f in fields:
        if f.get('name') == 'path': f['value'] = path
        elif f.get('name') == 'arguments': f['value'] = ''
    payload = {k: v for k, v in schema.items() if k.startswith('supportsOn')}
    payload.update({k: False for k in schema if k.startswith('on')})
    payload.update(name=NAME, implementation=schema['implementation'], configContract=schema['configContract'], fields=fields, tags=[], onArtistAdd=True, includeHealthWarnings=False)
    print('Connection: SoulSync | Artist Add only | Script: ' + path)
    if not apply:
        print('Preview only. No Lidarr changes made.')
        return 'preview'
    if not Path(path).is_file() or not os.access(path, os.X_OK):
        raise RuntimeError('Script is missing or not executable. Run chmod +x lidarr-to-soulsync.py in the extracted folder.')
    headers = {'X-Api-Key': cfg['LIDARR_API_KEY']}
    def post(endpoint, codes):
        status, body = bridge.request(cfg['LIDARR_URL'], headers, 'POST', endpoint, payload)
        bridge.check(status, body, 'Lidarr ' + endpoint, codes)
    print('Testing script through Lidarr (no artist changes)...')
    post(ROUTE + '/test', (200, 204))
    print('Lidarr script test passed.')
    result = existing(get())
    if result:
        return result
    print('Creating connection...')
    try:
        post(ROUTE, (200, 201))
    except RuntimeError:
        print('Create failed or response was lost. Check Lidarr Settings > Connect before retrying.')
        raise
    saved = [r for r in get() if r.get('name') == NAME and matches(r, path)]
    if len(saved) != 1:
        raise RuntimeError('Create response succeeded but saved connection could not be verified. Check Lidarr Settings > Connect before retrying.')
    print('Verified: SoulSync connection created and Artist Add enabled. ID: ' + str(saved[0].get('id')))
    return 'created'
