# Manual installation (no wizard)

[Download and extract the latest release](https://github.com/SeadogsBooty/Lidarr-SoulSync-Bridge/releases/latest) first. Select the named installation ZIP under Assets, not GitHub's Source code ZIP. Python 3.8+ must be installed where Lidarr runs. Get both API keys as described in the [README](README.md#1-download). If using Docker, first see [Docker setup](DOCKER.md). Use the Lidarr service user for all commands; on a native Linux install where that user is `lidarr`, you can enter its shell with `sudo -u lidarr -H sh`. Ensure the extracted files are readable by that user.

**1. Put the files in Lidarr.** In Lidarr, open **System → Status** and find its AppData directory. Create a `scripts/soulsync` folder there and copy the nine extracted installation ZIP files into it. The test suite and GitHub development files are not needed. Use your file manager or run the following from the extracted folder as the Lidarr service user:

```sh
APPDATA="/path/to/lidarr-appdata"
DEST="$APPDATA/scripts/soulsync"
(umask 077; mkdir -p "$APPDATA/scripts" && mkdir "$DEST" && cp -R . "$DEST/")
```

Replace the AppData example with the path Lidarr reports. Common paths are `/var/lib/lidarr` (Linux) and `/config` (Docker). If the folder already exists, stop and review it; do not overwrite an existing configuration.

**2. Configure the bridge.** Open a terminal as the Lidarr service user in the new `scripts/soulsync` folder (or run `cd "$DEST"` if you used the commands above). Run:

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

## Test and use

From the installed folder, run `python3 lidarr-to-soulsync.py --bulk --select` in bulk/both mode. Enter `all` or comma-separated artist numbers and confirm with `yes`. For a read-only preview use `--bulk` or `--bulk --limit 5`. For future/both mode, the Lidarr connection's **Test** button checks connectivity without adding an artist.

To have the bridge create the Custom Script connection instead of configuring it in the UI, run `python3 setup.py --connect` from the installed folder and confirm. No connection is required in bulk-only mode.

For a noninteractive import, first preview with `python3 lidarr-to-soulsync.py --bulk`, then explicitly apply with `python3 lidarr-to-soulsync.py --bulk --apply`. Interactive `--bulk --select` always asks for selection and confirmation, including when you enter `all`. Canceling the initial import in the wizard does not prevent it offering future sync in both mode.

## Troubleshooting and recovery

| Command (run with `python3 lidarr-to-soulsync.py`) | What it does |
| --- | --- |
| `--review` | Show unresolved recorded sync attempts |
| `--artist-name "Artist Name"` | Preview a single artist |
| `--artist-name "Artist Name" --apply` | Retry that artist |
| `--retry-all` | Preview recorded unresolved attempts |
| `--retry-all --apply` | Apply retries |
| `--help` | Show all options |

Exit code 2 means manual review is needed; 1 means an error. Previews do not record attempts. Actual attempts are recorded in private `activity.jsonl`. Do not share that file or `config.env`.

Unresolved artists from the wizard's preview are shown in its summary but are not written to activity history. Use `--bulk --select` to review them again, or preview an exact artist name before retrying. In both mode, unresolved imports still allow the automatic connection to be configured; the wizard retains exit code 2.

Matching follows SoulSync's search provider. Ambiguous identities are left for review; some exact-name matches lack independent identity evidence, so check proposed additions before applying. Deezer writes have been live-tested; other supported providers have automated coverage but await provider-specific live validation. Direct lookup supports Deezer, iTunes and MusicBrainz; iTunes defaults to the US storefront.

Existing installations: back up first, preserve `config.env`, `activity.jsonl`, ownership and the Lidarr connection. Never run simultaneous imports from different installations.
