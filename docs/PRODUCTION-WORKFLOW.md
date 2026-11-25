# Media Studio production workflow

Media Studio describes the creative crew and handoffs. The documentary engine supplies rendering functions. The Drive automation plan describes a future intake and delivery route. Codex coordinates them; no separate dashboard, queue service or orchestration platform is introduced.

## Production gates

| Gate | Work and owner | Acceptance evidence |
| --- | --- | --- |
| G0 Brief and concept | Producer and creative lead define audience, language, format, sources, rights, budget and strongest opening. | Selected treatment, explicit constraints and a small proof of the riskiest idea |
| G1 Script | Writer and director develop the chosen story; showrunner maintains episode canon when relevant. | Timed script, stable scene IDs, factual corrections/source ledger and pronunciation notes |
| G2 Production design | Director, cinematographer, art director, sound and editor plan coverage, lighting, references and dialogue. | Versioned shot/asset/cue lists, animatic, continuity notes and separate vertical composition |
| G3 Takes | Spark operator or camera crew creates owned, versioned takes using the qualified adapter. | Frozen graph/model identities, job IDs, hashes, playback and technical checks; resource recovery evidence |
| G4 Private master | Editor and sound assemble the film; independent QC and rights reviewers inspect it. | Editable timeline or recipe, audio stems, captions, full decode, timestamped review, accepted master hash |
| G5 Release | Channel producer prepares title, thumbnail, description, chapters, credits and disclosure. Owner controls delivery. | Explicit named destination/version/visibility authorization and provider receipt |

Default to two targeted revision rounds per disputed artifact unless the production brief defines another budget. Preserve previous takes. Hold unresolved material defects and return the specific decision to the owner.

## Runtime paths

- `runtime/documentary_engine/pipeline.py` assembles chapter/scene manifests with narration, stock or generated imagery, optional pinned archival/illustration sources, score/mixing, motion, HUD, captions, thumbnails, metadata and final encoding.
- `runtime/documentary_engine/tools/comfy_pipeline.py` adapts a reviewed API-format ComfyUI graph to the documentary assembly path. Graph ownership, model/node installation and exact graph mapping require qualification.
- `runtime/documentary_engine/tools/render_short.py` handles a separate Shorts manifest and graph contract, scene caching, narration, captions, video preparation and master assembly. A partial visual proof does not count as a delivered master.
- Render code, creative quality, platform upload and public publication are separate states. The included runtime does not implement the proposed Drive or YouTube connectors.

The runtime uses external FFmpeg/FFprobe and optional speech/image/music packages. It does not include weights, source footage, voices, soundtracks, model licenses or access grants. Do not infer format, model or hardware support beyond the selected runner and verified environment.

## Future Drive-to-Unlisted route

1. Developer submits the immutable episode ZIP and READY completion record.
2. Discover and download only eligible files from the configured Drive area.
3. Verify size/checksum/identity, reject unsafe archives and validate required input contracts.
4. Preserve originals; prepare the canonical story and production task contracts.
5. Run the established media workflow and independent acceptance gates.
6. Upload accepted artifacts with explicit Unlisted visibility, attach captions/thumbnail, reconcile external operations and save the video ID/receipt.
7. Return the report and eligible PC delivery files. The owner reviews and chooses public release.

These steps are **planned**. See the complete [nine-document plan](drive-automation-v1/README.md), especially [intake](drive-automation-v1/DRIVE-INTAKE-CONTRACT.md), [quality](drive-automation-v1/MEDIA-QUALITY-GATES.md), [recovery](drive-automation-v1/SPARK-OPERATIONS-AND-RECOVERY.md) and [rollout](drive-automation-v1/VALIDATION-AND-ROLLOUT.md).

## Modes

The crew contracts cover originals, documentary films, social cuts, authorized clips, podcasts, dubbing, drama and seasons. These are planning modes, not a claim that every combination has a qualified renderer. Record the chosen mode, target language, canvas, source permissions and review method in each brief. Urdu dialogue needs actual native-language listening and caption playback checks. Model names and dated research are historical selections until requalified.
