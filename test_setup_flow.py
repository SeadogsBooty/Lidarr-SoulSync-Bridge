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

import os
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import setup

TARGET = Path('/example/lidarr/scripts/soulsync')


class SetupFlowTests(unittest.TestCase):
    def test_bulk_import_only(self):
        with patch.object(setup, 'initial_import', return_value=0) as initial, patch.object(setup, 'register') as register:
            self.assertEqual(setup.finish_setup({'SYNC_MODE':'bulk'}, TARGET), 0)
            initial.assert_called_once()
            register.assert_not_called()

    def test_future_connection_only(self):
        with patch.object(setup, 'initial_import') as initial, patch.object(setup, 'register', return_value=0) as register:
            self.assertEqual(setup.finish_setup({'SYNC_MODE':'future'}, TARGET), 0)
            initial.assert_not_called()
            register.assert_called_once()

    def test_both_import_then_connection(self):
        order=[]
        with patch.object(setup, 'initial_import', side_effect=lambda *a: order.append('import') or 0), patch.object(setup, 'register', side_effect=lambda *a, **kw: order.append('connect') or 0):
            self.assertEqual(setup.finish_setup({'SYNC_MODE':'both'}, TARGET), 0)
            self.assertEqual(order, ['import','connect'])

    def test_review_does_not_prevent_future_sync(self):
        with patch.object(setup, 'initial_import', return_value=2), patch.object(setup, 'register', return_value=0) as register:
            self.assertEqual(setup.finish_setup({'SYNC_MODE':'both'}, TARGET), 2)
            register.assert_called_once()

    def test_connection_failure_reported(self):
        with patch.object(setup, 'initial_import', return_value=0), patch.object(setup, 'register', return_value=1):
            self.assertEqual(setup.finish_setup({'SYNC_MODE':'both'}, TARGET), 1)

    def test_import_uses_installed_config_and_confirmed_selection(self):
        with patch.dict(os.environ, {'BRIDGE_CONFIG':'/wrong/config.env'}), patch.object(setup.subprocess, 'run', return_value=Mock(returncode=2)) as run:
            self.assertEqual(setup.initial_import({'SOULSYNC_PROFILE_ID':'2'}, TARGET), 2)
            args, kwargs=run.call_args
            self.assertEqual(args[0][2:], [str(TARGET/'lidarr-to-soulsync.py'),'--bulk','--select'])
            self.assertEqual(kwargs['env']['BRIDGE_CONFIG'],str(TARGET/'config.env'))
            self.assertEqual(kwargs['cwd'],str(TARGET))
