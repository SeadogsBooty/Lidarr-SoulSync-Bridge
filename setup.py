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

"""Interactive setup and optional Lidarr connection registration."""
import argparse
import connect
import install
import getpass
import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

BASE = Path(__file__).resolve().parent
CONFIG = BASE / 'config.env'
spec = importlib.util.spec_from_file_location('bridge', BASE / 'lidarr-to-soulsync.py')
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


def ask(label, default='', secret=False):
    while True:
        value = (getpass.getpass(label + ': ') if secret else input(label + (f' [{default}]' if default else '') + ': ')).strip() or default
        if value and not any(c in value for c in '\r\n'):
            return value
        print('Please enter a value.')


def url(label, default):
    while True:
        value = ask(label, default).rstrip('/')
        try:
            p = urlsplit(value)
            if p.scheme in ('http', 'https') and p.hostname and not (p.username or p.password or p.query or p.fragment):
                _ = p.port
                return value
        except ValueError:
            pass
        print('Enter a full http:// or https:// server address, without a login or query string.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--connect', action='store_true', help='create connection using saved config, after confirmation')
    parser.add_argument('--connection-preview', action='store_true', help='inspect saved config and Lidarr without changes')
    args = parser.parse_args()
    if args.connect or args.connection_preview:
        if not CONFIG.exists():
            print('Run setup.py first.'); return 1
        cfg = dict((k.strip(), v.strip().strip(chr(34)).strip(chr(39))) for k,v in (line.split('=',1) for line in CONFIG.read_text().splitlines() if '=' in line and not line.lstrip().startswith('#')))
        return register(cfg, preview=args.connection_preview)
    print('\nLidarr -> SoulSync: first-time setup')
    print('Run this in the same Linux environment/container that will execute the bridge.')
    print('This wizard configures the bridge. Existing-artist modes preview an import and ask before adding anything. Future sync creates a Lidarr connection after confirmation.')
    if CONFIG.exists():
        print('A config.env already exists. It will not be replaced. Use a fresh folder for a clean test.')
        return 1
    if not sys.stdin.isatty():
        print('Run in an interactive terminal (Docker: docker exec -it ...).')
        return 1
    cfg = {}
    print('\n1. Lidarr: Settings > General > Security > API Key.')
    cfg['LIDARR_URL'] = url('Lidarr address', 'http://localhost:8686')
    cfg['LIDARR_API_KEY'] = ask('Lidarr API key (hidden)', secret=True)
    try:
        artists = bridge.lidarr(cfg, '/api/v1/artist')
        monitored = [a for a in artists if a.get('monitored') is True]
        print(f'Lidarr connected. {len(artists)} artists, {len(monitored)} monitored.')
        target = install.destination(bridge, cfg)
        print('Lidarr application data: ' + str(target.parent.parent))
        print('Permanent bridge location: ' + str(target))
        if target.exists() and target.resolve() != BASE:
            print('A bridge directory already exists at this location. No files overwritten. Review it or use its setup.py.')
            return 1
    except (OSError, ValueError, RuntimeError, TypeError) as exc:
        print(str(exc) if isinstance(exc, RuntimeError) else 'Lidarr check failed. Check address, port, base path, API key and network reachability.')
        print('No config saved.')
        return 1
    print('\n2. SoulSync: Settings > SoulSync API > Generate API Key (menu wording may vary).')
    print('Use a key with search and watchlist write access. Keep both keys private.')
    cfg['SOULSYNC_URL'] = url('SoulSync address', 'http://localhost:8008')
    cfg['SOULSYNC_API_KEY'] = ask('SoulSync API key (hidden)', secret=True)
    try:
        profiles = bridge.profiles(cfg)
        print('Available SoulSync profiles:')
        for i, profile in enumerate(profiles, 1):
            print(f"{i}. {profile['name']}")
        if len(profiles) == 1:
            chosen = profiles[0]
        else:
            while True:
                answer = ask('Choose profile by menu number (no default)')
                if answer.isdigit() and 1 <= int(answer) <= len(profiles):
                    chosen = profiles[int(answer)-1]
                    break
                print('Choose one of the listed numbers.')
        cfg['SOULSYNC_PROFILE_ID'] = str(chosen['id'])
        install.validate_config({'SOULSYNC_PROFILE_ID': cfg['SOULSYNC_PROFILE_ID']})
        rows = bridge.watchlist(cfg)
        provider, _ = bridge.search_artists(cfg, 'The Beatles', 5)
        print('SoulSync artist-search provider: '+provider+' (selected by SoulSync)')
        print(f"Connected to {chosen['name']}: {len(rows)} watched artists. Search and read access verified; writes not tested.")
    except (OSError, ValueError, RuntimeError, TypeError) as exc:
        print(str(exc) if isinstance(exc, RuntimeError) else 'SoulSync connection failed.')
        print('No config saved. Retry setup when the issue is resolved.')
        return 1
    print('\n3. What would you like to do?')
    print('1 = Import existing artists now (one-time; review and confirm)')
    print('2 = Sync new artists only (no existing-library import)')
    print('3 = Both (import existing artists now, then enable future sync)')
    while True:
        choice = ask('Choose 1, 2 or 3', '1')
        if choice in ('1','2','3'): break
    cfg['SYNC_MODE'] = {'1':'bulk','2':'future','3':'both'}[choice]
    print('\n4. Which artists?')
    print('1 = Monitored artists only (recommended)')
    print('2 = All artists, including unmonitored')
    while True:
        choice = ask('Choose 1 or 2', '1')
        if choice in ('1','2'): break
    cfg['ARTIST_SCOPE'] = 'monitored' if choice == '1' else 'all'
    cfg['REQUIRE_TAG'] = ''
    if ask('Restrict to a Lidarr tag? (yes/no)', 'no').lower() == 'yes':
        tags = bridge.lidarr(cfg, '/api/v1/tag')
        print('Existing tags: ' + (', '.join(str(t['label']) for t in tags) or '(none)'))
        tag = ask('Required tag')
        if tag.casefold() not in {str(t['label']).casefold() for t in tags}:
            print('Tag not found. Create it in Lidarr and rerun setup. No config saved.')
            return 1
        cfg['REQUIRE_TAG'] = tag
    print('\nExisting watchlist artists are never deliberately updated. New artists use SoulSync defaults.')
    print('Selected profile: ' + str(chosen['name']))
    print('Mode: ' + cfg['SYNC_MODE'] + '; scope: ' + cfg['ARTIST_SCOPE'])
    print('Install directory: ' + str(target))
    print('Configuration will be saved privately next to the installed script. It contains API keys; do not share it.')
    if ask('Save configuration? Type yes to continue', 'no').lower() != 'yes':
        print('Cancelled. No config saved.')
        return 0
    try:
        install.save(BASE, target, cfg)
    except (OSError, RuntimeError) as exc:
        print(str(exc) if isinstance(exc, RuntimeError) else 'Cannot install files. Check AppData folder permissions; run as the Lidarr service account.')
        return 1
    print('\nConfiguration saved.')
    print('Installed in: ' + str(target))
    return finish_setup(cfg, target)


def initial_import(cfg, target):
    """Run the existing, confirmed bulk-selection flow in the installed directory."""
    script = target / 'lidarr-to-soulsync.py'
    child_env = os.environ.copy()
    # Always use the just-installed profile, never a caller's temporary override.
    child_env['BRIDGE_CONFIG'] = str(target / 'config.env')
    print('\nInitial import: profile ' + cfg['SOULSYNC_PROFILE_ID'], flush=True)
    print('Review the proposed artists. Enter all or individual numbers, then type yes to add.', flush=True)
    print('Adding artists can trigger SoulSync downloads. Pause automatic downloads if testing.', flush=True)
    return subprocess.run([sys.executable, '-u', str(script), '--bulk', '--select'],
                          cwd=str(target), env=child_env, check=False).returncode


def finish_setup(cfg, target):
    """Complete the chosen mode; distinguish review, failure and connection status."""
    mode = cfg['SYNC_MODE']
    result = 0
    if mode in ('bulk', 'both'):
        result = initial_import(cfg, target)
        if result == 2:
            print('Initial import has artists requiring review. Check the summary above.')
        elif result != 0:
            print('Initial import did not complete successfully. Earlier successful adds may remain.')
        else:
            print('Initial import step finished. Check the summary above for additions or cancellation.')
        print('To preview or resume later, run python3 ' + str(target / 'lidarr-to-soulsync.py') + ' --bulk --select')
    if mode in ('future', 'both'):
        print('\nFuture sync: configure the Lidarr Artist Add connection.')
        connection_result = register(cfg, script=target / 'lidarr-to-soulsync.py')
        if connection_result:
            return 1
    else:
        print('Existing-artist mode: no automatic Lidarr connection is needed.')
    return result


def register(cfg, preview=False, script=None):
    try:
        script = Path(script) if script is not None else BASE / 'lidarr-to-soulsync.py'
        retry = 'python3 ' + str(script.parent / 'setup.py') + ' --connect'
        state = connect.configure(bridge, cfg, script, apply=False)
        if state == 'conflict':
            return 1
        if state != 'preview' or preview:
            if state == 'existing' and not preview:
                print('Automatic sync is enabled. Add new eligible artists in Lidarr normally.')
            return 0
        print('This enables future Artist Add events, including automatic Lidarr additions within your selected scope/tag.')
        if ask('Create and test the SoulSync connection in Lidarr? Type yes to continue', 'no').lower() != 'yes':
            print('Automatic sync not enabled. Run ' + retry + ' to finish later.')
            return 0
        state = connect.configure(bridge, cfg, script, apply=True)
        if state in ('created', 'existing'):
            print('Automatic sync is enabled. Add new eligible artists in Lidarr normally.')
        return 1 if state == 'conflict' else 0
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        print(str(exc) if isinstance(exc, RuntimeError) else 'Connection setup failed. Check folder permissions and API compatibility.')
        print('Your config is saved. Fix the problem, then run ' + retry + '. No existing connection was overwritten.')
        return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (KeyboardInterrupt, EOFError):
        print('\nSetup cancelled.')
        sys.exit(1)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError):
        print('Setup failed. Check folder permissions and configuration inputs. No credentials displayed.')
        sys.exit(1)
