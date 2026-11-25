# Production artifact contracts

Use stable production, scene, shot, dialogue, asset and take IDs. Example `meter-room`, `S01`, `S01-010`, `D001`, `AS001`, `S01-010-v001`. Retain decisions by version.

| Artifact | Minimum records |
| --- | --- |
| Brief | Production ID, mode, owner, audience, language, platforms, narrative promise, runtime, target gate, budgets, allowed sources |
| Creative treatment | Distinct concepts, openings, intended effect, visual and sound motifs, recurring series device if relevant, proof plan and chosen direction |
| Series bible | World, premise, season arc, character relationships, locked continuity, episode cards, timeline, open threads and canon deltas |
| Script and dialogue cues | Fountain or timed script, stable scene references, language, spelling/pronunciation, cue ID, speaker, performance and timing |
| Lookbook | Cast and approved references by asset ID, expressions/angles, wardrobes, props, markers, geography, palette and motivated lighting |
| Shot list | The example schema uses `shot_id,scene_id,seconds,method,description,camera,asset_ids,dialogue_ids,vertical_note`. Separate multiple IDs with semicolons inside the field. Split details into linked per-shot notes when useful. |
| Asset ledger | Example fields `asset_id,kind,source,rights_status,evidence`. Track exact revision, actual rights and authorized uses/platforms, territory, term, approval and private rights pointer in working records. Use planned for missing future materials. |
| Dialogue paths | Example `dialogue.csv` contains `dialogue_id,scene_id,speaker,language,line,performance_note`. Keep dry takes and selection notes outside Git. |
| Take and render receipts | Production and take ID, parent attempt if any, selected source and hash, recipe and hash, model versions, environment/parameters, job ID, timing and retries, output paths and hashes, technical and creative status |
| Edit and caption deliverables | Original NLE project or supported edit interchange, timebase, original shot/timecode, audio stems, captions, color/export settings, aspect-specific change notes and rubric |
| Review and release | File version and hash, device and reviewer, timestamps/defects, language/rights checks, destination, title/thumbnail brief, disclosure, visibility and owner authorization |

Suggested folder layout for a production:

```text
productions/<slug>/
  BRIEF.md
  TREATMENT.md
  script.fountain
  dialogue.csv
  shot-list.csv
  assets.csv
  LOOKBOOK.md
  SERIES-BIBLE.md        optional for serialized work
  takes/                text receipts
  edit/                 edit metadata and interchange if shareable
  review/               decision, QC and release records
```

The [worked example](../examples/meter-room/BRIEF.md) gives the three CSV templates and a Fountain scene. Copy its shape, replace sample content and use the [gate record template](../templates/GATE-RECORD.md). For shot-based productions, validate the CSV files with `python scripts/validate_studio.py --package productions/<slug>`. For an audio-only package, use timed cue and stem sheets in place of the shot list and check them against the edited audio.

Keep media and backups in the designated storage for the production. Access-controlled records such as releases, voice reference files and source camera footage stay there. Capture restoration evidence before depending on archives for future episodes.
