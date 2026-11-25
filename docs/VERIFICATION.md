# Snapshot verification

Executed locally on 25 November 2026 with Python 3.12.10:

| Check | Result |
| --- | --- |
| `python scripts/validate_studio.py` | 13 role definitions, nine skills; four shots, six assets and two dialogue cues, 24 planned seconds |
| `python scripts/validate_repository.py` | Python syntax, JSON/TOML, local Markdown links, published-source hashes and high-confidence disclosure scan passed |
| ComfyUI adapter tests | 10 passed |
| Shorts production-contract tests | 15 passed |
| Shorts score containment tests | 3 passed, including symlink escape |
| Pinned reference-image tests | 5 passed |
| Supplied-score tests | 5 passed; one FFmpeg-dependent test skipped because FFmpeg/FFprobe were not on this host's PATH |
| Smoke manifest | Accepted by the real `pipeline.validated` function; two scenes |

Total: **38 selected tests passed, one skipped**. The PyTorch/Diffusers/SafeTensors prompt-cache test file was not run because those dependencies are absent. No model dependencies were installed, no model weights downloaded and no GPU inference performed. The synthetic fixture was structurally validated but no diagnostic video was rendered here.

Independent source audits reviewed workflow completeness and publication security. They identified the missing fixture/environment template, machine-specific operator, external transfer-test dependency and Shorts supplied-score path escape. The final workflow review also caught a mismatch between static smoke scenes and the renderer's motion-evidence requirement; the fixture now uses supported nonzero motions and preserves stock-first / independent-AI live directions. The offline validator enforces those fixture contracts. This snapshot resolves or explicitly excludes these items, as recorded in [the review](REPOSITORY-REVIEW.md). Final staged-snapshot security review approved public publication; corrected fixture directions remain structurally reviewed, not rendered here.

The public CI workflow runs source checks plus the dependency-free ComfyUI, Shorts and score-containment tests on Python 3.12. CI results must be read from GitHub after the push; local results alone do not prove remote CI execution.

Both independent reviewers approved initial public source publication after the fixture correction. The workflow reviewer independently reran the two source validators and 28 dependency-free tests before that correction, then verified the corrected fixture directions and source checks. The security reviewer inspected the exact staged file inventory and selected staged blobs, including the score boundary fix.

GPU rendering, provider/model setup, native-language listening, live account integration and unattended operation require separate qualification. No active production job or service is changed by this repository publication.
