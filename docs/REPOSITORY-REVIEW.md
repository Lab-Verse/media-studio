# Workflow review — 25 November 2026

| Layer | Repository evidence | Status |
| --- | --- | --- |
| Crew and skills | 13 TOML role definitions, nine SKILL files and artifact handoffs | Present; file validity can be checked locally; client discovery must be proven per installation |
| Creative production | Brief through independent QC/release gates and fictional Meter Room package | Documented and locally validateable |
| Documentary engine | Python assembly modules and selected regression tests | Existing source; new Spark/environment qualification required |
| ComfyUI and Shorts | Adapter/runner source with own manifest/graph contracts | Source present; qualified graph, nodes, models and services are external prerequisites |
| Drive intake | READY, checksum, archive, ownership and duplicate contracts | Plan only |
| Unattended coordination | Role parity, startup, checkpoint and recovery contracts | Plan only |
| YouTube delivery | Resumable Unlisted transfer, attachments and receipt design | Plan only |
| Public publication | Explicit owner release decision | Never implied by a successful render |

## Findings addressed in this snapshot

1. The source runtime referenced an absent smoke manifest and environment template. This snapshot adds a synthetic two-scene manifest and blank configuration template. Fixture media does not establish speech or generation quality.
2. The historical studio smoke script imports machine-local helpers and can stop a shared model container. It is excluded; the runbook requires the existing operator and reservation procedure.
3. One transfer test imports a host-bound helper outside the engine tree. Both are excluded from the portable test set and identified in provenance.
4. The Shorts score path could escape its selected project. This snapshot adds contained-path validation and tests for traversal, absolute paths and symlink escape, without modifying the active production workspace.
5. Original production records and supplied graphs mix implementation evidence with machine/rights context. They are excluded from public publication. Do not confuse a historical successful run with current installation or unattended acceptance.

Source review was performed independently for workflow completeness and publication security. Exact executed checks and final snapshot review are recorded in [verification](VERIFICATION.md).
