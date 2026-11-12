# Docker setup

Use this guide if Lidarr runs in Docker. The bridge runs **inside the Lidarr container**, not inside SoulSync and not just on the Docker host.

## 1. Check Python

On the machine running Docker, run:

```sh
docker ps
docker exec lidarr python3 --version
```

Replace `lidarr` with your actual container name throughout this guide. Python 3.8 or newer is required. If the command works, go to step 2. If it fails, see [Installing Python](#installing-python) below.

## 2. Download and copy the files

The following example uses a LinuxServer Lidarr container with service user `abc` and persistent configuration at `/config`. For a different image, use its actual Lidarr service user and AppData path (shown in Lidarr **System → Status**).

On the Docker host, download and extract the release. You can also download and extract the ZIP manually, then use that folder instead of `$STAGE`.

```sh
STAGE=$(mktemp -d)
curl -fL https://github.com/SeadogsBooty/Lidarr-SoulSync-Bridge/releases/download/v1.1/Lidarr-SoulSync-Bridge-v1.1.zip -o "$STAGE/bridge.zip"
unzip "$STAGE/bridge.zip" -d "$STAGE/files"
```

Confirm `$STAGE/files/setup.py` exists. Copy the files into a new staging folder inside the container:

```sh
docker exec -u abc lidarr mkdir /config/bridge-staging
docker cp "$STAGE/files/." lidarr:/config/bridge-staging/
```

If the staging folder already exists, stop and inspect it rather than overwriting anything. Ensure the service user can read the copied files. For LinuxServer, `docker exec lidarr id abc` shows the UID and GID; for other images use the UID/GID of Lidarr's process.

## 3. Run the guided setup

From the Docker host:

```sh
docker exec -it -u abc lidarr sh
```

You are now **inside the Lidarr container**. Run:

```sh
cd /config/bridge-staging
python3 setup.py
```

Enter your own Lidarr and SoulSync URLs and API keys. Lidarr's URL can normally be `http://localhost:8686` here. SoulSync's URL must be reachable **from this container**: use its hostname on a shared Docker network or its reachable server address. Do not use `localhost` for a separate SoulSync container.

Choose your profile, sync mode and scope, then confirm saving and optional connection creation. The wizard installs into `/config/scripts/soulsync` in this example.

Still inside the container, test it:

```sh
cd /config/scripts/soulsync
python3 lidarr-to-soulsync.py --bulk --limit 5
```

This preview requires bulk or both mode. For future-only mode use the Lidarr connection's **Test** button instead. Follow [README step 3](README.md#3-use-the-bridge) to import or enable automatic sync.

## Manual setup instead

If you prefer not to use the wizard, copy the extracted files directly into the persistent AppData `scripts/soulsync` folder (inside the container or through its host-mounted config directory). Make sure they are owned by the Lidarr service user. Follow [manual installation guide](https://github.com/SeadogsBooty/Lidarr-SoulSync-Bridge/blob/main/MANUAL.md) to configure `config.env` and add the Custom Script connection. Use the **container's** absolute script path in Lidarr, not the host's mount path.

## Installing Python

If Python is missing, do not install it only in the running container: that change disappears when it is recreated. Build a derived image using your existing Lidarr image as the base. Example for a LinuxServer-style image:

```dockerfile
FROM lscr.io/linuxserver/lidarr:latest
RUN if command -v apt-get >/dev/null 2>&1; then \
      apt-get update && apt-get install -y --no-install-recommends python3 && rm -rf /var/lib/apt/lists/*; \
    elif command -v apk >/dev/null 2>&1; then \
      apk add --no-cache python3; \
    else echo "Unsupported package manager" >&2; exit 1; fi
```

Use the exact image and tag you currently run. Save the example as `Dockerfile`, then build:

```sh
docker build -t lidarr-with-python:1 .
```

Back up Lidarr's config. Change only the image in your Compose service to `lidarr-with-python:1`, keeping the existing mounts, environment and networking. Recreate that service and verify Python again. Rebuild the derived image when updating Lidarr. Other images may need a different method.

**Persistence:** The bridge files, configuration and activity history live in Lidarr's mounted AppData directory. Keep that mount when recreating the container. Do not share `config.env` or activity logs.
