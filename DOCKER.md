# Docker prerequisites

The bridge executes **inside Lidarr**, using the same UID as its service. It needs Python 3 and a writable persistent AppData directory. Check:

```sh
docker exec <lidarr-container> python3 --version
docker exec -u <lidarr-service-uid> <lidarr-container> sh -c 'id; test -w /config && echo writable'
```

If Python is missing, use a derived image instead of installing packages interactively (which disappears on recreation). Example `Dockerfile` for a LinuxServer-style root-initialized image; replace the base with the exact image/tag your deployment uses:

```dockerfile
FROM lscr.io/linuxserver/lidarr:latest
RUN if command -v apt-get >/dev/null 2>&1; then \
      apt-get update && apt-get install -y --no-install-recommends python3 && rm -rf /var/lib/apt/lists/*; \
    elif command -v apk >/dev/null 2>&1; then \
      apk add --no-cache python3; \
    else echo "Unsupported package manager" >&2; exit 1; fi
```

Build: `docker build -t lidarr-with-python:1 .` from the Dockerfile directory. Change only the image in your existing Compose service to `lidarr-with-python:1` (or use a Compose build definition), keeping volumes, environment, networking and user settings. Recreate with `docker compose up -d <lidarr-service>`. Back up your existing config first. Rebuild the derived image when updating Lidarr. This example has not been tested on every image; non-root or other base images may require a different approach. See [README](README.md) for setup and manual connection instructions.
