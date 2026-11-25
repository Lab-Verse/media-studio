# Crew roles and skills

One Codex producer delegates short contracts during each phase. People provide creative and release decisions, on-set work, native-language listening and independent playback when a tool cannot actually inspect motion or audio.

| Role | Primary handoff | Typical pairing |
| --- | --- | --- |
| studio_producer | Brief, budget and evidence log | All modes |
| studio_creative_lead | Distinct concepts, openings, treatments and a proof of the highest-risk idea | Producer, writer and director |
| studio_showrunner | Series bible, episode cards, canon delta | Seasons and serialized dramas |
| studio_writer | Fountain script, beats and dialogue cues | Director and sound |
| studio_director | Performance and coverage plan, approved takes | Cinematographer and editor |
| studio_cinematographer | Camera, lighting, continuity and vertical coverage | Art director and Spark operator |
| studio_art_director | Reference pack, wardrobe, props and locations | Director and rights reviewer |
| studio_spark_operator | Versioned render recipes, output and receipts | Cinematographer and sound |
| studio_sound | Casting, recording, dialogue edit, captions and mix | Writer and editor |
| studio_editor | Editable timeline, cut, mix handoff and exports | Director and sound |
| studio_rights_reviewer | Rights and policy findings | Producer and channel producer |
| studio_qc | Timestamped media/technical findings | Independent of production edits |
| studio_channel_producer | Destination-specific release package and analytics brief | Rights reviewer and owner |

## Repository skills

- **studio-production** runs the phases and role handoffs.
- **studio-creative-development** develops original ideas and tests how the hook, look and sound work together.
- **studio-screenwriting** covers screenplay, short scripts, dialogue cues, audio writing and episodic canon.
- **studio-cinematography** covers direction, blocking, focal length intent, lighting, eyelines, continuity, image-to-video prompts and vertical design.
- **studio-spark-render** covers private job submission, recovery and provenance.
- **studio-sound-and-captions** covers auditions, dialogue, dubbing, ASR, Urdu RTL, cues and stems.
- **studio-post-production** covers NLE, conform, grading handoff, loudness, export and validation.
- **studio-rights-and-release** covers asset and model licensing, consent, platform disclosure and release packages.
- **studio-clip-production** covers source-grounded selection, timing, speaker framing and derivative cuts.

## Upstream extensions to evaluate

1. [Comfy's official comfy-director skill](https://github.com/Comfy-Org/comfy-cli/blob/main/comfy_cli/skills/comfy-director/SKILL.md) for multi-shot continuity and conform. Its hosted examples need inspection; adapt concepts to the permitted local adapters. [Comfy's official general skill](https://github.com/Comfy-Org/comfy-cli/blob/main/comfy_cli/skills/comfy/SKILL.md) can inform graph inspection and operation.
2. [Remotion official agent skills](https://www.remotion.dev/docs/ai/skills) for repeatable titles, lower thirds, caption animations and template renders. Check commercial terms before adopting the runtime. Use an NLE for performance-driven scene edits. [License](https://www.remotion.dev/docs/license)
3. [Film Production Skills](https://github.com/zhangzhangco/film-production-skills) and [Cinema Skills](https://github.com/Benitoow/cinema-skills) for screenplay shaping, shot lists and color scripts. Try the planning instructions on the same scene and check whether they improve continuity and editability.
4. [LTX prompting guide](https://docs.ltx.io/open-source-model/usage-guides/prompting-guide), [ASC Master Class](https://theasc.com/Master-Class/), [Fountain syntax](https://fountain.io/syntax/) and [DaVinci Resolve training](https://www.blackmagicdesign.com/products/davinciresolve/training) for craft and vendor-specific references. Train the in-house cinematography skill with accepted house examples, shot intent and failure cases.
5. [MiniMax H3 prompt-writing skill](https://github.com/MiniMax-AI/MiniMax-H3/blob/main/skills/README.md) is model-specific. Consider it only when qualifying that model and checkpoint. Keep experimental model content scoped to its evaluation.

Inspect instructions, scripts, permissions, external endpoints and license before adopting a pinned upstream revision. Record the commit and test it on a small private task. Built-in agent definitions provide roles. Skill files provide reusable technique. A render endpoint still needs proof that its actual tools work with the Spark environment.

## Delegation example

**Role** studio_cinematographer. **Objective** deliver coverage for scene S01 and flag risky talking-face shots. Exclude rendering and story rewrites. **Inputs** approved script v001, selected references and delivery canvases. **Scope** write only `productions/<slug>/shot-list.csv` and its assigned camera notes. **Deliverables** stable shot IDs, physical or generated method, framing, action, continuity and alternate vertical coverage. **Validation** compare with scene timing and verify all references, then review the animatic with the director. **Acceptance** each essential beat has an intended cut, and the hero scene is feasible within the shot budget. **Revisions** up to two. **Authorization** no external actions for planning.
