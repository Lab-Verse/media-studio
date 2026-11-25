# Research, decisions and remaining setup facts

**Research date:** 20 November 2026 (Asia/Karachi).
**Status:** Planning evidence; account and Spark capability testing pending.
**Parent:** [Complete implementation plan](IMPLEMENTATION-PLAN.md).

## 1. Selected decisions

| ID | Decision | Basis |
| --- | --- | --- |
| A01 | Reuse existing paid Google Drive for intake | User selected this direction; reported allowance requires live verification |
| A02 | ZIP plus immutable ready record | Gives an explicit completed submission and byte identity |
| A03 | Outbound polling with startup reconciliation | Works with an intermittently online Spark without a webhook receiver |
| A04 | Codex CLI coordinates the existing media engine | Preserves the approved production approach and makes the PC optional |
| A05 | Small fixed API tools and filesystem receipts | Sufficient integration scope; no separate workflow platform/database needed |
| A06 | One GPU production episode at a time | Avoids shared-root/configuration and resource races in version 1 |
| A07 | Independent, hash-bound media review | Technical completion alone does not establish a correct documentary |
| A08 | Official YouTube API for routine Unlisted delivery | Removes a routine dependency on browser sessions and click automation |
| A09 | Owner alone publishes publicly | Explicit user requirement; completed deliveries are not reset later |
| A10 | Preserve supplied originals and accepted outputs | Enables corrections, recovery and traceability |
| A11 | Qualify a hybrid local-Qwen/cloud profile and complete PC copy-back | Owner clarified the existing desktop-led workflow and local 27B model; see [workflow parity](CLI-MEDIA-WORKFLOW-PARITY.md) |

These are design choices, not claims that the corresponding adapters already exist. Proposed two-minute polling, five-delivery sustained trial, admission limits and retry counts are implementation defaults to qualify, not provider guarantees.

## 2. Primary research sources

| Source | Finding used in the plan |
| --- | --- |
| [Drive file search](https://developers.google.com/workspace/drive/api/guides/search-files) | Supported listing/search operations for scoped discovery |
| [Drive downloads](https://developers.google.com/workspace/drive/api/guides/manage-downloads) | Download original binary file contents using the API |
| [Drive changes](https://developers.google.com/workspace/drive/api/guides/manage-changes) | Saved cursors support incremental reconciliation |
| [Drive OAuth scopes](https://developers.google.com/workspace/drive/api/guides/api-specific-auth) | Distinguish per-file authorization from broad account access |
| [Google upload/storage rules](https://support.google.com/drive/answer/2424368) | Shared-folder ownership does not automatically determine the uploader's storage allowance |
| [Shared drive management](https://developers.google.com/workspace/drive/api/guides/manage-shareddrives) | Workspace edition and account capabilities govern this branch |
| [Drive errors](https://developers.google.com/workspace/drive/api/guides/handle-errors) | Handle storage, access, quota and transient failures distinctly |
| [Google OAuth lifecycle](https://developers.google.com/identity/protocols/oauth2) | Refresh credentials have lifecycle limits; Testing configuration needs attention |
| [Codex noninteractive mode](https://learn.chatgpt.com/docs/non-interactive-mode) | Supported CLI automation, structured results and saved sessions |
| [Codex authentication](https://learn.chatgpt.com/docs/auth) | ChatGPT subscription sign-in and separately billed API authentication |
| [Codex skills](https://learn.chatgpt.com/docs/build-skills) | Portable skill format and local discovery requirements |
| [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) | Custom roles, delegation and model settings; real capability still requires testing |
| [Codex models](https://learn.chatgpt.com/docs/models?surface=cli) | Custom provider compatibility is not established by Chat Completions alone |
| [vLLM compatible server](https://docs.vllm.ai/en/stable/serving/online_serving/openai_compatible_server/) | Current upstream Responses support does not establish the installed Spark version |
| [systemd timers](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html) | OS activation and supervision of bounded work |
| [YouTube upload reference](https://developers.google.com/youtube/data/reference/rest/v3/videos/insert) | Explicit visibility and upload metadata configuration |
| [YouTube revision history](https://developers.google.com/youtube/data/revision_history) | Recent visibility-policy and paid-placement declaration changes |
| [YouTube resumable uploads](https://developers.google.com/youtube/data/guides/using_resumable_upload_protocol) | Recover interrupted transfers through a saved upload operation |
| [Video resource](https://developers.google.com/youtube/data/reference/rest/v3/videos) | Owned-video status and processing fields for readback |
| [Thumbnail upload](https://developers.google.com/youtube/data/reference/rest/v3/thumbnails/set) | Supported custom-cover attachment |
| [Caption upload](https://developers.google.com/youtube/data/reference/rest/v3/captions/insert) | Caption-track creation and permission requirements |
| [Content ID API access](https://developers.google.com/youtube/partner) | Restricted interface; ordinary upload success is not a complete copyright report |
| [Audiocraft licensing](https://github.com/facebookresearch/audiocraft#license) | Code and model-weight permissions differ |

Provider documents can change. Recheck the relevant endpoint, scopes, constraints and current project quota before implementation and before a material dependency upgrade. No obsolete fixed 1,600-unit upload assumption or universal private-only API restriction is built into this plan.

## 3. Current local evidence inspected

| File | What it establishes | What it does not establish |
| --- | --- | --- |
| [Preparation guide (historical evidence excluded)](../PROVENANCE.md#excluded-evidence) | Original engine intent and example format | Current dependency compatibility, historical truth or music-rights guarantees |
| [Spark episode launcher (historical evidence excluded)](../PROVENANCE.md#excluded-evidence) | Existing container, model, CPU/GPU, font and encoder configuration | New unattended CLI/Drive/YouTube capability |
| [Engine README](../../README.md) | Existing invocation and compatibility notes | Fresh live qualification of every historical statement |
| [Tenerife status (historical evidence excluded)](../PROVENANCE.md#excluded-evidence) | Recorded episode production and review history | Upload of that episode or a standing automation service |
| [Tenerife technical QA (historical evidence excluded)](../PROVENANCE.md#excluded-evidence) | Recorded technical checks and their limits | Universal tests/counts for every future episode |
| [Tenerife visual review (historical evidence excluded)](../PROVENANCE.md#excluded-evidence) | Recorded sampled scene review and accepted identity | Complete continuous playback or listening |
| [Goldsboro upload receipt (historical evidence excluded)](../PROVENANCE.md#excluded-evidence) | Recorded channel/video identity and metadata | Current OAuth validity, current visibility, or rights clearance for new work |

The working directory is not currently a Git checkout. Root `AGENTS.md`, `PROJECT.md`, `PROJECT_STATE.yaml`, `TASKS.md`, `DECISIONS.md` and `RISKS.md` were not found in this workspace scan; the user-supplied operating instructions still apply. This document package does not bootstrap a coding workflow or create replacement root governance files.

## 4. Remaining setup facts

| Fact | How to resolve during implementation |
| --- | --- |
| Actual Google subscription type and free capacity | Owner account settings and authorized storage check |
| Personal versus organization-owned input/archive files | Real developer submission and owner-copy test |
| Exact production folder IDs and ACLs | Provisioned folders plus access tests |
| Scopes that admit newly uploaded developer files | Safe listing/download test with the intended runtime identity |
| Correct channel OAuth identity and full required actions | API identity readback and scoped Unlisted pilot |
| Spark CLI/auth/media-role availability | Safe task, image/audio review and tool capability tests |
| Numerical cost and retention limits | Initial owner operating policy informed by pilot measurements |
| Source and score permissions for unattended delivery | Recorded rights evidence for the selected assets |
| Native API versus Studio readiness evidence | Pilot comparison and explicit reporting limitations |

Do not ask the owner to reconfirm Google Drive as the platform choice. Resolve account facts through authorized inspection where possible. Human interaction remains necessary for initial consent, provider-required verification and exceptional reauthorization; no secrets are requested in chat.

## 5. Deferred alternatives and limits

WhatsApp intake and its group/API eligibility are removed from version 1. Nextcloud, Twake Workplace and self-hosted email are alternatives for another requirement, not dependencies of this plan. Custom-domain email can be considered separately without changing the production contract.

This research does not promise that arbitrary package instructions are safe, historical claims can always be resolved, all generated media is licensed, or provider checks are final. It proposes automatic execution for compliant packages plus visible, resumable exception handling. External ambiguous outcomes, revoked access and complete loss of local state may still require owner action.

No installation, account connection, automated schedule, new render, upload, or production configuration change was performed as part of creating these documents.
