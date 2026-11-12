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

Import artists from Lidarr into your SoulSync Watchlist and automatically sync new artists. Existing Watchlist entries are left alone.

**[Download v1.1 ZIP](https://github.com/SeadogsBooty/Lidarr-SoulSync-Bridge/releases/download/v1.1/Lidarr-SoulSync-Bridge-v1.1.zip)**

## 1. Before you start

- Lidarr and SoulSync must be running.
- Python 3.8+ must be installed **where Lidarr runs**. Check with `python3 --version`. No pip packages required.
- Get your Lidarr API key from **Settings → General → Security**.
- Get your SoulSync API key from **Settings → SoulSync API → Generate API Key**. Allow profile listing, artist search and Watchlist read/write.

Use a SoulSync Test profile and pause automatic downloads while trying the bridge. Both applications and outbound metadata APIs must be reachable from Lidarr.

**Running Lidarr in Docker?** Start with [Docker setup](DOCKER.md) to get the files and Python inside your Lidarr container, then return to step 2.

## 2. Install the bridge

Choose **A or B**, not both.

### A. Guided setup (recommended)

Download and extract the ZIP on the Linux machine running Lidarr. Open a terminal in the extracted folder (the folder containing `setup.py`). Run as the user that runs Lidarr. For example, on a native Linux install where the service user is `lidarr`:

```sh
sudo -u lidarr -H python3 setup.py
```

If you are already logged in as the Lidarr service user (including inside Docker), simply run `python3 setup.py`. The user must be able to read the extracted files and write to Lidarr's AppData. On native Linux, if Python is missing on Debian/Ubuntu, install it with `sudo apt-get install python3`.

The wizard asks for:

- Lidarr URL and API key.
- SoulSync URL and API key, then the Watchlist profile.
- Existing artists, future artists, or both. Choose **3 = Both** if you want to import your library and automatically sync new artists.
- Which artists to sync. Choose **1 = Monitored artists only** to start. An optional Lidarr tag can further restrict syncing.

Confirm saving by typing `yes`. If using future sync, also confirm creating the Lidarr connection.

**Done!** The wizard installs the files in Lidarr's AppData directory under `scripts/soulsync` and prints the exact installed path. It does not import any artists. Continue to step 3.

### B. Manual setup (no wizard)

**1. Put the files in Lidarr.** In Lidarr, open **System → Status** and find its AppData directory. Create a `scripts/soulsync` folder there and copy the extracted ZIP files into it. Use your file manager or run the following from the extracted folder as the Lidarr service user:

```sh
APPDATA="/path/to/lidarr-appdata"
DEST="$APPDATA/scripts/soulsync"
(umask 077; mkdir -p "$APPDATA/scripts" && mkdir "$DEST" && cp -R . "$DEST/")
```

Replace the AppData example with the path Lidarr reports. Common paths are `/var/lib/lidarr` (Linux) and `/config` (Docker). If the folder already exists, stop and review it; do not overwrite an existing configuration.

**2. Configure the bridge.** Open a terminal in the new `scripts/soulsync` folder (or run `cd "$DEST"` if you used the commands above) and run:

```sh
umask 077
cp -n config.env.example config.env
chmod 600 config.env
chmod 700 lidarr-to-soulsync.py
nano config.env
```

Enter your own values (the URLs below are examples):

```ini
LIDARR_URL=http://localhost:8686
LIDARR_API_KEY=YOUR_LIDARR_KEY
SOULSYNC_URL=http://your-soulsync-server:8008
SOULSYNC_API_KEY=YOUR_SOULSYNC_KEY
SOULSYNC_PROFILE_ID=YOUR_PROFILE_ID
SYNC_MODE=both
ARTIST_SCOPE=monitored
REQUIRE_TAG=
```

To find the profile ID, save your URLs and keys first, then run:

```sh
python3 -c 'import setup; print([(p["id"], p["name"]) for p in setup.bridge.profiles(setup.bridge.config())])'
```

Enter the ID of the desired profile in `config.env`. Use `SYNC_MODE=bulk` for existing artists only or `future` for new artists only. Leave `REQUIRE_TAG` empty unless you want to sync only artists with a specific Lidarr tag.

Keep the configuration private. The Lidarr service user must own or have access to the folder and files.

**3. Enable automatic sync (optional).** In Lidarr, go to **Settings → Connect → + → Custom Script**:

| Setting | Value |
| --- | --- |
| Name | SoulSync |
| On Artist Add | Enabled |
| Other triggers | Disabled |
| Path | Full installed path to `lidarr-to-soulsync.py` |
| Arguments / Tags | Leave blank |

For example, the path may be `/var/lib/lidarr/scripts/soulsync/lidarr-to-soulsync.py` or `/config/scripts/soulsync/lidarr-to-soulsync.py`. Click **Test**, then **Save**. Skip this connection if you only want to import existing artists.

## 3. Use the bridge

Open a terminal in the **installed** `scripts/soulsync` folder as the Lidarr service user. Use the path printed by guided setup, or the folder you created manually. If you chose future-only mode, skip the bulk commands and test by adding a new artist in Lidarr.

**Preview your first five artists (nothing is added):**

```sh
python3 lidarr-to-soulsync.py --bulk --limit 5
```

**Preview all and choose which artists to import:**

```sh
python3 lidarr-to-soulsync.py --bulk --select
```

Enter the numbers of the artists you want, separated by commas, then type `yes`. Press Enter without selecting anything to cancel.

**Import all eligible artists:** preview first with `python3 lidarr-to-soulsync.py --bulk`, then run:

```sh
python3 lidarr-to-soulsync.py --bulk --apply
```

Bulk commands require bulk or both mode. If you enabled future sync, add a new eligible artist in Lidarr to test it. The Custom Script runs automatically.

## Help

- [Docker setup](DOCKER.md) — install Python and run the wizard inside Lidarr.
- `python3 lidarr-to-soulsync.py --review` — see unresolved recorded attempts.
- `python3 lidarr-to-soulsync.py --help` — all commands, including single-artist and retry options.

The bridge leaves ambiguous artists for review and never automatically deletes existing Watchlist entries. Review proposed additions before applying. Deezer writes have been live-tested; other supported provider writes have automated coverage but await live validation. See [release notes](https://github.com/SeadogsBooty/Lidarr-SoulSync-Bridge/releases/tag/v1.1) for details and [changelog](CHANGELOG.md) for updates.

Independent community project. [MIT license](LICENSE).
