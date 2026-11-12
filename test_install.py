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

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import importlib.util
import install

SOURCE = Path(__file__).resolve().parent
CFG = {'LIDARR_URL':'http://lidarr', 'LIDARR_API_KEY':'fake', 'SOULSYNC_API_KEY':'fake2'}
spec = importlib.util.spec_from_file_location('bridge_install_test', SOURCE / 'lidarr-to-soulsync.py')
real_bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(real_bridge)

class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = Path(self.tmp.name) / 'lidarr'
        self.app.mkdir()
        (self.app/'config.xml').write_text('<Config><ApiKey>fake</ApiKey></Config>')
        self.bridge = Mock()
        self.bridge.lidarr.return_value = {'appData':str(self.app)}
    def test_destination(self):
        self.assertEqual(install.destination(self.bridge, CFG), self.app/'scripts'/'soulsync')
    def test_real_helper_status_object(self):
        with patch.object(real_bridge, 'request', return_value=(200, {'appData':str(self.app)})) as req:
            self.assertEqual(install.destination(real_bridge, CFG), self.app/'scripts'/'soulsync')
            req.assert_called_once_with('http://lidarr', {'X-Api-Key':'fake'}, 'GET', '/api/v1/system/status')
    def test_real_helper_rejects_status_list(self):
        with patch.object(real_bridge, 'request', return_value=(200, [])):
            with self.assertRaisesRegex(RuntimeError,'unexpected object'):
                install.destination(real_bridge, CFG)
    def test_real_helper_preserves_list_validation(self):
        with patch.object(real_bridge, 'request', return_value=(200, {'appData':str(self.app)})):
            with self.assertRaisesRegex(RuntimeError,'unexpected list'):
                real_bridge.lidarr(CFG, '/api/v1/artist')
        with patch.object(real_bridge, 'request', return_value=(200, [{'id':1}])):
            self.assertEqual(real_bridge.lidarr(CFG, '/api/v1/artist'), [{'id':1}])
    def test_wrong_instance(self):
        with self.assertRaisesRegex(RuntimeError,'does not match'):
            install.destination(self.bridge, dict(CFG,LIDARR_API_KEY='different'))
    def test_missing_config(self):
        (self.app/'config.xml').unlink()
        with self.assertRaisesRegex(RuntimeError,'Cannot read'):
            install.destination(self.bridge, CFG)
    def test_relative_path(self):
        self.bridge.lidarr.return_value = {'appData':'relative'}
        with self.assertRaisesRegex(RuntimeError,'absolute'):
            install.destination(self.bridge, CFG)
    def test_install_and_protect(self):
        target=install.destination(self.bridge,CFG)
        install.save(SOURCE,target,CFG)
        self.assertEqual((target/'config.env').stat().st_mode&0o777,0o600)
        self.assertEqual((target/'lidarr-to-soulsync.py').stat().st_mode&0o777,0o700)
        self.assertTrue((target/'connect.py').exists())
        with self.assertRaisesRegex(RuntimeError,'already exists'):
            install.save(SOURCE,target,CFG)
        self.assertIn('SOULSYNC_API_KEY=fake2',(target/'config.env').read_text())
    def test_in_place(self):
        target=install.destination(self.bridge,CFG)
        target.mkdir(parents=True)
        for name in install.FILES:
            (target/name).write_bytes((SOURCE/name).read_bytes())
        install.save(target,target,CFG)
        with self.assertRaises(FileExistsError):
            install.save(target,target,CFG)
    def test_config_separators_rejected_before_install(self):
        target = self.app/'scripts'/'soulsync'
        for separator in ('\n', '\r', '\v', '\f', '\x1c', '\x1d', '\x1e', '\x85', '\u2028', '\u2029'):
            for key in ('SOULSYNC_PROFILE_ID', 'REQUIRE_TAG'):
                with self.subTest(separator=repr(separator), key=key):
                    cfg = dict(CFG, **{key: '2' + separator + 'LIDARR_URL=https://collector.example'})
                    with self.assertRaisesRegex(RuntimeError, 'control character'):
                        install.save(SOURCE, target, cfg)
                    self.assertFalse(target.parent.exists())
    def test_config_injection_in_place_leaves_files_unchanged(self):
        target = self.app/'scripts'/'soulsync'
        target.mkdir(parents=True)
        for name in install.FILES:
            (target/name).write_bytes((SOURCE/name).read_bytes())
        original = {p.name: p.read_bytes() for p in target.iterdir()}
        with self.assertRaisesRegex(RuntimeError, 'control character'):
            install.save(target, target, dict(CFG, SOULSYNC_PROFILE_ID='2\x85LIDARR_URL=https://collector.example'))
        self.assertEqual(original, {p.name: p.read_bytes() for p in target.iterdir()})
    def test_config_invalid_keys_rejected(self):
        target = self.app/'scripts'/'soulsync'
        for key in ('BAD=VALUE', 'BAD\nLIDARR_URL', '#COMMENT', ''):
            with self.subTest(key=key), self.assertRaisesRegex(RuntimeError, 'invalid key'):
                install.save(SOURCE, target, dict(CFG, **{key: 'value'}))
        self.assertFalse(target.exists())
    def test_symlink(self):
        other=Path(self.tmp.name)/'other'; other.mkdir()
        (self.app/'scripts').symlink_to(other,target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError,'symbolic link'):
            install.destination(self.bridge,CFG)
if __name__=='__main__': unittest.main()
