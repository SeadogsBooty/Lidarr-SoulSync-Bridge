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
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import setup
from test_connect import SCHEMA


class WizardIntegrationTests(unittest.TestCase):
    """Real wizard, installer, matching and connection code; only transport is fake."""

    def run_wizard(self, mode, selection=(), connect='yes', unresolved=False,
                   wrong_profile=False, save='yes'):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)/'installed'
            artists = [dict(id=1, artistName='Example Alpha', monitored=True, tags=[]),
                       dict(id=2, artistName='Example Beta', monitored=True, tags=[])]
            rows, notifications, actions = [], [], []
            approved = {'import': False, 'connection': False}
            answers = iter(['http://lidarr.example', 'http://soulsync.example',
                            '2', mode, '2', 'no', save] + list(selection) +
                           ([connect] if mode in ('2', '3') else []))

            def answer(prompt):
                value = next(answers)
                if prompt.startswith('Type yes to add'):
                    approved['import'] = value == 'yes'
                if prompt.startswith('Create and test'):
                    approved['connection'] = value == 'yes'
                return value

            def request(url, headers, method, path, payload=None):
                if url == 'http://lidarr.example':
                    self.assertEqual(headers['X-Api-Key'], 'fake-lidarr')
                    if path == '/api/v1/artist':
                        return 200, artists
                    if path == '/api/v1/notification/schema':
                        return 200, [SCHEMA]
                    if path == '/api/v1/notification' and method == 'GET':
                        return 200, list(notifications)
                    if method == 'POST' and path in ('/api/v1/notification/test', '/api/v1/notification'):
                        self.assertTrue(approved['connection'])
                        self.assertTrue(payload['onArtistAdd'])
                        self.assertFalse(payload['onGrab'])
                        self.assertEqual(payload['tags'], [])
                        actions.append('test' if path.endswith('/test') else 'connect')
                        if path.endswith('/test'):
                            return 200, {}
                        notifications.append(dict(payload, id=1))
                        return 201, notifications[-1]
                elif url == 'http://soulsync.example':
                    self.assertEqual(headers['Authorization'], 'Bearer fake-soulsync')
                    if path == '/api/v1/profiles':
                        return 200, {'success': True, 'data': {'profiles': [
                            {'id': 1, 'name': 'Other profile'}, {'id': 2, 'name': 'Selected profile'}]}}
                    self.assertEqual(headers['X-Profile-Id'], '2')
                    if path == '/api/v1/watchlist' and method == 'GET':
                        result = ([{'profile_id': 1, 'artist_name': 'Other profile artist'}]
                                  if wrong_profile else list(rows))
                        return 200, {'success': True, 'data': {'artists': result}}
                    if path == '/api/v1/search/artists':
                        found = [a for a in artists if a['artistName'] == payload['query']]
                        matches = [dict(id=a['id'], name=a['artistName']) for a in found]
                        if unresolved and found and found[0]['id'] == 2:
                            matches.append(dict(id=99, name=found[0]['artistName']))
                        return 200, {'success': True, 'data': {'source': 'deezer', 'artists': matches}}
                    if path == '/api/v1/watchlist' and method == 'POST':
                        self.assertTrue(approved['import'], 'Write before explicit import approval')
                        self.assertEqual(set(payload), {'artist_id','artist_name','source'},
                                         'Artist addition must not override Watchlist settings or request a scan')
                        actions.append('add:' + payload['artist_id'])
                        rows.append({'profile_id': 2, 'artist_name': payload['artist_name'],
                                     'deezer_artist_id': payload['artist_id'], 'source': 'deezer'})
                        return 201, {'success': True}
                self.fail('Unexpected request: ' + method + ' ' + url + path)

            def child(command, cwd, env, check):
                self.assertEqual(command[3:], ['--bulk', '--select'])
                self.assertEqual(Path(cwd), target)
                self.assertEqual(env['BRIDGE_CONFIG'], str(target/'config.env'))
                spec = importlib.util.spec_from_file_location('installed_bridge', command[2])
                bridge = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(bridge)
                with patch.dict(os.environ, env, clear=True), patch('sys.argv', command[2:]), \
                     patch.object(bridge, 'request', side_effect=request), patch.object(bridge.time, 'sleep'):
                    return SimpleNamespace(returncode=bridge.main())

            with patch.object(setup, 'CONFIG', Path(tmp)/'staging-config.env'), \
                 patch.object(setup.install, 'destination', return_value=target), \
                 patch.object(setup.bridge, 'request', side_effect=request), \
                 patch.object(setup.subprocess, 'run', side_effect=child), \
                 patch.dict(os.environ, {'BRIDGE_CONFIG': '/wrong/profile/config.env'}), \
                 patch.object(setup.sys.stdin, 'isatty', return_value=True), \
                 patch('sys.argv', ['setup.py']), patch('builtins.input', side_effect=answer), \
                 patch.object(setup.getpass, 'getpass', side_effect=['fake-lidarr', 'fake-soulsync']), \
                 redirect_stdout(io.StringIO()):
                result = setup.main()
            if save == 'yes' and not wrong_profile:
                self.assertIn('SOULSYNC_PROFILE_ID=2', (target/'config.env').read_text())
                self.assertTrue((target/'MANUAL.md').is_file())
            else:
                self.assertFalse(target.exists())
            return result, actions

    def test_existing_all_approved(self):
        self.assertEqual(self.run_wizard('1', ['all', 'yes']), (0, ['add:1', 'add:2']))

    def test_existing_individual_approved(self):
        self.assertEqual(self.run_wizard('1', ['2', 'yes']), (0, ['add:2']))

    def test_future_only_tests_then_connects_without_import(self):
        self.assertEqual(self.run_wizard('2'), (0, ['test', 'connect']))

    def test_both_imports_then_tests_and_connects(self):
        self.assertEqual(self.run_wizard('3', ['all', 'yes']),
                         (0, ['add:1', 'add:2', 'test', 'connect']))

    def test_import_all_declined_never_writes(self):
        self.assertEqual(self.run_wizard('1', ['all', 'no']), (0, []))

    def test_blank_selection_still_offers_future_sync(self):
        self.assertEqual(self.run_wizard('3', ['']), (0, ['test', 'connect']))

    def test_declined_connection_never_writes(self):
        self.assertEqual(self.run_wizard('2', connect='no'), (0, []))

    def test_unresolved_identity_is_skipped_and_status_retained(self):
        self.assertEqual(self.run_wizard('3', ['all', 'yes'], unresolved=True),
                         (2, ['add:1', 'test', 'connect']))

    def test_wrong_profile_rejected_before_install_or_import(self):
        self.assertEqual(self.run_wizard('1', wrong_profile=True), (1, []))

    def test_declining_save_never_imports_or_connects(self):
        self.assertEqual(self.run_wizard('3', save='no'), (0, []))
