# Changelog

## v0.3.0 - Capability Runtime Contract

Planned release type: minor.

This release introduces Mongoose Runtime Contract v1: a portable execution
context that lets agents discover host state, selected capability metadata,
configuration status, provider availability, and structured diagnostics without
knowing the local environment layout.

### Added

- Add `MONGOOSE_RUNTIME_CONTEXT` and `MONGOOSE_RUNTIME_CONTRACT_VERSION` for
  `mongoose run` and non-dry-run `mongoose route` executions.
- Add Runtime Contract v1 context files under user-local Mongoose runtime state.
- Add provider descriptors for configuration, logs, state, local storage,
  memory, tools, API profiles, and LLM.
- Add agent/capability-scoped local storage provider paths.
- Add structured runtime error codes for missing agents, missing entrypoints,
  missing required configuration, unavailable providers, and incompatible
  runtime contracts.
- Add runtime contract and provider-interface documentation.

### Changed

- Preserve existing agent subprocess argument shapes while adding runtime
  context through environment variables.
- Extend validation fixtures to prove agents receive runtime context and can
  discover providers without importing Mongoose internals.

## v0.2.0 - Update Lifecycle Release

Planned release type: minor.

This release makes the install/update/release loop reliable enough for the
next capability-runtime milestones. Mongoose remains local-first and
capability-runtime-first: install, update, versioning, and release artifacts
are lifecycle support for portable agents, not the whole product identity.

### Added

- Add installed-binary self-update validation for `%LOCALAPPDATA%\Agents\bin\mongoose.exe`.
- Add release scope gates and a release-prep checklist for milestone discipline.
- Add validation that guards against repository-name drift, default registry URL
  drift, and release workflow ordering problems.

### Changed

- Make `mongoose update` run both registry refresh and Mongoose CLI update
  phases with explicit output and a phase summary.
- Add `mongoose update --registry-only` and `mongoose update --self-only` for
  automation and recovery workflows while keeping `mongoose update --self` as
  an alias.
- Reposition docs around Mongoose as a local-first capability runtime.

### Recovery Notes

- If self-update cannot replace the running executable immediately, Mongoose
  schedules replacement after the command exits and tells the user to confirm
  with `mongoose --version` in a new terminal.
- If replacement fails, Mongoose reports the staged download path and manual
  recovery guidance.
- The previous release asset remains available from the GitHub Releases page.

## v0.1.2 - CLI Version Hotfix

Planned release type: hotfix.

### Fixed

- Update the Mongoose CLI version reported by `mongoose --version` and
  `mongoose state` to `0.1.2`.
- Correct the release-version drift where the `v0.1.1` release asset still
  reported `mongoose 0.1.0`.
- Report whether a build is a development build or an official release build.
- Add CI validation so version-tagged release builds fail when the tag does not
  match the Mongoose CLI version.

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
