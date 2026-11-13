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

"""Scan reachable Git blobs for common credential patterns without printing secrets.

This is a targeted secret-pattern check, not a substitute for GitHub secret
scanning, a dedicated scanner or manual review.
"""
import re
import subprocess
import sys

RULES = {
    'github-token': rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})',
    'aws-access-key': rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
    'private-key': rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----',
    'openai-key': rb'\bsk-(?:proj-)?[A-Za-z0-9_-]{30,}',
    'service-api-key': rb'(?im)^\s*(?:LIDARR_API_KEY|SOULSYNC_API_KEY)\s*=\s*["\']?[A-Za-z0-9]{24,}["\']?\s*$',
}


def git(*args, data=None):
    return subprocess.check_output(['git', *args], input=data)


def main():
    objects = git('rev-list', '--objects', '--all').splitlines()
    ids = [row.split(b' ', 1)[0] for row in objects]
    kinds = git('cat-file', '--batch-check=%(objectname) %(objecttype)', data=b'\n'.join(ids)+b'\n').splitlines()
    count = 0
    found = 0
    for row in kinds:
        oid, kind = row.split()
        if kind != b'blob':
            continue
        count += 1
        blob = git('cat-file', 'blob', oid.decode('ascii'))
        for rule, pattern in RULES.items():
            if re.search(pattern, blob):
                # Never output matched content, names, or credentials.
                print('Potential secret:', rule, 'blob', oid.decode('ascii'))
                found += 1
    print('Scanned', count, 'unique reachable Git blobs;', found, 'pattern findings.')
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main())
