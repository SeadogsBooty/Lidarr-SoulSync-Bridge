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

"""Install the bridge in Lidarr's reported AppData, without replacing files."""
import hmac
import os
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

FILES = ('lidarr-to-soulsync.py', 'setup.py', 'connect.py', 'install.py', 'README.md', 'config.env.example', 'LICENSE', 'DOCKER.md', 'MANUAL.md')


def destination(bridge, cfg):
    status = bridge.lidarr(cfg, '/api/v1/system/status')
    raw = status.get('appData') if isinstance(status, dict) else None
    if not isinstance(raw, str) or not Path(raw).is_absolute():
        raise RuntimeError('Lidarr did not report an absolute AppData path. No installation made.')
    appdata = Path(raw).resolve()
    # Guard against running on the wrong host or outside the Lidarr container.
    try:
        key = ET.parse(appdata / 'config.xml').getroot().findtext('ApiKey')
    except (OSError, ET.ParseError):
        raise RuntimeError('Cannot read Lidarr config.xml at its reported AppData path. Run setup in Lidarr’s own environment as its service account.') from None
    if not key or not hmac.compare_digest(key.strip(), cfg['LIDARR_API_KEY']):
        raise RuntimeError('The local Lidarr config.xml does not match the connected instance. Run setup on the correct Lidarr host/container.')
    scripts = appdata / 'scripts'
    target = scripts / 'soulsync'
    if scripts.is_symlink() or target.is_symlink():
        raise RuntimeError('Installation path contains a symbolic link. No installation made; review the directory first.')
    return target


def validate_config(cfg):
    """Reject settings that could become extra lines when config is reloaded."""
    for key, value in cfg.items():
        if (not isinstance(key, str) or not re.fullmatch(r'[A-Z][A-Z0-9_]*', key)
                or not isinstance(value, str)
                or any(ord(c) < 32 or 127 <= ord(c) <= 159 or c in '\u2028\u2029'
                       for c in value)):
            raise RuntimeError('Configuration contains an invalid key or control character. No configuration saved.')


def save(source, target, cfg):
    validate_config(cfg)
    source, target = Path(source).resolve(), Path(target)
    if target.is_symlink() or target.parent.is_symlink():
        raise RuntimeError('Installation path contains a symbolic link.')
    same = source == target.resolve()
    created = False
    if not same:
        if target.exists():
            raise RuntimeError('Destination already exists. No files overwritten. Use the installed setup.py or back up and review that folder first.')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.mkdir(mode=0o700)
        created = True
    config = target / 'config.env'
    try:
        if not same:
            for name in FILES:
                shutil.copyfile(source / name, target / name)
                (target / name).chmod(0o700 if name.endswith('.py') else 0o600)
        else:
            # In-place installs already have the packaged files.
            for name in FILES:
                if not (target / name).is_file():
                    raise RuntimeError('Installation files are missing. Extract the complete ZIP first.')
            (target / 'lidarr-to-soulsync.py').chmod(0o700)
        fd = os.open(config, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            for k, v in cfg.items():
                f.write(f'{k}={v}\n')
    except Exception:
        if created:
            # Only remove our newly created directory, never an existing one.
            shutil.rmtree(target)
        raise
    return target
