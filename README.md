# Lidarr SoulSync Bridge

**Your Lidarr artists. Your SoulSync Watchlist. Connected.**

Manage artists in Lidarr. Download music with SoulSync.

[**Download the latest release**](https://github.com/SeadogsBooty/Lidarr-SoulSync-Bridge/releases/latest) · [Docker Setup](DOCKER.md) · [Manual Setup](MANUAL.md) · [Report an Issue](https://github.com/SeadogsBooty/Lidarr-SoulSync-Bridge/issues)

---

## How it works

| Lidarr | The Bridge | SoulSync |
| :---: | :---: | :---: |
| Manage your artists | Import and automatically sync artists | Manage your Watchlist and downloads |

Import your existing artists, sync new additions automatically, or do both. The bridge avoids duplicate entries and leaves your existing SoulSync Watchlist untouched.

## Getting started

### 1. Download

[**Download the latest ZIP**](https://github.com/SeadogsBooty/Lidarr-SoulSync-Bridge/releases/latest) and extract it on the machine running Lidarr.

Under **Assets**, choose the file named `Lidarr-SoulSync-Bridge-v1.1.2.zip` (or the named installation ZIP for a newer release), not GitHub's **Source code** ZIP. The installation ZIP contains only the nine files needed for setup. You can extract them directly into Lidarr's `scripts/soulsync` folder or let the wizard install them for you.

You'll need:

- Lidarr and SoulSync running and reachable from Lidarr.
- Python 3.8 or newer installed where Lidarr runs. No additional Python packages required.
- API keys for both applications.

| API key | Where to find it |
| --- | --- |
| Lidarr | **Settings → General → Security** |
| SoulSync | **Settings → SoulSync API** (allow profile listing, artist search and Watchlist read/write) |

> [!IMPORTANT]
> **Let SoulSync handle downloads.** If SoulSync manages your music, disable Lidarr's downloading automations and download clients before continuing (Settings → Download Clients). Keep artist monitoring enabled for monitored-only sync. This prevents duplicate downloads and competing imports. If both apps download music, use separate workflows or libraries.

### 2. Run setup

Open a terminal in the extracted folder as the Lidarr service user and run:

```bash
python3 setup.py
```

**Using Docker?** Follow the [Docker Setup Guide](DOCKER.md) to run setup inside your Lidarr container.

### 3. Follow the setup wizard

Enter your Lidarr and SoulSync URLs and API keys, then choose your SoulSync profile using the number shown.

**What would you like to do?**

| Enter | What happens |
| :---: | --- |
| `1` | Import your existing Lidarr artists once. |
| `2` | Automatically sync new artists added to Lidarr. |
| `3` | **Both** — import existing artists and automatically sync new ones. |

**Recommended:** Choose `3` if you want to import your library and keep new additions synchronized.

**Which artists would you like to sync?**

| Enter | Which artists |
| :---: | --- |
| `1` | Monitored artists only (recommended). |
| `2` | All artists, including unmonitored artists. |

When asked about a Lidarr tag, enter `no` to include all artists in your chosen scope, or `yes` to restrict sync to an existing tag.

Type `yes` to save your configuration. The wizard installs the bridge and guides you through the remaining steps.

### 4. You're ready!

**Option 1 — Existing artists only**

The wizard previews your existing artists. Enter `all` to import every proposed artist, or enter numbers such as `1,3,5` to choose specific artists. Type `yes` to confirm. Your selected artists are added to SoulSync; no ongoing connection is configured.

**Option 2 — New artists only**

Type `yes` to create and test the Lidarr connection. Once confirmed, simply add artists in Lidarr as you normally would. New eligible artists sync automatically.

**Option 3 — Both**

Approve the initial import as in Option 1, then confirm creating the Lidarr connection as in Option 2. Your selected existing artists are imported, and future eligible additions sync automatically.

> [!TIP]
> After successful automatic connection setup, you can close the terminal. There's no additional command to run or process to keep open.

## Good to know

- Ambiguous artist matches are skipped for manual review.
- Existing Watchlist entries are not deleted or modified.
- Adding artists to SoulSync may trigger its download automations. Use a Test profile and pause automatic downloads when testing.

## More ways to get started

| Guide | What's inside |
| --- | --- |
| [Manual installation](MANUAL.md) | Install the files yourself, edit the configuration and create the Lidarr connection. |
| [Docker setup](DOCKER.md) | Install and run the bridge inside your Lidarr container. |
| [Later imports & troubleshooting](MANUAL.md) | Import more artists, review unresolved matches and retry. |
| [Releases](https://github.com/SeadogsBooty/Lidarr-SoulSync-Bridge/releases/latest) | Download the latest version and see what's changed. |

---

Built by [**SeadogsBooty**](https://github.com/SeadogsBooty) · Independent community project · [MIT License](LICENSE)
