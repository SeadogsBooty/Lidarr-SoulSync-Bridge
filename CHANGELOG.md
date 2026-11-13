# Changelog

## 1.1.1 — Guided setup completes the selected workflow

- Options 1 and 3 start the existing-library import preview immediately after configuration; choose all or individual artists and explicitly confirm before writing.
- Options 2 and 3 offer automatic Lidarr Artist Add connection setup; no extra command is required after setup.
- Clarified numbered choices, manual installation, Docker instructions, and incomplete-import reporting. Preserves provider matching and duplicate safeguards.
- Added regression tests for setup modes, profile isolation, confirmed all-selection, cancellation and unresolved-review reporting.
- Added isolated integration coverage through the real wizard, installer, matching and connection logic with mocked API transport. The complete suite has 117 tests; no production services are used.
- README lists every wizard prompt and keeps later-import/recovery commands in MANUAL.md. Updated the public version and release download links to v1.1.1.

## 1.1 — Initial public release

- Guided and manual installation; optional automatic Lidarr Artist Add connection.
- Bulk preview, selective import, single-artist retries and activity history.
- Provider-aware identity matching, aliases, direct lookups for supported catalogs, duplicate protection and metadata retry handling.
- 94 automated regression tests; native Linux, Docker and Deezer live validation. Non-Deezer writes remain awaiting live validation.
- Release audit fix: reject control characters and Unicode line separators before saving configuration, including remotely supplied profile IDs; matching behavior is unchanged.
- Four configuration-safety regression tests bring the release suite to 98 tests. Added direct ZIP download, explicit manual copy/permission commands, broader private-file exclusions and LF line endings.
- CI validates Python 3.8, 3.11, 3.13 and 3.14; the minimum-version job uses Ubuntu 22.04 for interpreter availability.

Version cadence: 1.1.1 for fixes, 1.2 for the next feature release.
