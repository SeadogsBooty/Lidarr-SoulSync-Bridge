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

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

import build_release
import install

EXPECTED = {
    'lidarr-to-soulsync.py', 'setup.py', 'connect.py', 'install.py',
    'config.env.example', 'README.md', 'DOCKER.md', 'MANUAL.md', 'LICENSE',
}


class ReleasePackageTests(unittest.TestCase):
    def test_exact_installation_files_and_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = build_release.build(Path(tmp))
            with ZipFile(archive) as package:
                self.assertEqual(set(package.namelist()), EXPECTED)
                self.assertEqual(len(package.namelist()), len(EXPECTED))
                self.assertIsNone(package.testzip())
                for name in EXPECTED:
                    self.assertEqual(package.read(name), (build_release.ROOT / name).read_bytes())
                for name in ('setup.py', 'lidarr-to-soulsync.py'):
                    self.assertEqual((package.getinfo(name).external_attr >> 16) & 0o777, 0o755)
                self.assertNotIn(b'NOT ALL BOOTY COMES IN A CHEST.', package.read('README.md'))
                for name in EXPECTED:
                    if name.endswith('.py'):
                        self.assertIn(b'NOT ALL BOOTY COMES IN A CHEST.', package.read(name))

    def test_package_can_install_from_staging_or_in_place(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = build_release.build(root)
            source = root / 'extracted'
            with ZipFile(archive) as package:
                package.extractall(source)
            cfg = {'LIDARR_API_KEY':'example', 'SOULSYNC_API_KEY':'example'}
            target = root / 'lidarr' / 'scripts' / 'soulsync'
            install.save(source, target, cfg)
            self.assertEqual({p.name for p in target.iterdir()}, EXPECTED | {'config.env'})
            self.assertEqual((target / 'config.env').stat().st_mode & 0o777, 0o600)
            self.assertEqual((target / 'lidarr-to-soulsync.py').stat().st_mode & 0o777, 0o700)
            install.save(source, source, cfg)
            self.assertTrue((source / 'config.env').is_file())

    def test_extracted_entrypoints_need_no_development_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = build_release.build(root)
            source = root / 'extracted'
            with ZipFile(archive) as package:
                package.extractall(source)
            for name in ('setup.py', 'lidarr-to-soulsync.py'):
                result = subprocess.run([sys.executable, '-B', str(source / name), '--help'],
                                        cwd=str(source), capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('usage:', result.stdout.lower())


if __name__ == '__main__':
    unittest.main()
