# Codex and DGX Spark media production plan

Research checked 16 November 2026. The initial deliverable is the local repository and production design. The pilot, service integration and new model qualification are subsequent implementation phases.

## Production architecture

```text
Owner: brief, creative decisions and release authorization
  |
Codex project: producer coordinates named agents and records versioned decisions
  |
Brief -> creative treatment -> series bible / script -> coverage, references, dialogue -> animatic
  |
  +-> DGX Spark: private ComfyUI / existing film adapter, ASR, media processing
  +-> Camera / voice crew: filmed material, performances and room tone
  |
Edit and mix -> independent review -> private masters -> channel package
```

The repository carries the production plan, role instructions, templates, recipes and versioned references. Media lives in a designated workspace with backups. Use private SSH or NVIDIA Sync to work on the existing Spark. A Codex remote project is an option if that application surface is available and the Spark repo is intentionally selected. Keep a single writable production checkout for planning. For the first pilot, the Windows Codex checkout owns Git and Spark receives a frozen, versioned input package. Use the existing ComfyUI queue, film adapter and Spark-side media reservation. The operator records job IDs and results in the production folder. [Codex remote connections](https://learn.chatgpt.com/docs/remote-connections#connect-to-an-ssh-host) · [ComfyUI server routes](https://docs.comfy.org/development/comfyui-server/comms_routes)

## Production modes

| Mode | Source and editorial workflow | First output |
| --- | --- | --- |
| Original Short/Reel | Hook → beat change → payoff. Compose vertical shots, use a read-aloud script, and check first audio/caption on a phone. | 20–60 second 9:16 cut and caption sidecar |
| Licensed clips / podcast reels | Ingest authorized media, transcribe, select timecodes, watch context and speakers, reframe and verify source-to-export traceability. | Private review cut and timestamp map |
| Audio / podcast / audio drama | Outline or cue sheet, record and edit speech, mix dialogue/ambience/music, listen through, preserve transcript and stems. | WAV master, distribution encode if requested, transcript |
| YouTube original | Audience promise, source ledger when factual, script, coverage, B-roll or inserts, editable timeline, thumbnail and metadata. | 16:9 master plus optional distinct promo |
| Drama episode | Canon, scene breakdown, performance, matched eyelines and wardrobe, audio-first animatic, shot-level renders and human edit. | Start with 60–90 second proof, then 3–5 minute pilot after qualification |
| Season | Series bible, arc and episode cards, casting/reference continuity, recurring looks and music, schedule with capacity data. | Three outlined episodes, then one commissioned episode at a time until throughput is known |

## Gates and handoffs

| Gate | Lead and reviewers | Required evidence |
| --- | --- | --- |
| G0 Brief and concept | Producer, creative lead, showrunner, rights reviewer | Audience, primary language, channel, rights and budget. Choose a treatment with a specific hook, look, sonic motif and cheap proof. |
| G1 Script | Writer, director, showrunner, native reader when relevant | Timed table read, approved script revision, pronunciation sheet, factual source links where needed, continuity deltas |
| G2 Production design | Director, cinematographer, art director, editor, sound | Shot list and IDs, character and environment references, dialogue takes or approved scratch track, versioned animatic, minimum viable coverage, alternate vertical composition |
| G3 Takes | Spark operator or camera crew, director | Job or camera receipts, fault/recovery evidence, approved takes checked at playback speed, continuity and decode evidence |
| G4 Private master | Editor, sound, independent QC and rights | Editable timeline, stems, subtitle sidecars, technical results, human language pass, exported versions and hashes, timestamped reviewer notes |
| G5 Release | Channel producer, rights reviewer and owner | Version hash and destination, channel-specific copy, disclosure, rights per asset, explicit approval for the named upload and visibility |

The Creative Lead owns concept development and cross-format ideas. The writer turns the chosen treatment into scenes, the director steers how performers and camera realize them, and the showrunner maintains the season arc and canon. The Creative Lead can review the rough cut and suggest a stronger beat or opening before picture lock.

A rejection records the issue, owner, affected file revisions and resolution. Revise changed work and re-run its dependent checks. Keep earlier takes recoverable. Resolve creative tradeoffs with the owner after two targeted revision passes unless the brief gives another budget. The pilot can stop at G4 with local review outputs.

## Implementation sequence

| Phase | Tasks | Exit evidence |
| --- | --- | --- |
| 0. Local setup | Open repo in Codex. Validate role and skill definitions and run the sample planning prompt. Choose a production slug and authorized media storage. | Crew discovery and a bounded planning handoff visible in the session |
| 1. Spark connection | Identify current host, active adapter, approved service owner, real ARM64/CUDA/Torch versions and shared-memory headroom. Check active job/reservation and backup. Smoke-test the known graph with the runbook. | Preflight record, job ID, short playable take, full decode, checksum, and recovery of any paused service |
| 2. Original pilot | Two fictional characters, one location, 60–90 seconds in Urdu, roughly 8–14 edited shots using generated, filmed or authorized material. Commission three priority shots first. Cut a 20–35 second vertical promo and test an audio-only mix. | G1–G4 evidence; native listeners, phone playback, editorial and QC signoff, logged time per accepted second |
| 3. Candidate qualification | Compare Wan A14B with isolated LTX-2.5 on the same reference set. Compare an eligible Urdu speech model to cast recordings. Add integration only when it removes an observed bottleneck. | Test matrix, representative clips, failure/recovery logs, license disposition and approved shot/audio uses |
| 4. Repeatability | Complete a second private production using the same contracts. Run disconnect/resume and targeted cancel/recovery on owned work. Verify editable timeline + project archive restore. | Two complete private deliveries and successful recovery, including a known baseline render after recovery |
| 5. Channel and season | Select channel concept and publishing cadence. Draft a three-episode arc, commission one 3–5 minute episode, then assess capacity and authorized channel results. | Approved release version, rolling throughput log and season budget based on actual results |

Start with English or Urdu as selected per brief. Urdu-first pilot is proposed based on the existing production work. Use cast dialogue as the reference, with an approved synthetic voice only after documented comparison and rights review. Check pronunciation, phrasing, breath, emotional delivery and accuracy before lip-sync. Use reactions, backs, inserts and off-screen dialogue as coverage when a close-up fails. When matched talking-face performance remains essential, audition audio-driven generation or filmed coverage at the animatic stage.

## Working targets for the pilot

- Begin with a 5-second technical smoke render, then three story shots, then the complete edit. Start at 480p or 720p where appropriate and scale only selected work. Plan real generated time around measured accepted seconds. One previously recorded 5-second A14B run took about 19.5 minutes at eight steps and 16 fps. Twelve runs at that same setting would occupy about 3.9 Spark hours before retries, longer or higher-quality settings, audio or edit time. This arithmetic is a scheduling example, not a forecast.
- Use 1080p delivery presets for review where they fit the material, with 1920×1080 and 1080×1920 as initial canvases. Choose one editorial frame rate per delivery, document the conform from source and inspect motion; upscaling source to the master canvas does not add native detail. Start with H.264/AAC stereo review copies, sidecar SRT or VTT, and 48 kHz WAV stems. Keep an edit master suited to the NLE and delivery requirements.
- Set an internal stereo review target around −16 LUFS integrated and ≤−1 dBTP when appropriate for a short online mix, measure the actual export and listen at comparable levels. Define separate targets if a broadcaster or distributor requires them. These are pilot mix targets.
- Two independent people for final editorial/QC if available, plus at least one native Urdu listener for an Urdu release. Require correct spoken meaning and names, no visible clip-breaking continuity defects, no broken captions or first-word truncation, no decode errors, and all rights reviewed before release.
- Record elapsed render time, peak shared-memory pressure, accepted takes per attempt, minutes per approved generated second, minutes per finished minute including edit, revision count and failure/recovery incidents. After authorized release, track Shorts engaged views and retention, long-form CTR and retention, and returning viewers by series where available. Set channel cadence after the second private delivery measures capacity. [YouTube analytics definitions](https://support.google.com/youtube/answer/12220281)

## Reusable outputs

Use [Artifact contracts](ARTIFACTS.md) for consistent IDs, fit-for-purpose evidence and release records. Use [Spark runbook](SPARK-RUNBOOK.md) for the on-device implementation and [Crew and skills](CREW-AND-SKILLS.md) for role selection. The [research report](research/MARKET_RESEARCH.md) records source-backed alternatives and their limits.
