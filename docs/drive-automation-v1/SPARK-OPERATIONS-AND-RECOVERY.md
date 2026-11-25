# Spark installation, operation and recovery

**Version:** 1.0 — 20 November 2026.
**Status:** Proposed operations contract; no services installed.
**Parent:** [Complete implementation plan](IMPLEMENTATION-PLAN.md).

## 1. Qualify the existing environment

Inventory the actual Spark account, architecture, driver, disk, running jobs, container image, models, Python packages, media tools and network access before changing anything. The inspected repository launcher uses:

| Item | Repository configuration to preserve and revalidate |
| --- | --- |
| Engine location | `$HOME/documentary_engine` on Spark; `/workspace/documentary_engine` inside the existing container |
| Container | `nvcr.io/nvidia/pytorch:26.02-py3`; pin the tested digest during qualification |
| Decode/probe | Existing FFmpeg 9.0.1 Linux ARM64 paths |
| NVENC | Separate project FFmpeg 7.1.3 binary |
| HUD font | A pinned DejaVu Sans Mono font copy |
| Narration/captions | Existing CPU settings, including Kokoro and qualified recognizer configuration |
| Images | Existing FLUX.2 klein snapshot and memory/offload settings |
| Model storage | Existing cached weights and read-only media-library mounts |

These entries were read from [run-tenerife.sh (historical evidence excluded)](../PROVENANCE.md#excluded-evidence); they are not a new live Spark inventory. Preserve compatible dependencies rather than installing a duplicate Torch/CUDA stack. Keep unrelated ComfyUI, language-model and other production jobs under their existing ownership.

Qualify the hardware with an actual generated media sample and NVENC encode, full decode, and font/HUD sample. Encoder enumeration alone is insufficient. Record versions, digests, command configuration, elapsed time, output identity and actual results.

## 2. Codex and trusted tools

Install a pinned Linux ARM64 Codex CLI release and a protected media configuration. Provision the selected cloud authentication using protected storage and test a safe task under the unattended account. Qualify the owner's Pro-backed ChatGPT sign-in and API-key option before choosing; API authentication is an automation option with separate usage charges, not a mandatory second subscription. Follow [the local Qwen/cloud and workflow parity contract](CLI-MEDIA-WORKFLOW-PARITY.md). The CLI documentation supports structured noninteractive runs and saved-session continuation. [Codex noninteractive mode](https://learn.chatgpt.com/docs/non-interactive-mode).

Use one episode session plus distinct review sessions as needed. Save their explicit IDs. Session history supports continuity; artifact receipts establish what actually finished. Avoid ephemeral sessions for work that needs recovery.

The current local workspace is not a Git checkout. At implementation, use a trusted deployment checkout or explicitly qualify Codex's documented non-Git mode for this engine root. Do not initialize, reset or migrate the working media directory merely to satisfy a default CLI check.

Keep durable launch/QA helpers out of purgeable cache. Limit tool operations to validated paths and supported stage actions. A fixed GPU launcher must validate the episode path and image/mount configuration. Do not solve unattended operation by giving incoming packages a root shell or unrestricted Docker access. Keep credentials out of media-worker environments and agent-visible output.

## 3. Proposed local layout

Paths below are relative to the verified engine root and will be created only during implementation:

```text
automation/
  policy/                 trusted configuration and schemas; no secrets
  tools/                  fixed adapters and reusable launch/QA commands
  state/
    host.json             runtime identity and policy/tool versions
    drive-cursor.json     recorded change position
    episodes/<id>/v001/   atomic progress and operation receipts
  logs/                   sanitized event logs
  locks/                  local OS locks
incoming/<id>/v001/       quarantined ZIP and immutable originals
projects/<id>/v001/       canonical inputs and derived assets
cache/episodes/<id>/v001/ owned generated cache only
output/<id>/v001/         accepted master, cover, captions and evidence
```

The current engine may require compatibility paths. Resolve and regression-test those mappings rather than moving existing deliveries wholesale. Secrets belong in a separately protected store, not this layout or Drive reports.

## 4. Startup and work admission

A systemd unit starts the approved tool entry point after boot. A matching timer performs bounded idle checks, proposed every two minutes. On boot, scan unfinished local state and Drive submissions; a calendar timer can catch missed activations but does not replay files itself. No GUI login is required. [systemd timers](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html).

Use one designated Spark host in version 1. Acquire a host-level production lock before mutable engine configuration or GPU work, plus an upload-creation lock before starting an external video upload. A second invocation must observe the lock and exit/recheck, not spawn overlapping work. This is a local locking design, not distributed coordination.

Choose admitted episodes in a deterministic order. Before GPU admission, check available memory, disk, existing processes and expected working space. Wait when unrelated workloads occupy resources. Do not automatically kill or unload other users' jobs.

## 5. Progress records

Proposed states:

```text
DISCOVERED -> ACQUIRING -> VALIDATED -> PREPARING -> PRODUCING
 -> REVIEWING -> LOCAL_ACCEPTED -> UPLOADING -> VERIFYING
 -> DELIVERY_PENDING -> DELIVERED_UNLISTED
```

Additional states: `RETRY_WAIT`, `WAITING_RESOURCES`, `HELD`, `SUPERSEDED`, and `WITHDRAWN`. Each includes a reason and resumable next action.

Each transition records episode/version, package/canonical hashes, policy and tool versions, previous/current state, timestamps, attempt count, session ID, process identity where relevant, produced artifacts and hashes, review result, and external-operation references. Write a temporary record, flush it, atomically rename it, and flush the containing directory on the qualified filesystem. Keep a bounded transition journal and protect concurrent access with locks.

Record process boot ID and start identity as well as PID/container ID. A reused PID must not be mistaken for the old job. Time spent on source review, production, review revisions, upload and archive is measured separately.

## 6. Restart decisions

| Found after restart | Action |
| --- | --- |
| Running owned render with matching identity | Reattach monitoring; do not start a second render |
| Partial ZIP with unchanged source | Resume supported transfer; verify whole-file hash |
| Verified original ZIP | Reuse it; validate extraction and checkpoints |
| Completed scene assets with matching input/tool keys | Reuse them; rerun invalid/missing stages |
| Interrupted master encoding | Rebuild master from verified inputs if the output is incomplete |
| Accepted master and matching reviews | Continue delivery without rendering again |
| Saved YouTube session | Query/resume the same external operation |
| Known video ID, missing caption/thumbnail/report | Finish missing attachments or records against that ID |
| Ambiguous external completion | Reconcile first; hold if unresolved rather than create a duplicate |
| Already delivered video | Preserve receipt; do not reset owner-edited visibility or metadata |

No exact-once guarantee is assumed across process crashes and external services. The design uses persistent operation identity, reconciliation, and conservative holds for ambiguous writes.

## 7. Retry and resource policy

Use bounded backoff with jitter for retryable network/5xx/429 failures and honor retry guidance. A proposed limit is five transient attempts per stage invocation, then a recorded later retry. Classify quota, permission, missing-file, withdrawn-input and invalid-credential errors separately; do not repeatedly retry every 403.

Enforce local limits for episode/day model usage, revision count, provider calls and disk admission. Amounts are set before paid calls are enabled. Provider budget alerts alone are not a hard execution stop. Do not poll an LLM while idle.

If the internet fails, an already-running local render may finish while Codex/cloud-dependent stages wait. If Google authorization is revoked, retain artifacts and record a one-time action request. External OAuth applications in Testing can receive seven-day refresh tokens for these scopes, so initial setup must address the correct production/personal-use configuration and applicable verification. [Google OAuth lifecycle](https://developers.google.com/identity/protocols/oauth2).

## 8. Cache and retention

Replace global episode cleanup with a validated episode/version cache operation. Resolve the absolute target, confirm it is the recorded owned cache directory, reject symlinks/escaped paths, and check active-job locks. Preserve model weights, source ZIPs, archival originals, accepted artifacts and unrelated work. Cache keys include the relevant input/model/settings identities.

The old shared cache paths need either explicit namespacing or an ownership index plus serialization; qualify this before automation. Ordinary cleanup must not erase prompt embeddings or tools required for a resumed job.

Keep accepted inputs, masters, captions, covers and receipts until the owner adopts a retention period. A conservative pilot performs no automatic deletion of accepted deliveries or incoming submissions. Set local and Drive free-space thresholds based on measured working-set requirements. On pressure, wait/report; do not delete unrelated files to make space.

A Drive copy is useful retention but is not automatically an independent backup. Back up sanitized operational receipts separately according to the agreed recovery policy. Upload sessions and tokens require protected treatment and must not appear in shared delivery reports. A lost state disk or compromised account may require manual reconciliation; ordinary restart recovery is not a claim of complete disaster recovery.

## 9. Pause and rollback

Disable the new launcher/timer to stop admitting work, then allow or stop only the identified owned job at a safe boundary. Preserve all checkpoint files and provider IDs. Restore the pinned adapters/configuration if necessary. The pre-existing manual media invocation remains available. Rollback must not delete Drive submissions, reset the engine directory, revoke unrelated credentials, or alter delivered YouTube videos.
