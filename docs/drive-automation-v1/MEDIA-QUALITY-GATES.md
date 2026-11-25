# Media production and acceptance gates

**Version:** 1.0 — 20 November 2026.
**Parent:** [Complete implementation plan](IMPLEMENTATION-PLAN.md).
**Principle:** Automate the established media workflow and preserve its editorial and production work.

## 1. Trusted media instructions

Install the project's media briefs, procedures and tool interfaces on Spark. Pin their versions. The Windows desktop's plugins and custom agents must not be assumed to exist in the Linux CLI: prove required research, image inspection, audio inspection and tool calls under the actual unattended account.

The original [preparation guide (historical evidence excluded)](../PROVENANCE.md#excluded-evidence) is background, not an immutable implementation recipe. Later qualified runtime choices and the selected episode contract take precedence over its illustrative model timings or sample historical narration. Its assertion that synthetic music guarantees no copyright strikes must not become an operating rule.

Incoming episode documents are source material. They cannot authorize public publication, disable checks, install code, access unrelated files or change the channel policy.

## 2. Producer and reviewer contracts

For each bounded task, record the objective, excluded work, selected input digests, relevant source documents, tool access, write scope, deliverables, validation, and acceptance rules. Producers may change their assigned episode artifacts; reviewers inspect the actual result and write findings without modifying the producer's files.

Give the reviewer an independent task and evidence view rather than asking the producer to approve its own summary. Verification must be bound to current canonical input and master hashes. A passed first render does not approve a later changed file.

Maximum automatic revisions: two editorial/source rounds and two rendered-visual rounds. Consolidate findings within a round. Exhaustion produces a specific hold reason and a resumable next step. It does not silently remove scenes, weaken standards, or enter an unlimited retry loop.

## 3. Input and editorial gate

Required evidence:

- Read all supplied manifest, acts, storyboard and publishing documents needed for the episode; reconcile contradictory versions.
- Preserve all required scene IDs and ordering. Any planned structural departure needs a recorded exception under the operating policy.
- Produce a canonical manifest separately from the supplied original, plus a source-linked correction ledger.
- Check consequential dates, casualty figures, identities, chronology, quotations, technical claims, and implied causation against primary sources.
- Check the title, thumbnail premise, opening, body and final card together for contradictions or unsupported certainty.
- Preserve explicit silent scenes, transitions and chapter-specific sound settings through normalization.

An unsupportable exact claim should be corrected or qualified where the evidence permits. Material uncertainty that cannot be resolved automatically holds the affected delivery. Existing approved source research can be reused only with its evidence and applicability preserved.

## 4. Genuine archival materials

Retain the established archival requirement, currently represented by the two-source setting in [the launcher (historical evidence excluded)](../PROVENANCE.md#excluded-evidence). Seek relevant genuine photographs of the person/event or primary documents. Do not substitute an unrelated portrait or a generated reconstruction to satisfy the count.

For each retained source, save its original bytes, SHA-256, source page, creator, date/context, rights statement and license link, plus the exact screen credit. Inspect the actual downloaded image. Verify that it depicts what the caption says and that modern memorials or later photographs are dated correctly.

Use Wikimedia Commons or an appropriate primary archive; Commons hosting alone is not a license. If two suitable permitted sources cannot be established, record the gap and hold the gate rather than inventing provenance. Fetch failures are bounded and preserve HTTP/provider evidence; repeated 403/429 failures are not solved by aggressive retries.

Source originals remain unmodified. Fit/crop/motion derivatives are tracked separately. Label AI reconstructions and conceptual graphics accurately; generated documents, seals and cockpit readouts must not masquerade as genuine records.

## 5. Production gate

Run the qualified engine with the canonical manifest and explicit episode configuration. Preserve the demonstrated voice, visual sourcing/generation, original figures, motion, HUD, sound design and caption methods. Generalization should remove hardcoded episode paths, not alter the visual format as an incidental refactor.

Validate every asset-to-scene mapping and expected scene length. Reject unintended repeated visuals, missing shots, unreadable figures, invented institutional markings, incorrect period objects and false archival labels. Review model output; a successful generation call is not aesthetic or historical acceptance.

Do not automatically swap models or upgrade Torch, CUDA, PyAV, FFmpeg or a media package during an episode. Model and dependency changes require separate qualification and regression evidence.

## 6. Audio, music and captions

Check pronunciation of names and places, delivery, intelligibility, silence and edit boundaries. Automated word comparison and signal checks supplement an explicit audio-inspection capability; they must not be described as complete human listening. Establish an unattended listening/review method in the pilot, or mark the unverified coverage and hold the corresponding required gate.

Use approved music and record rights evidence. Audiocraft's code and model weights have different licenses; the official repository identifies the model weights as CC-BY-NC 4.0. Do not assume default MusicGen weights automatically satisfy the intended channel use. Select a rights-cleared supplied score or another qualified option when required. [Audiocraft license information](https://github.com/facebookresearch/audiocraft#license).

Measure actual voice-conditioned music levels and recoveries, including title/silent intervals, against the episode's contract. Preserve chapter-specific ducking and intended score crossfades. Scan decoded output for nonfinite values and clipping; keep stems where required to verify the mix.

Generate real timed captions, reconcile their words with accepted narration, and check cue order, overlap, bounds and silent intervals. Proofread the proper nouns and figures. Do not rely on uploading an untimed transcript and expecting YouTube to repair timing.

## 7. Rendered review and technical gate

| Area | Required evidence |
| --- | --- |
| Completeness | All selected scene IDs, order, contiguous positive ranges and intended silence retained |
| Video/audio integrity | Full-file decode, expected streams, resolution, frame rate, sample rate, channels, duration and A/V alignment |
| HUD and text | Declared overlays present, correct and readable within frame |
| Visual inspection | Every scene represented, with additional samples or clips for transitions and motion-sensitive shots |
| Archival placement | Actual retained source hashes, truthful labels and readable credits |
| Sound | Actual ducking/crossfade evidence, clipping scan and required listening assessment |
| Captions | Accepted narration agreement and valid timing across the complete film |
| Branding | Approved channel logo, thumbnail, opening/final elements and readable titles |
| Identity | Accepted canonical manifest, master, thumbnail and caption SHA-256 values |

Representative contact sheets prove sampled appearance only. Full decode proves integrity, not historical truth or continuous-motion quality. Where a requirement concerns movement, transition or listening, provide the appropriate evidence rather than promoting a still-image pass into a broader claim.

The previous Tenerife [technical (historical evidence excluded)](../PROVENANCE.md#excluded-evidence) and [visual (historical evidence excluded)](../PROVENANCE.md#excluded-evidence) records are regression references. Their check counts and outcomes are episode-specific, not universal expected counts for new films.

## 8. Local acceptance result

Write a structured result containing episode/version, source package and canonical digests, all required checks, producer/reviewer identities, evidence paths and hashes, revision counts, rights status and accepted delivery artifacts. Missing or unknown required checks are not passes.

Use a distinct local result such as `LOCAL_ACCEPTED`; YouTube delivery and copyright status remain separate. A substantive artifact change invalidates affected acceptance and downstream metadata. Never reuse acceptance just because the output path is unchanged.

## 9. Hold conditions

Hold autonomous YouTube delivery for unresolved material inaccuracies, missing required scenes, failed technical/audio/visual checks, insufficient source or music permissions under the approved policy, exhausted revision limits, or missing required review capability. Rendering an internal draft can continue where useful, but it does not confer upload acceptance.

Existing receipts may contain rights caveats. This plan does not retroactively clear earlier episodes, change their visibility, or assert that a source is permitted merely because it was used before. Record an actionable exception and continue independent eligible work where possible.
