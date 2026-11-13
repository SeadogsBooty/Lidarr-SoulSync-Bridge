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

# Lidarr SoulSync Bridge v1.1.1

Import your Lidarr artists into SoulSync's Watchlist, keep future additions in sync, or do both.

## 1. Download

[Download the latest release](https://github.com/SeadogsBooty/Lidarr-SoulSync-Bridge/releases/latest), then extract the ZIP on the machine running Lidarr.

You need Python 3.8+ where Lidarr runs, your Lidarr API key (**Settings → General → Security**) and a SoulSync API key (**Settings → SoulSync API**). Both apps and public metadata services must be reachable. No pip packages needed.

**Docker?** Follow [Docker setup](DOCKER.md) to run the wizard inside the Lidarr container.

## 2. Run setup

From the extracted folder, as the Lidarr service user:

```sh
python3 setup.py
```

Enter the two server URLs and API keys. Then answer the wizard's menus:

| Prompt | What to enter |
| --- | --- |
| SoulSync profile | The number next to your desired Watchlist profile |
| What would you like to do? | **1** = import existing artists once; **2** = automatically sync new artists only; **3** = do both |
| Which artists? | **1** = monitored only (recommended); **2** = all artists, including unmonitored |
| Restrict to a Lidarr tag? | **no** = all artists in the chosen scope; **yes** = enter an existing Lidarr tag |
| Save configuration? | **yes** |

### What happens next?

**Option 1 — Existing artists:** The wizard previews your library. Enter `all` to import every proposed artist, or enter numbers such as `1,3,5` to import just those artists. Type `yes` to confirm. That's it; no ongoing sync is configured.

**Option 2 — New artists:** Type `yes` when asked to create the Lidarr connection. That's it. Add artists in Lidarr normally; the bridge syncs eligible new artists automatically.

**Option 3 — Both:** Approve the initial import as in option 1, then type `yes` to create the Lidarr connection as in option 2. Your existing artists are imported and new eligible artists sync automatically.

Existing Watchlist entries are preserved. Ambiguous matches are skipped for review. Press Enter at the import selection to skip it, or decline confirmation to cancel that import. Additions may trigger SoulSync downloads; use a Test profile and pause automatic downloads when testing.

## Manual setup or later imports

Prefer not to use the wizard? Follow [Manual installation](MANUAL.md) for file placement, configuration and the Lidarr Custom Script connection.

If you skipped the initial import or want to import more later, run this from the installed `scripts/soulsync` folder (mode 1 or 3):

```sh
python3 lidarr-to-soulsync.py --bulk --select
```

For automatic sync, no terminal needs to stay open. See [manual setup and recovery](MANUAL.md) for troubleshooting and [Docker setup](DOCKER.md) for containers.

Independent community project. [MIT license](LICENSE).
