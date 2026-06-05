# Changelog

## v0.1.2 - CLI Version Hotfix

Planned release type: hotfix.

### Fixed

- Update the Mongoose CLI version reported by `mongoose --version` and
  `mongoose state` to `0.1.2`.
- Correct the release-version drift where the `v0.1.1` release asset still
  reported `mongoose 0.1.0`.

### Changed

- Includes the colored terminal output work merged after `v0.1.1`.

## v0.1.1 - Maintenance Release

Planned release type: maintenance.

This release aligns the public release artifacts with the current Mongoose
project identity and licensing posture.

### Changed

- Rename the public repository identity from Agents to Mongoose.
- Add the Mongoose source-available commercial-permission license to the
  release source snapshot.
- Add README license guidance for non-commercial use and commercial permission.

### Notes

- No functional CLI changes are planned from v0.1.0.
- The release should include a fresh `mongoose.exe` asset built by GitHub
  Actions from the tagged source.
- The release should not be marked as a prerelease.
