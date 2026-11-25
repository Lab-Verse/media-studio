# Desktop-to-Spark media workflow parity and Qwen/cloud policy

**Version:** 1.1 — 20 November 2026.
**Status:** Migration and qualification contract; no runtime package installed.
**Parent:** [Complete implementation plan](IMPLEMENTATION-PLAN.md).

## 1. Preserve the actual working pattern

The owner clarified the current flow: place and extract an approximately 20–25 MB episode package in `<local-workspace>`, ask Codex in the desktop chat to use the media workflow, run production on Spark, then return the film, thumbnail, subtitles and supporting files to the PC workspace.

The new flow changes intake and where the coordinator runs. Google Drive replaces manual package placement as the normal source; Codex CLI on Spark replaces the routine desktop-chat trigger. The existing engine and review work remain. PC delivery remains available through a separate copy-back operation, including when the PC returns online later. The input ZIP size does not bound the much larger film, generated assets or working storage.

Support the existing manually supplied package as a compatibility intake during rollout. Both intake methods produce the same normalized episode identity and use the same duplicate protection. Do not start two productions if the same episode arrives through PC and Drive.

## 2. Distinguish four independent layers

| Layer | Meaning |
| --- | --- |
| Codex client | Desktop or CLI: reads instructions, manages sessions, and exposes tools |
| Model/provider | The reasoning model answering the requests: an available hosted OpenAI model or the local Qwen endpoint |
| Roles and skills | Task instructions, resources and procedures loaded by the client |
| Execution tools | Real file, research, inspection, rendering, Drive and YouTube operations |

Installing the CLI does not turn a local Qwen model into a hosted OpenAI model. Copying skill/role files does not prove they were discovered or that their tools work. A local CLI can still use hosted reasoning while executing media tools on Spark.

Codex supports ChatGPT sign-in and API-key authentication, with different availability and billing. Qualify the owner's existing Pro-backed sign-in and selected model where supported; compare it with the API route before selecting the unattended profile. API usage is separately billed, not automatically included in Pro. The earlier API-key recommendation is an automation option, not a requirement to purchase a second plan. [Authentication documentation](https://learn.chatgpt.com/docs/auth).

Do not claim identical desktop/CLI behaviour. Comparable performance requires the chosen model/settings, loaded instructions, tools, permissions and context to be qualified together. Desktop browser/connector state and this conversation are not automatically imported.

## 3. Actual PC media-package inventory

Read-only inspection found the existing source package at:

```text
<local-workspace>
```

It contains 13 role TOML files and nine skill directories, each with a `SKILL.md`. The production workspace itself currently has no project `.codex` or `.agents` directory. This does not prove absence of global or desktop-provided instructions; it establishes that copying only the production folder would not copy this separate package.

Roles found:

```text
studio_producer              studio_creative_lead
studio_showrunner            studio_writer
studio_director              studio_cinematographer
studio_art_director          studio_spark_operator
studio_sound                 studio_editor
studio_rights_reviewer       studio_qc
studio_channel_producer
```

Skills found:

```text
studio-production            studio-creative-development
studio-screenwriting         studio-cinematography
studio-spark-render           studio-sound-and-captions
studio-post-production        studio-rights-and-release
studio-clip-production
```

These are actual local files, not a claim that all roles/skills are currently active in this chat or installed on Spark. Some were designed for dramas or clips; activate relevant documentary tasks rather than running every role for every scene. Identify additional source-research and documentary correction procedures used in prior deliveries and include them explicitly in the adapted contracts.

## 4. Required deployable package

During implementation produce a versioned, checksummed media-runtime bundle containing:

- Trusted documentary `AGENTS.md` guidance with stage ownership and explicit delegation/review requirements.
- Selected/adapted `.codex/agents/` definitions and `.agents/skills/`, including referenced resources and helper scripts.
- The generalized engine adapters and actual episode preparation/QA logic currently spread across PC helpers.
- Research/source, image inspection, audio inspection and full-decode interfaces available from Linux.
- Drive intake, fixed Unlisted upload, recovery schemas and delivery-copy contracts.
- Channel assets, supported configuration templates, dependency/model references and house-style examples.
- A bundle inventory with file hashes, source versions, required capabilities and qualification results.

The models can remain in their existing Spark library; the bundle references their verified paths and identities. Credentials are provisioned separately. Exclude secrets, personal desktop state, browser cookies, model weights and incoming package instructions from the trusted bundle.

Inspect existing role/skill instructions before adaptation. Replace routine parent-chat approvals with the owner's approved standing documentary policy where authorized; preserve material exception holds and manual public publication. Resolve Windows paths, shell differences, trust/discovery and missing tools explicitly.

Verify discovery and a real bounded delegation under the unattended profile for each required role. Count files, discovered skills, and completed role tasks separately. Official Codex documentation supports local skills and custom agents, but installation alone is not capability proof. [Skills](https://learn.chatgpt.com/docs/build-skills), [subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents).

## 5. Recommended first production profile: hybrid

The owner confirmed an already installed local Qwen 27B and wants to use it with cloud capability. Record the exact checkpoint, quantization, serving version, context limits and supported input types through a later safe live inventory. No new model installation or service change is authorized by this document.

| Task | Initial routing proposal |
| --- | --- |
| ZIP checks, IDs, hashes, timing arithmetic and state | Deterministic tools; no LLM needed |
| Asset classification, summaries, prompt drafts, metadata drafts | Local Qwen, with schemas and bounded source context |
| Routine manifest assistance | Local Qwen proposes; deterministic validation and selected-input checks enforce the contract |
| Consequential historical claims and contradiction resolution | Hosted model with real source-retrieval tools and recorded citations |
| Images, voice, ASR, motion and NVENC | Existing qualified media workers on Spark |
| Visual/audio judgement | A qualified modality-capable reviewer and actual inspection tools; never infer that a text-only endpoint saw/heard the output |
| Final editorial acceptance and unresolved findings | Independent hosted review for the first version |
| Drive/YouTube writes | Fixed validated adapters with protected credentials |

This is a design recommendation, not a measured claim that Qwen is inferior or that a fixed percentage of work will be local. Measure output quality, corrections, tool failures, context handling and total cost on representative episodes. Repeated role prompts using one checkpoint do not remove its shared blind spots.

Use Codex as the coordinator. Initially a hosted Codex session can call Qwen through a narrow structured task tool for qualified local work. That tool is a bounded model call, not a separate workflow runner. A mixed-provider native-subagent arrangement is optional and must be proven in the installed CLI; do not assume a role name or model setting automatically routes to another provider.

## 6. Direct local-Qwen Codex profile: qualification required

A local-first coordinator remains an option after compatibility and quality testing. Current Codex documentation requires a compatible Responses endpoint for custom providers; a Chat Completions-only endpoint is insufficient. Current vLLM documents Responses support, but that does not establish which version/configuration is running on this Spark. [Codex model-provider requirements](https://learn.chatgpt.com/docs/models?surface=cli), [vLLM APIs](https://docs.vllm.ai/en/stable/serving/online_serving/openai_compatible_server/).

Test actual streaming, multi-turn tool results, structured output, error recovery, context handling, saved-session continuation and required role delegation. Test research and modality capabilities separately. Plain text generation, OpenCode operation or a `/v1/models` response is not sufficient qualification.

If direct compatibility fails, keep Qwen behind the structured task tool and retain the hosted coordinator. Do not build an unqualified protocol shim or replace the existing media workflow to force local-only operation. A fallback requiring cloud must be explicit and budgeted; if unavailable, hold the required stage rather than silently accepting a weaker review.

## 7. GPU scheduling and quality comparison

Qwen serving and image/video generation can compete for the Spark's shared GPU memory and compute. Measure headroom with the real checkpoint, request concurrency and media workload. Default to serialized local model tasks and heavy media generation. Keep the selected existing model installation intact; change its running state only under an explicitly approved resource-handoff policy and verify recovery.

Compare the existing desktop-led flow with the CLI hybrid flow on the same approved source package. Freeze model/worker settings where possible, preserve scene IDs, and compare script corrections, archival choices, frames/clips, captions, sound, final card and full technical evidence. Exact generated bytes need not match. A nominally successful render or model benchmark cannot establish editorial parity.

Also test difficult cases: a wrong date, contradictory final card, misleading archival caption, missing scene, invented label and bad caption timing. Required reviewers must detect the seeded material defects. Expand local responsibilities only after task-specific acceptance; do not migrate all review roles at once.

## 8. Return the complete episode to the PC

Define a delivery manifest listing the original package, canonical manifest/corrections, selected assets and source ledger, master MP4, thumbnail, SRT/word timings, publishing metadata, QA evidence and delivery receipt. Copy only recorded deliverables, not credentials or the whole model/cache library.

Stage a one-way copy into a new versioned PC delivery directory, verify every listed size/hash, and expose a completed receipt only after the copy passes. Preserve existing PC files; do not use a deletion-based mirror or overwrite the active root manifest. An explicit compatibility mapping can retain familiar episode names and output locations.

If the PC is off, Spark completes eligible production and Unlisted cloud delivery. Mark PC copy-back pending separately, preserve the source artifacts, and deliver when the PC returns online. Do not rerender or reupload because the PC was unavailable. Google Drive can hold the selected delivery set so the PC does not need permanent inbound access.

## 9. Enablement conditions

Before claiming the same workflow is autonomous: the trusted package inventory exists, all required skills/roles load and complete safe tasks, tools cover the required modalities, the actual Qwen integration passes its tests, cloud and local authentication/budgets are selected, a representative episode passes comparison, and PC copy-back hashes match. These additions close gaps in the earlier generic migration plan; they do not certify that the migration is already complete.
