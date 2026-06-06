# Release Scope Gates

Mongoose releases are sequenced by dependency. A later capability release should
not start just because the milestone exists; it starts when the earlier runtime
surface is reliable enough to carry it.

The current release train is anchored on making the install, update, version,
release asset, and documentation loop boringly reliable before expanding into
LLM providers, UI, scheduling, persistence, or guarded autonomy.

## v0.2.0 Exit Checklist

v0.2.0 is the update lifecycle release. It is ready to ship only when all of
these are true:

- `mongoose update --self-only` can update the installed user-local
  `%LOCALAPPDATA%\Agents\bin\mongoose.exe` without depending on repo-local
  scripts.
- plain `mongoose update` reports both registry and CLI update phases clearly.
- `mongoose update --registry-only` and `mongoose update --self-only` are
  documented for automation and recovery workflows.
- installed-binary self-update behavior is covered by a Windows integration
  test with no live network dependency.
- failed executable replacement produces actionable recovery output and leaves
  an observable staged file or recovery path.
- `mongoose --version` and `mongoose state --json` report the same version and
  development/official release kind expected for the build context.
- version-tagged GitHub Actions runs fail if the release tag does not match
  `MONGOOSE_VERSION`.
- GitHub Actions builds `dist\mongoose.exe`, runs smoke tests, uploads the
  artifact, and attaches the executable to version-tagged releases.
- release notes explain the update lifecycle behavior, user-facing command
  changes, validation performed, and known recovery path.
- public docs frame Mongoose as a local-first capability runtime, with
  install/update/versioning described as lifecycle support rather than the
  whole product identity.

## Milestone Start Gates

Later milestones must satisfy these start gates before implementation moves
past v0.2.0 release work:

- v0.3.0 Capability Runtime Contract can start after v0.2.0 ships and the
  manifest/runtime contract can be changed without destabilizing install,
  update, version, or release validation.
- v0.4.0 Provider-Neutral Runtime Interfaces can start after the v0.3.0
  contract names the capability provider boundaries that LLM, memory, tools,
  storage, and API providers must implement.
- v0.5.0 Runtime Documentation and SysML Modeling can start after the runtime
  contract is stable enough that generated/modeling docs validate a real
  contract rather than speculative architecture.
- v0.6.0 Persistent Runtime and Observability can start after local state,
  logging, and job metadata have a documented contract that will not conflict
  with install/update paths.
- v0.7.0 LLM Capability Provider Runtime can start after provider-neutral LLM
  security, profile, and invocation guardrails are documented and testable.
- UI, scheduling, guarded writes, and autonomy milestones can start only after
  the runtime capability they depend on exists in a tested CLI or local service
  surface.

If a milestone wants to violate a start gate, create or update an issue that
names the dependency risk, the reason for the exception, and the rollback plan.

## Release-Prep Issue Checklist

Every release-prep issue should include this checklist:

```text
## Release scope
- [ ] Release version:
- [ ] Release theme:
- [ ] Issues included:
- [ ] Issues explicitly deferred:
- [ ] User-facing behavior changes:

## Scope gate
- [ ] Earlier milestone gates are satisfied.
- [ ] This release does not pull in later milestone work without an explicit issue.
- [ ] Known deferrals are documented in the release note.

## Validation
- [ ] Run release-version validation.
- [ ] Run install validation.
- [ ] Run Mongoose CLI validation.
- [ ] Build dist\mongoose.exe.
- [ ] Run mongoose.exe smoke validation.
- [ ] Run installed-binary self-update validation when update behavior changed.
- [ ] Confirm GitHub Actions checks are green.

## Release assets
- [ ] MONGOOSE_VERSION matches the release tag.
- [ ] CHANGELOG.md includes the release section.
- [ ] GitHub Release includes dist\mongoose.exe.
- [ ] Release asset reports official release metadata.

## Rollback and recovery
- [ ] Document how users recover if install/update fails.
- [ ] Confirm previous release asset remains available.
- [ ] Confirm update failure leaves actionable output and does not hide registry state.
- [ ] Confirm no secret values are printed in validation or release output.
```

