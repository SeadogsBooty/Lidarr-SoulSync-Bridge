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

"""Build the end-user installation ZIP from the installer's exact file list."""
import argparse
import re
import stat
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from install import FILES

ROOT = Path(__file__).resolve().parent


def version(root=ROOT):
    value = (root / 'VERSION').read_text(encoding='utf-8').strip()
    if not re.fullmatch(r'\d+\.\d+(?:\.\d+)?', value):
        raise ValueError('VERSION must be a numeric release version, e.g. 1.1.2')
    if 'bridge v' + value + '.' not in (root / 'lidarr-to-soulsync.py').read_text(encoding='utf-8'):
        raise ValueError('VERSION and bridge version do not match')
    return value


def build(output_dir, root=ROOT):
    """Write only the named installer files; no local config, logs or tests."""
    root = Path(root)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / ('Lidarr-SoulSync-Bridge-v' + version(root) + '.zip')
    for name in FILES:
        source = root / name
        if not source.is_file() or source.is_symlink():
            raise ValueError('Missing or unsafe release file: ' + name)
    with ZipFile(archive, 'w', compression=ZIP_DEFLATED) as package:
        for name in FILES:
            entry = ZipInfo(name)
            entry.create_system = 3
            mode = 0o755 if name in ('setup.py', 'lidarr-to-soulsync.py') else 0o644
            entry.external_attr = (stat.S_IFREG | mode) << 16
            package.writestr(entry, (root / name).read_bytes(), compress_type=ZIP_DEFLATED)
    with ZipFile(archive) as package:
        if tuple(package.namelist()) != FILES or package.testzip() is not None:
            raise ValueError('Invalid installation archive')
        for name in FILES:
            if package.read(name) != (root / name).read_bytes():
                raise ValueError('Archive content mismatch: ' + name)
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    print(build(args.output_dir))


if __name__ == '__main__':
    main()
