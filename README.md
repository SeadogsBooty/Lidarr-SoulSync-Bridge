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

# Lidarr SoulSync Bridge

Keep your Lidarr artists synchronized with your SoulSync Watchlist.

**Use Lidarr to manage your artists and SoulSync to download your music.**

## What does it do?

- Import your existing Lidarr artists into SoulSync.
- Automatically add new Lidarr artists to SoulSync.
- Prevent duplicate artists from being added to your Watchlist.
- Leave your existing SoulSync Watchlist entries untouched.

## Getting Started

### 1. Before You Begin

You will need:

- Lidarr and SoulSync running.
- Python 3.8 or newer installed where Lidarr runs.
- Your Lidarr and SoulSync API keys.

**Where to find your API keys:**

| Application | Location |
|---|---|
| Lidarr | Settings → General → Security |
| SoulSync | Settings → SoulSync API |

**IMPORTANT:** If SoulSync will manage your music downloads, disable Lidarr's download clients and downloading automations before continuing. Leave artist monitoring enabled. This prevents both applications from downloading and managing the same music.

### 2. Download & Run Setup

[**Download the latest release**](https://github.com/SeadogsBooty/Lidarr-SoulSync-Bridge/releases/latest)

Extract the ZIP on the machine running Lidarr.

Open a terminal in the extracted folder as the Lidarr service user and run:

```bash
python3 setup.py
```

**Using Docker?** Follow the [Docker Setup Guide](DOCKER.md) to run setup inside your Lidarr container.

### 3. Follow the Setup Wizard

The wizard will ask for your Lidarr and SoulSync addresses, API keys, and which SoulSync profile you want to use.

Next, choose how you want the bridge to work.

**What would you like to do?**

| Option | Description |
|---|---|
| 1 | Import your existing Lidarr artists into SoulSync. |
| 2 | Automatically sync new artists added to Lidarr. |
| 3 | Import existing artists AND automatically sync new artists. |

**Recommended: Option 3** if you want to migrate your existing library and keep it synchronized going forward.

**Which artists would you like to sync?**

| Option | Description |
|---|---|
| 1 | Monitored artists only. |
| 2 | All artists, including unmonitored artists. |

**Recommended: Option 1**

The wizard will also ask if you want to restrict synchronization to a specific Lidarr tag.

Choose `no` to include all artists within your selected scope, or `yes` to use an existing Lidarr tag.

Type `yes` to save your configuration and complete the remaining setup prompts.

### 4. You're Ready!

**If you chose Option 1 — Import Existing Artists**

The wizard will preview your existing artists.

- Enter `all` to import all proposed artists.
- Or enter individual numbers, such as `1,3,5`, to import specific artists.
- Type `yes` to confirm.

Your selected artists will be added to SoulSync. No automatic synchronization is configured.

**If you chose Option 2 — Sync New Artists**

Type `yes` when asked to create the Lidarr connection.

That's it! Simply add artists in Lidarr as you normally would. The bridge automatically adds eligible artists to SoulSync.

**If you chose Option 3 — Both**

The wizard will guide you through importing your existing artists and then ask to create the Lidarr connection.

Once both steps are complete, you're done!

**Your existing artists are imported, and new artists will automatically sync to SoulSync whenever you add them to Lidarr.**

No additional commands are required, and you do not need to leave a terminal open.

---

## Manual Installation

Prefer to install and configure everything yourself?

Follow the [Manual Installation Guide](MANUAL.md) for file placement, configuration, and setting up the Lidarr Custom Script connection.

## Additional Information

- Existing Watchlist entries will not be deleted or modified.
- Artists that cannot be confidently matched are skipped for manual review.
- Adding artists to SoulSync may trigger its downloading automations.
- For testing, we recommend using a SoulSync Test profile with automatic downloads paused.

[Manual Setup & Troubleshooting](MANUAL.md) · [Docker Setup](DOCKER.md) · [Latest Release](https://github.com/SeadogsBooty/Lidarr-SoulSync-Bridge/releases/latest)

---

Created by **SeadogsBooty**

Independent community project — [MIT License](LICENSE).
