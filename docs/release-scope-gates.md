# Release Scope Gates

Mongoose releases are sequenced by dependency. A later capability release should
not start just because the milestone exists; it starts when the earlier runtime
surface is reliable enough to carry it.

The current release train is anchored on making the install, update, version,
release asset, and documentation loop boringly reliable before expanding into
LLM providers, UI, scheduling, persistence, or guarded autonomy.

Njord budget-maintenance work is scoped separately from unrelated platform
expansion. A release may include Mongoose runtime changes only when they are
necessary for the active Njord milestone's read, plan, approve, execute,
reconcile, or learn loop. Otherwise, platform, UI, commerce, and non-Njord agent
work should remain in their own milestones.

## Configuration Management Strategy

Each release owns a long-lived integration branch named
`release/v<major>.<minor>.<patch>`, for example `release/v0.7.0`.

Release branches are the only place where release scope is integrated before it
lands on `main`. Issue branches for that release branch from the release branch,
not from `main`, and target their pull requests back to the same release branch:

```text
main
  -> release/v0.7.0
       -> issue/126-njord-llm-runtime
       -> issue/118-response-events
```

When the release branch is ready, it is merged to `main` through a pull request.
That merge is the release boundary. GitHub Actions validates the release branch
version, creates the matching `v<version>` tag/release from the merged source,
and the existing tag build attaches the official `mongoose.exe` asset.

The release version is rolled at the start of the release branch, not at the end
of unrelated issue work. The selected version must come from SemVer impact and
roadmap intent:

- patch: corrective fixes or narrow refinements inside the current release
  promise.
- minor: additive user-facing behavior, new runtime surfaces, or the next
  roadmap capability release.
- major: incompatible command, manifest, runtime contract, storage, or
  automation behavior changes.

The release branch must keep these values aligned before it can merge:

- branch name: `release/v<version>`
- source version: `MONGOOSE_VERSION`
- changelog section: `## v<version>`
- GitHub milestone/release-prep issue scope

After a release branch merges, `main` should represent the latest official
release source. New work starts by creating the next release branch from `main`.
Emergency fixes may use a patch release branch from `main` or from the affected
release tag, but they still merge through `main` and publish through the same
Actions path.

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
- v1.2.0 Njord Guarded Write Planning can start only after read-only Njord
  analysis can produce stable evidence for recommendations. It may create
  budget-maintenance plans for moving money or allocating new money, but it
  must not call YNAB write endpoints.
- v1.4.0 Njord Guarded Write Execution can start only after write plans,
  approvals, expiration, and stale-state checks are represented as durable
  records. It must execute only approved plans and emit audit records from the
  first write operation.
- v2.1.0 Decision Learning and Guarded Autonomy can start only after proposal
  outcomes and write reconciliation exist. Preference learning may influence
  ranking and rationale before auto-approval is enabled, but auto-approval must
  remain policy-gated and limited to low-risk, reversible operations.

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

## Configuration management
- [ ] Release branch is named `release/v<version>`.
- [ ] Issue branches for this release branch from `release/v<version>`.
- [ ] Issue pull requests target `release/v<version>`, not `main`.
- [ ] The release branch version matches `MONGOOSE_VERSION`.
- [ ] The release branch version matches the changelog section.
- [ ] The version bump matches SemVer impact and roadmap intent.

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
- [ ] Release branch PR merge to `main` created the matching GitHub Release.
- [ ] GitHub Release includes dist\mongoose.exe.
- [ ] Release asset reports official release metadata.

## Rollback and recovery
- [ ] Document how users recover if install/update fails.
- [ ] Confirm previous release asset remains available.
- [ ] Confirm update failure leaves actionable output and does not hide registry state.
- [ ] Confirm no secret values are printed in validation or release output.
```

