# Complete implementation plan: Drive → Spark → YouTube Unlisted

**Version:** 1.1, 20 November 2026 (Asia/Karachi).
**Status:** Planning complete; installation, integration, and qualification not performed.
**Approved platform decision:** Reuse the owner's existing paid Google Drive storage.

## 1. Outcome and scope

Build a dependable unattended path from a developer's completed episode package to an accepted, Unlisted YouTube video. The DGX Spark performs the production work whenever powered on. Google Drive holds submissions while it is offline. The Windows PC and a logged-in browser must not be dependencies of routine production.

Preserve the owner's complete PC delivery as well: originals, selected production documents/assets, master, thumbnail, subtitles and evidence return through a checksummed copy when the PC is available. PC availability must not block eligible Spark/YouTube work. The new [workflow parity contract](CLI-MEDIA-WORKFLOW-PARITY.md) defines the role/skill migration, deployable media-runtime package, hybrid local-Qwen/cloud policy and copy-back acceptance.

Preserve the existing documentary media workflow: manifest preparation, historical corrections, genuine archival sources, narration, explanatory graphics, AI reconstructions, music, forensic HUD, scene timing, captions, thumbnail, independent review, and technical evidence. Parameterize episode-specific operations and make their checkpoints reusable; do not redesign the film format.

The owner retains public publication. Unlisted videos remain Unlisted indefinitely until the owner changes them. There is no automatic one- or two-hour publication timer.

This plan adds narrow integration tools and OS startup configuration around Codex and the existing engine. It does not introduce a separate workflow platform, dashboard, database, message broker, or orchestration stack. The current media container remains available. WhatsApp, a self-hosted office suite, custom-domain email, and Ansible are not prerequisites.

## 2. Architecture

| Component | Responsibility |
| --- | --- |
| Private Drive production area | Store completed inputs and sanitized delivery records |
| Small deterministic Drive adapter | List allowed folders, validate ready records, download selected bytes, and publish receipts |
| Codex CLI on Spark | Coordinate bounded episode stages, research, inspection, and corrections using trusted media instructions |
| Existing documentary engine | Run qualified local media models, composition, captions, and NVENC encoding |
| Independent media reviewer sessions | Judge actual selected inputs and rendered evidence against the episode contract |
| Fixed YouTube adapter | Upload approved artifacts, enforce Unlisted, and verify provider results |
| systemd and filesystem locks | Start work after boot, reactivate idle checks, and prevent overlapping jobs |
| Per-episode files | Record input identity, progress, output hashes, reviews, and external operation receipts |

All service traffic originates from Spark. Version 1 uses periodic Drive polling, so no public inbound endpoint or webhook relay is needed. A cheap adapter check runs while idle; an LLM session is started only for actual work or recovery requiring it. A proposed two-minute interval is adjustable during qualification.

Files in Drive are persistent intake, not the live render filesystem. Work is copied to local Spark storage. The adapter never mirrors the entire subscription. Selected originals and masters can be archived to Drive after identity checks.

Google provides file download and change-tracking APIs suitable for these connectors. Their use here is a proposed design, not an existing connected integration. [Drive downloads](https://developers.google.com/workspace/drive/api/guides/manage-downloads), [change tracking](https://developers.google.com/workspace/drive/api/guides/manage-changes).

## 3. Google subscription and storage

The configured storage allowance is a user-provided allowance, not a verified free-space measurement. Phase 0 establishes subscription type, available capacity, account permissions, and organization restrictions.

| Account situation | Setup branch |
| --- | --- |
| Workspace edition supporting Shared drives | Prefer an organization-owned production Shared drive; confirm membership and external contributor policy |
| Google One or personal My Drive | Use a dedicated production folder, with explicit file ownership and archive-copy handling |

For personal My Drive, another user's uploads to a shared folder can consume that uploader's allowance. The proposed default is developer-owned temporary submissions plus an owner-authorized, verified archive copy, using the owner's storage for retention. This requires temporary uploader capacity and may temporarily store two copies. Do not delete either copy automatically. If that does not suit the actual accounts, settle the upload ownership arrangement before enabling production; do not silently add a paid Workspace subscription. [Google upload ownership/storage rules](https://support.google.com/drive/answer/2424368).

Shared drive availability depends on the actual Workspace edition. A personal shared folder is not a Workspace Shared drive. [Shared drive management](https://developers.google.com/workspace/drive/api/guides/manage-shareddrives).

## 4. Submission and discovery

The developer submits one immutable ZIP per episode version, followed by a small `READY.json` uploaded last. An approved packaging helper should validate local contents, upload the ZIP, obtain its Drive file ID, and write the ready record. The developer's ordinary action is submitting a finished package, not operating the production system.

The full contract is in [DRIVE-INTAKE-CONTRACT.md](DRIVE-INTAKE-CONTRACT.md). It includes manifest location, publishing package, acts, storyboard, assets, source/rights records, package size, SHA-256, version, and ready status.

The adapter uses configured folder IDs rather than matching arbitrary folder names. It performs a startup scan, processes every listing page, and filters to the approved area. A change cursor can make later checks efficient, but a periodic full production-area reconciliation remains the recovery fallback. Repeated events and files are deduplicated locally.

No package executes until bytes, declared entry points, and archive safety pass validation. Incoming text and documents inform the brief; they cannot redefine trusted machine instructions or publishing permissions.

## 5. Episode lifecycle

| Stage | Work and required checkpoint |
| --- | --- |
| Discover | Save episode/version, source folder and file IDs, ready-record hash, ZIP size and hash |
| Acquire | Resume/retry download, verify complete bytes, preserve originals, and validate safe extraction |
| Prepare | Reconcile supplied manifest/acts/storyboard; create a canonical manifest and correction ledger |
| Source review | Verify consequential historical claims and genuine images/documents; record provenance and permissions |
| Produce | Generate approved narration, media, graphics and captions; assemble all scenes with the existing engine |
| Review | Inspect actual inputs and current rendered evidence; allow bounded corrections |
| Accept locally | Full decode and media checks pass; selected master, thumbnail and caption hashes are accepted |
| Upload | Start or resume the recorded YouTube operation for these exact artifacts |
| Verify | Read back settings, processing, caption status and thumbnail evidence; persist the video ID |
| Deliver | Save a sanitized receipt and link locally and in Drive; preserve the master and inspect next work |

The automation must distinguish a pipeline exit code, artifact acceptance, API upload response, provider processing, and owner publication. None substitutes for another.

Input hashes and policy/tool versions accompany each checkpoint. An accepted scene or film that changes must pass its affected checks again. A newly written filename is not proof that the correct artifact was reviewed.

## 6. Preserve and formalize the media workflow

Existing repository evidence includes [the Spark launcher (historical evidence excluded)](../PROVENANCE.md#excluded-evidence), [Tenerife production records (historical evidence excluded)](../PROVENANCE.md#excluded-evidence), [technical QA (historical evidence excluded)](../PROVENANCE.md#excluded-evidence), and [visual review (historical evidence excluded)](../PROVENANCE.md#excluded-evidence). These show the intended production and review pattern; they do not qualify new autonomous services.

The launcher is currently episode-specific and invokes a helper from cache. Implementation must move reusable trusted preparation/launch logic into durable project tools, parameterize the episode, and retain the demonstrated environment. Production code must not depend on a helper that normal cache cleanup can erase.

Use the selected episode's manifest directly. If legacy code requires a root-manifest mirror, update it atomically under the single-production lock, record its hash, and prevent another episode from changing it during a run. A golden-episode regression must demonstrate equivalent scene contracts and quality; generated bytes need not be identical when models are nondeterministic.

[MEDIA-QUALITY-GATES.md](MEDIA-QUALITY-GATES.md) defines the reviews, including all-scene coverage, title/final-card consistency, actual voice-conditioned ducking, and source verification. Give producers and reviewers separate bounded sessions. Each contract names its inputs, outputs, allowed edits, checks, two-round maximum, and conditions for holding the episode.

## 7. Spark startup and recovery

Install a pinned, qualified Linux ARM64 Codex CLI and the trusted media instructions/tools. Use bounded `codex exec` tasks with structured output and persistent session IDs. Resume the saved episode session, not a global most-recent session. Authentication and local permissions are provisioned once and tested under the actual unattended account. [Official Codex automation documentation](https://learn.chatgpt.com/docs/non-interactive-mode).

The first recommended profile uses local Qwen 27B for qualified bounded drafting tasks and hosted reasoning/review for consequential claims and final acceptance, with the existing media workers unchanged. Qualify Pro-backed ChatGPT sign-in and the API option before choosing cloud authentication; API charges are separate. Direct local-Qwen Codex operation, including tools and subagents, requires endpoint and quality tests before adoption. Copying role/skill files is not sufficient proof of parity.

systemd starts the existing tools after boot; no desktop session is required. Filesystem locks serialize production and external upload creation. On recovery, inspect both recorded process identity and artifacts before restarting a stage. A still-running render must not be launched again.

An interrupted encoding process may need to restart; verified finished inputs and scene assets should be reused. An interrupted YouTube upload follows its saved session. Uncertain completion is reconciled or held, never blindly retried as a new video.

Use a dedicated runtime account, validated fixed tool operations, protected credentials, and limited filesystem/network access. Incoming assets do not receive arbitrary shell, Docker, root, or credential access. [SPARK-OPERATIONS-AND-RECOVERY.md](SPARK-OPERATIONS-AND-RECOVERY.md) defines the detailed rules.

## 8. Upload policy

The target channel is seeded from existing repository receipts as `<configured-channel-id>`; verify it live through the authorized identity before enabling writes. This is a known identifier, not evidence of current API authorization.

The trusted uploader enforces Unlisted, no publication schedule, AI disclosure Yes, truthful paid-promotion declarations, reviewed metadata, approved branding, timed captions, and verified prior-video URLs. It accepts only artifact identities accepted by the quality gate. The package cannot supply an arbitrary visibility operation.

The owner publishes manually in Studio. Once a delivery is complete, routine reconciliation must not change that video's visibility or overwrite the owner's later edits. An already-public completed video is not automatically reverted to Unlisted.

The supported API path and its limits are specified in [YOUTUBE-UNLISTED-DELIVERY.md](YOUTUBE-UNLISTED-DELIVERY.md). Copyright-check status must remain distinct from processing success. No claim-free or monetization guarantee is made.

## 9. Operating controls and proposed defaults

| Control | Proposed version-1 policy |
| --- | --- |
| Concurrency | One production episode using the GPU; intake checks can continue cheaply |
| Cache | Episode/version namespace; preserve model weights, originals and deliveries |
| Corrections | Maximum two editorial and two rendered-visual revision rounds |
| Transient API failure | Bounded exponential backoff with jitter and provider retry guidance |
| Failed episode | Hold with a specific reason; allow independent eligible work to continue |
| Publication | Always Unlisted at automated delivery; no automatic public transition |
| Notifications | Delivery, terminal failure, or required action; no routine polling spam |
| Spending | Locally enforced per-episode/day limits agreed before paid calls are enabled |
| Retention | Keep originals, accepted masters and receipts; cleanup requires a recorded policy |

Measure complete turnaround, rendering, NVENC throughput, source/review effort, upload time, revision count, disk use, and model/API spending during the pilot. Previous encode performance is not an end-to-end production SLA.

## 10. Implementation work packages

1. **Inventory and accounts:** establish Drive type/ownership, folder IDs, target channel, trusted runtime paths, Codex authentication, budgets and operating policy. Output: a nonsecret configuration record and qualification results.
2. **Intake adapter and developer packager:** implement the submission contract, pagination, selective downloads, completeness checks, safe extraction, immutable snapshots, and deduplication. Output: validated local package plus source receipt.
3. **Reusable media entry points:** parameterize the episode-specific preparation, model/FFmpeg settings, source and prompt handling, renderer invocation and QA helpers. Output: existing film behaviour preserved on the selected regression package.
4. **Quality and progress contracts:** implement hash-bound receipts, state transitions, producer/reviewer session contracts, retry limits and invalidation after edits. Output: a machine-checkable local acceptance result.
5. **Unlisted delivery:** implement OAuth, resumable upload, visibility guards, caption/thumbnail attachment, readback, video-ID persistence and Drive report/archive operations. Output: a fully verified Unlisted pilot.
6. **Startup and qualification:** configure OS startup and locks; run reboot, network, duplicate, authorization and failure tests. Output: rollout evidence and a reversible enable/disable procedure.

These are future bounded implementation scopes, not assignments to running agents or authorization to deploy during documentation work. Any implementation team must preserve unrelated files and jobs.

## 11. Acceptance and rollout

Follow [VALIDATION-AND-ROLLOUT.md](VALIDATION-AND-ROLLOUT.md). Required proof includes offline submission and catch-up, no partially uploaded package processing, duplicate prevention, all-scene production, independent media acceptance, saved upload recovery, exact channel/visibility/disclosures, continued operation after reboot, and owner publication remaining untouched.

Start with read-only discovery, then local-only production, then a clearly identified live Unlisted pilot, then a proposed five consecutive representative deliveries and injected failure cases. Enable the standing loop only after the operating policy and evidence are accepted. Tests cannot establish zero future failures; they establish demonstrated behaviour and a recovery path.

## 12. Current limits and decisions still needed at setup

The Drive platform choice is settled. Actual plan type, storage availability, folder ACLs, authentication, budgets, retention periods, source/music rights and runtime installation remain to be qualified. Initial account consent and platform-required verification cannot be automated away. Revoked access or unresolved material source/rights findings can stop an affected stage without discarding its work.

No earlier browser upload or successful render proves that the proposed API connectors, CLI media roles, startup service, or crash recovery are already operational. [RESEARCH-AND-DECISIONS.md](RESEARCH-AND-DECISIONS.md) separates provider facts, local evidence, and proposed design choices.
