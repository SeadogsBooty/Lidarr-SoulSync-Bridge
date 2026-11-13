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

Import existing Lidarr artists into SoulSync, automatically sync future additions, or both. Existing Watchlist entries stay unchanged.

## 1. Download

**[Download v1.1.1 ZIP](https://github.com/SeadogsBooty/Lidarr-SoulSync-Bridge/releases/download/v1.1.1/Lidarr-SoulSync-Bridge-v1.1.1.zip)** and extract it. You need Python 3.8+ on Lidarr's Linux host, running Lidarr/SoulSync, API keys and network access to both apps and public metadata services. No pip packages.

Get the Lidarr key from **Settings → General → Security**; get the SoulSync key from **Settings → SoulSync API**, allowing profile listing, search and Watchlist read/write. **Docker:** follow [DOCKER.md](DOCKER.md); run inside the Lidarr container.

> **Important — let SoulSync handle downloads:** If SoulSync will manage your music downloads, disable Lidarr's downloading automation before using the bridge. In Lidarr, go to **Settings → Download Clients** and disable its download clients (or otherwise prevent Lidarr from sending downloads). This avoids duplicate downloads, competing imports and conflicts in your music library. Keep artist monitoring enabled if using the bridge's monitored-only mode, and leave the SoulSync Custom Script connection enabled for future sync. If you still use Lidarr to download other music, use separate libraries/workflows so the two apps do not manage the same files.

## 2. Run setup

In the extracted folder, as the Lidarr service user:

```sh
python3 setup.py
```

Answer these prompts in order. Enter accepts a displayed default; API keys are hidden.

| Prompt | Answer / effect |
| --- | --- |
| Lidarr address | Your URL; default `http://localhost:8686` |
| Lidarr API key (hidden) | Your Lidarr key |
| SoulSync address | Your URL; default `http://localhost:8008` (not localhost for a separate container) |
| SoulSync API key (hidden) | Your SoulSync key |
| Choose profile by menu number | Desired profile number; only shown if multiple profiles exist |
| Choose 1, 2 or 3 | **1** existing artists only (default); **2** future artists only; **3** both |
| Choose 1 or 2 | **1** monitored artists only (default); **2** all, including unmonitored |
| Restrict to a Lidarr tag? | `no` (default), or `yes` |
| Required tag | Existing tag name; only asked after `yes` |
| Save configuration? | Type `yes` to install; Enter/anything else cancels setup |
| Enter all, comma-separated numbers, or Enter to cancel | Modes **1/3**, after preview: `all`, numbers such as `1,3`, or Enter to skip |
| Type yes to add these artists | Modes **1/3**, after selection: `yes` imports; anything else cancels import |
| Create and test the SoulSync connection in Lidarr? | Modes **2/3**: `yes` tests and creates Artist Add automation; Enter/anything else leaves it disabled |

**1 — Existing only:** preview → select → confirm → import. No Lidarr connection.

**2 — Future only:** confirm → test/create connection. No initial import. Add artists in Lidarr normally afterward.

**3 — Both:** initial preview/selection/confirmed import, then confirmed connection setup. No extra commands or open terminal needed after successful completion. Skipping the import still offers future sync.

Unresolved identities are skipped and reported for review. If nothing can be added, no import confirmation appears. Adding artists may trigger SoulSync downloads; use a Test profile and pause downloads when testing.

[Manual installation, later imports and recovery](MANUAL.md) · [Docker setup](DOCKER.md) · [Release notes](https://github.com/SeadogsBooty/Lidarr-SoulSync-Bridge/releases/tag/v1.1.1)

Independent community project. [MIT license](LICENSE).
