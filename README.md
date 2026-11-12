```text
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
```

# Lidarr SoulSync Bridge v1.1

Sync your Lidarr artists to your SoulSync Watchlist. Import your existing library, automatically sync new artists, or do both. Existing Watchlist entries are preserved.

**[Download v1.1 ZIP](https://github.com/SeadogsBooty/Lidarr-SoulSync-Bridge/releases/download/v1.1/Lidarr-SoulSync-Bridge-v1.1.zip)**

## 1. Before you start

- Lidarr and SoulSync must be running and reachable from Lidarr.
- Python 3.8+ installed where Lidarr runs (`python3 --version`). No pip packages needed.
- Lidarr API key: **Settings → General → Security**.
- SoulSync API key: **Settings → SoulSync API → Generate API Key**. Allow profile listing, artist search and Watchlist read/write.

If you're testing, use a SoulSync Test profile and pause automatic downloads.

**Docker users:** Follow [Docker setup](DOCKER.md) first. The bridge runs inside the **Lidarr** container, not SoulSync.

## 2. Install the bridge

### A. Guided setup (recommended)

1. Download and extract the ZIP on the machine running Lidarr.
2. Open a terminal in the extracted folder containing `setup.py`, as the Lidarr service user.
3. Run:

```sh
python3 setup.py
```

On native Linux, if your Lidarr service runs as user `lidarr`, you can instead run `sudo -u lidarr -H python3 setup.py` from the extracted folder. That user must be able to read the files.

Enter your Lidarr and SoulSync URLs and API keys, then choose your SoulSync profile. Select **3 = Both** to import existing artists and sync future additions, or choose only the mode you need. Select **1 = Monitored artists only** to start.

Type `yes` to save. If enabling future sync, also confirm creating the Lidarr connection.

**Setup is complete.** The wizard installs the bridge in Lidarr's AppData under `scripts/soulsync` and prints the installed path. It does not import any artists yet.

### B. Manual setup (no wizard)

Prefer to install the files yourself? Follow the **[manual installation guide](https://github.com/SeadogsBooty/Lidarr-SoulSync-Bridge/blob/main/MANUAL.md)**. It walks you through copying the files, editing `config.env`, setting permissions and creating the Lidarr Custom Script connection.

## 3. Use the bridge

Open a terminal in the **installed** `scripts/soulsync` folder, using the Lidarr service user.

**Preview five artists — nothing is added:**

```sh
python3 lidarr-to-soulsync.py --bulk --limit 5
```

**Choose which artists to import:**

```sh
python3 lidarr-to-soulsync.py --bulk --select
```

Enter the desired artist numbers, separated by commas, then type `yes` to add them. Press Enter without selecting anything to cancel.

**Import everything:** run `python3 lidarr-to-soulsync.py --bulk` to preview all, then `python3 lidarr-to-soulsync.py --bulk --apply` to add all resolved eligible artists.

**Automatic sync:** If you enabled future sync, add a new eligible artist in Lidarr. The bridge runs automatically. Future-only mode does not use bulk commands.

## Need help?

[Manual setup and recovery](https://github.com/SeadogsBooty/Lidarr-SoulSync-Bridge/blob/main/MANUAL.md) · [Docker setup](DOCKER.md) · [Release notes](https://github.com/SeadogsBooty/Lidarr-SoulSync-Bridge/releases/tag/v1.1)

Run `python3 lidarr-to-soulsync.py --review` for unresolved recorded attempts or `--help` for all commands.

Independent community project. [MIT license](LICENSE).
