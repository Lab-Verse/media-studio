# Validation, staged rollout and acceptance

**Version:** 1.0 — 20 November 2026.
**Status:** Future runtime qualification plan; no runtime tests executed for this documentation task.
**Parent:** [Complete implementation plan](IMPLEMENTATION-PLAN.md).

## 1. Evidence rules

Record the tool/policy version, selected input, exact command or API operation, timestamps, exit/result, output identity and reviewer verdict. Protect credentials and upload-session references. Separate source research, local artifacts, actual Spark runtime, provider state and owner publication.

Use deterministic fixtures for adapter/control tests and real providers for media and account qualification. A fixture pass must never be reported as a real model, GPU, NVENC or YouTube success. Previous episode passes are references, not evidence that the new automation is installed.

The current pipeline defines `--test` as live-provider verification and `--fixture` as an explicit inference-skipping diagnostic. Planned commands below run only inside the qualified Spark environment, not automatically during documentation delivery:

```bash
python pipeline.py --test --fixture
python pipeline.py --test
```

Record their actual distinct outputs. An unsupported live provider or model-license issue is resolved through approved configuration; it is not silently converted into a fixture success. Full episode acceptance still requires the media gates.

## 2. Rollout phases

| Phase | Work | Exit evidence |
| --- | --- | --- |
| 0. Inventory and policy | Confirm subscription, ownership, available space, folder ACLs, channel, runtime, auth method, limits and retention | Nonsecret configuration, initial grants, approved operating policy and recorded unresolved facts |
| 1. Read-only intake | Discover test packages; validate and download them without rendering or uploading | Completeness, scope, pagination, ownership, checksum and duplicate tests pass |
| 2. Local production | Run a representative complete episode with generalized trusted tools | Same required scene contracts and accepted editorial, visual, audio and technical results |
| 3. Unlisted live pilot | Upload the accepted pilot using the official API and finish attachments/reports | Correct channel and Unlisted delivery verified, with one initial Studio/playback comparison |
| 4. Recovery qualification | Inject interruptions, changed packages, authorization errors and repeated events | Reconciliation, artifact reuse, no duplicate video, and actionable holds demonstrated |
| 5. Sustained trial | Proposed five consecutive representative deliveries plus unattended reboot/idle periods | No routine prompts, no missing scenes, no duplicates, no public publication, and measured cost/turnaround |
| 6. Enable standing operation | Accept the pilot evidence and configured operating policy | Startup/timer enabled, rollback demonstrated, owner publication boundary intact |

Initial account consent and rollout acceptance are setup activities. Compliant episodes after enablement do not request routine human approval. Exceptional factual, rights, credential or ambiguous-write failures retain an explicit hold path.

## 3. Intake test matrix

| ID | Scenario | Expected behaviour |
| --- | --- | --- |
| D01 | ZIP still uploading; no ready record | No admission |
| D02 | Ready record references missing/truncated ZIP | Wait or hold; no extraction/production |
| D03 | Valid submission while Spark is off | Discovered and processed after boot |
| D04 | Listing requires multiple pages | Every eligible submission found once |
| D05 | Repeat event, renamed ZIP, archive copy | One delivery key; no repeated work |
| D06 | Same episode/version, different digest | Conflict hold |
| D07 | Source changes during download | Reject stale acquisition; require immutable version |
| D08 | ZIP traversal, symlink or expansion limit | Reject before production writes |
| D09 | Duplicate filenames or out-of-area shortcut/file ID | Reject ambiguity or scope escape |
| D10 | New developer file under selected auth scopes | List and download succeed without per-episode consent |
| D11 | Personal folder upload and owner archive copy | Actual storage owner verified; copies do not create new jobs |
| D12 | Withdrawn package or newer version | Honour safe-boundary/version rules; preserve evidence |

## 4. Runtime and production test matrix

| ID | Scenario | Expected behaviour |
| --- | --- | --- |
| S01 | Safe Codex task under unattended identity | Real tool/structured-output operation passes |
| S02 | Live local model and NVENC sample | Actual generation and encode/decode evidence, not encoder listing |
| S03 | Complete representative episode | All selected IDs/order, silence, overlays, captions and branding retained |
| S04 | Incorrect title/final card or false archival credit | Independent review catches and resolves or holds finding |
| S05 | Audio ducking/crossfade/clipping fault | Signal and required listening checks reject it |
| S06 | Reboot with render running/completed | Reconcile process identity and resume the appropriate stage |
| S07 | Two scheduler invocations | Locks prevent overlapping mutable/GPU production |
| S08 | Unrelated GPU job active | Wait; preserve that job |
| S09 | Episode cache cleanup | Only owned inactive generated cache removed; shared models and other episodes intact |
| S10 | Agent/network failure or revision limit | Bounded retries or hold; no unlimited spending loop |
| S11 | Local or Drive storage pressure | Admission waits/reports; no unrelated deletion |
| S12 | Changed master at same path | Hash mismatch invalidates acceptance and upload admission |
| S13 | No approved score/source rights | Internal draft may be retained; automatic delivery remains held |
| S14 | Long idle interval | Cheap checks only; no repeated empty LLM sessions |
| S15 | Media runtime migration | Required roles and skills actually discovered and complete bounded tasks under the unattended profile |
| S16 | Qwen/cloud qualification | Real endpoint, streaming/tool continuation, structured output and assigned review capability tested; no assumed provider interchangeability |
| S17 | Desktop-led versus CLI hybrid comparison | Same source package preserves scene contracts and passes independent editorial, visual, sound and technical acceptance |
| S18 | PC off during production | Cloud delivery completes; copy-back remains separately pending and finishes with matching hashes when the PC returns |

## 5. Delivery test matrix

| ID | Scenario | Expected behaviour |
| --- | --- | --- |
| Y01 | Wrong channel identity | Reject before upload |
| Y02 | Package requests Public or scheduled publication | Guard rejects it; no live public test is performed |
| Y03 | Normal upload | Unlisted and all mandatory declarations explicitly set |
| Y04 | Network failure during transfer | Resume/reconcile saved operation; no new video |
| Y05 | Lost final response or expired session | Reconcile; unresolved outcome held rather than duplicated |
| Y06 | Caption/thumbnail failure after video exists | Retry attachment against saved video ID |
| Y07 | Drive report/archive write fails | Delivery-pending retry; no new YouTube upload |
| Y08 | Processing/rejection/quota error | Classify correctly and retain resumable next action |
| Y09 | Revoked OAuth grant | Preserve artifacts and request account reauthorization once |
| Y10 | Owner publishes delivered video manually | Automation does not revert visibility or overwrite metadata |
| Y11 | Episode resubmitted after delivery | Saved receipt reused; replacement policy governs revisions |
| Y12 | Copyright status not exposed | Report it as unverified; do not claim Studio checks passed |

Mock invalid-public requests, ambiguous failures and permission errors where possible. Real external writes during qualification remain within the owner's approved Unlisted pilot scope. Use actual provider operations only where necessary to prove the capability.

## 6. Quality and cost acceptance

Use [MEDIA-QUALITY-GATES.md](MEDIA-QUALITY-GATES.md) as the required acceptance contract. Give independent review the actual final identities and evidence, not just the producer's assertion.

Measure total wall time from package admission to verified delivery, broken down into download, preparation/research, media generation, render/encode, reviews/revisions, upload/processing and archive/report. Measure NVENC fps and elapsed encode time separately. Keep model/API usage and actual costs distinct from GPU encode performance.

Adopt numerical cost and resource limits from the measured pilot and owner's initial budget. No fixed turnaround or zero-failure percentage is claimed from a single smoke test.

## 7. Enablement checklist

- Account/storage ownership and runtime capability checks passed.
- Initial OAuth and any applicable verification completed; refresh tested.
- Trusted media tools are durable, versioned and available on Spark.
- All required test categories have evidence and no unresolved delivery blocker.
- Unlisted safeguards and owner-publication protection passed.
- Producer/reviewer capabilities cover actual required visual and audio inspection.
- Budgets, revision limits, storage thresholds and retention are recorded.
- Exception reporting and disable/resume procedure demonstrated.
- Existing manual engine invocation and unrelated workloads preserved.

## 8. Rollback

Disable new work admission and timer activation. Stop only identified owned work where necessary. Preserve originals, checkpoints, credentials under their existing protection, and external IDs. Restore the previous qualified tool/configuration version and continue manually if needed. Do not delete, replace, publish, or change visibility on delivered videos as rollback.

## 9. Documentation validation for this delivery

Documentation checks executed on 20 November 2026:

| Check | Observed result |
| --- | --- |
| Expected document set | All nine Markdown files present after the version-1.1 parity addition |
| Encoding and final newlines | All files readable as UTF-8 with final newlines |
| Local Markdown links | All local file targets resolve; rechecked after the parity addition |
| Fenced examples | Balanced in all nine documents |
| JSON example | Parsed successfully; schema version, readiness, digest shape, positive version and size checked |
| Citation formatting | No internal web-tool citation markers found |
| Semantic inspection | Drive selection, storage-ownership branches, unchanged media format, episode-scoped cleanup, recovery, Unlisted delivery and owner publication boundary reconciled |

These checks validate this documentation delivery only. No Spark runtime, Drive account, OAuth grant, systemd service, media render or YouTube upload was tested or changed during this task.
