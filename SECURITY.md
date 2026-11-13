# Security

## Reporting a vulnerability

Use [private vulnerability reporting](https://github.com/SeadogsBooty/Lidarr-SoulSync-Bridge/security/advisories/new) if enabled for this repository. Otherwise request a private reporting channel without posting sensitive details.

Do not include API keys, private `config.env`, activity logs, internal URLs, hostnames, or library data in public issues or pull requests. Rotate any exposed keys immediately.

## Safe installation

- Run the bridge as the Lidarr service user; restrict the installation directory to mode 700 and private configuration/history/lock files to 600.
- Use regular, service-user-owned files, not symbolic links or hardlinks. Review parent directory permissions and filesystem ACLs.
- Use the final Lidarr and SoulSync API URLs, preferably HTTPS on untrusted networks. Authenticated HTTP redirects are refused, including same-origin redirects, to prevent credentials reaching another destination or POST requests being rewritten.
- The bridge only adds artists to the selected SoulSync Watchlist. It never starts scans or downloads or changes automation settings.

The current maintenance release receives fixes. Older releases may lack security hardening; upgrade using [MANUAL.md](MANUAL.md#upgrade-disable-or-uninstall).
