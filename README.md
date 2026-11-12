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

Import Lidarr artists into your SoulSync Watchlist and automatically sync new artists. Existing Watchlist entries are preserved. Matching follows SoulSync's search provider and uses MusicBrainz to resolve identities.

## 1. Requirements

- Lidarr and SoulSync running; both must be reachable from **Lidarr's own Linux host or container**.
- Python 3.8+ in that environment (standard library only; no `pip install`). Check `python3 --version`. On Debian/Ubuntu: `sudo apt-get install python3`.
- Lidarr API key: **Settings → General → Security**. SoulSync API key: **Settings → SoulSync API → Generate API Key** (labels may vary). Allow profile listing, artist search, Watchlist read/write. Keep both keys private.
- Outbound HTTPS to MusicBrainz and supported public metadata APIs. Pause SoulSync auto-downloads while testing, preferably in a separate Test profile.

## 2. Download and install (choose A or B)

Download **[Lidarr-SoulSync-Bridge-v1.1.zip](https://github.com/SeadogsBooty/Lidarr-SoulSync-Bridge/releases/download/v1.1/Lidarr-SoulSync-Bridge-v1.1.zip)** from the [v1.1 release](https://github.com/SeadogsBooty/Lidarr-SoulSync-Bridge/releases/tag/v1.1) and extract it. No Git or additional Python packages are needed. Run commands as the Lidarr service account, not as an unrelated user.

### A. Guided setup (recommended)

In the extracted folder run:

```sh
python3 setup.py
```

Enter the two server URLs and API keys, choose your SoulSync profile, then select **existing artists**, **future artists**, or **both**. Choose monitored/all and an optional Lidarr tag. Confirm saving; for future sync, confirm creation of the Lidarr connection. The wizard finds Lidarr's AppData and installs to `scripts/soulsync` inside it. Use the installed path it prints for all later commands.

### B. Manual setup (no wizard)

1. In Lidarr **System → Status**, find the AppData directory. From the extracted folder, run the commands below as the Lidarr service account. Replace `/path/to/lidarr-appdata` with that directory (often `/var/lib/lidarr` or `/config` in Docker). Stop if the destination already exists; these commands deliberately refuse to replace it.

   ```sh
   APPDATA='/path/to/lidarr-appdata'
   (umask 077; mkdir -p "$APPDATA/scripts" && mkdir "$APPDATA/scripts/soulsync" && cp -R . "$APPDATA/scripts/soulsync/")
   cd "$APPDATA/scripts/soulsync"
   chmod 700 .
   ```
2. Open a shell in that folder. Run:

   ```sh
   umask 077
   cp -n config.env.example config.env
   chmod 600 config.env
   chmod 700 lidarr-to-soulsync.py
   nano config.env  # or vi / your preferred editor
   ```

   Set `LIDARR_URL`, `LIDARR_API_KEY`, `SOULSYNC_URL`, `SOULSYNC_API_KEY` and your intended `SOULSYNC_PROFILE_ID`. To list profile names and IDs after setting the URLs/keys, run `python3 -c 'import setup; print(setup.bridge.profiles(setup.bridge.config()))'`. Set `SYNC_MODE=both` (or `bulk` / `future`), `ARTIST_SCOPE=monitored` (or `all`), and optionally `REQUIRE_TAG=your-existing-tag`. Save the file. Never publish `config.env`.
3. For automatic sync, in Lidarr **Settings → Connect → + → Custom Script**, name it `SoulSync`, enable **On Artist Add** only, set **Path** to the absolute installed `lidarr-to-soulsync.py` path, leave arguments blank if offered, and leave Lidarr connection tags empty (the bridge applies its own optional tag filter). Click **Test**, then **Save**. Alternatively run `python3 setup.py --connect` and confirm. Bulk-only mode needs no connection.

### Docker

Use the same instructions **inside the Lidarr container**, not the SoulSync container. For example, extract the ZIP into a staging folder in the persistent Lidarr config mount (`/config/bridge-staging`), then run `docker exec -it -u <lidarr-service-uid> <lidarr-container> python3 /config/bridge-staging/setup.py` for guided setup. For manual setup copy files into the mounted `/config/scripts/soulsync` directory and enter the container with `docker exec -it -u <lidarr-service-uid> <lidarr-container> sh`. Replace placeholders with your container and service UID. Python must be in the image; if missing, use a persistent custom image installing Python (see [Docker prerequisites](DOCKER.md)). Use network-reachable addresses: `localhost` means the current container. The `/config` mount preserves the installation across container recreation.

## 3. Use the bridge

Run from the installed `scripts/soulsync` folder (bulk/both mode for bulk commands):

```sh
python3 lidarr-to-soulsync.py --bulk --limit 5  # Preview five; no writes
python3 lidarr-to-soulsync.py --bulk          # Preview all eligible artists
python3 lidarr-to-soulsync.py --bulk --select # Choose artists, then confirm
```

For `--select`, enter comma-separated numbers and type `yes` to add only those artists. Enter alone cancels. When satisfied, `python3 lidarr-to-soulsync.py --bulk --apply` adds all eligible resolved artists. In future/both mode, adding a new eligible artist to Lidarr triggers the Custom Script automatically. Test with one desired artist first.

**Connection check:** For future/both mode, `env Lidarr_EventType=Test python3 lidarr-to-soulsync.py` checks connectivity without adding artists. Bulk-only users can use the five-artist preview above.

**Recovery:** `python3 lidarr-to-soulsync.py --review` shows unresolved recorded attempts. Use `--artist-name "Artist Name"` to preview one artist, add `--apply` to retry, or use `--retry-all` (add `--apply` to write). `--artist 123` selects a Lidarr ID; `--provider-id deezer:456` selects a manually verified candidate for a single artist. Use `--help` for all options. Exit code 2 means review needed; 1 means error. Preview reviews are not recorded; actual attempts are recorded privately in `activity.jsonl`.

## Notes

- No automatic deletion or modification of existing Watchlist entries. Additions use SoulSync defaults. Ambiguous identities may require review; no automatic provider switching. Some exact-name matches lack independent identity evidence; verify proposed additions before applying.
- Deezer writes and cross-provider recognition are live-tested; Spotify, MusicBrainz, iTunes, Discogs and Amazon write paths have automated tests but await live provider-specific validation. Direct-ID lookup is available for Deezer, iTunes and MusicBrainz only. Other providers use SoulSync search and identity links. iTunes lookup uses the US storefront by default.
- Validation: 94 original tests plus 4 configuration-safety regressions (98 total). CI runs the suite on Linux, including the minimum Python 3.8. Public-release validation uses mocks and temporary fixtures, without contacting production instances.
- Native Linux and a Docker installation have been tested. Image-specific dependency setup varies. Never run simultaneous imports from different bridge installations. Existing installs: back up and replace the packaged Python/README files, preserve `config.env`, `activity.jsonl`, ownership and Lidarr connection.

Independent community project; not an official Lidarr or SoulSync integration. [MIT license](LICENSE).
