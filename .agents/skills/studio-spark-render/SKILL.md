---
name: studio-spark-render
description: Plan, submit or reconcile an authorized private media job using the existing DGX Spark and its ComfyUI or native film adapter.
---

- Read docs/SPARK-RUNBOOK.md. Confirm the correct remote host, approved adapter and GPU reservation. Validate a UI and API graph as different artifacts before submission.
- Assign a versioned take and capture reference hashes, graph/checkpoint versions, seed, resolution, duration/fps and job identifier. Use one heavy job at a time on this Spark.
- After disconnect, query the existing ID and inspect output evidence before retrying. Retry a classified transient failure within the production budget. Link new attempts to the original. Check queue state and prior service health before releasing the reservation.
- Record actual decode, metadata and output hash per take. Have the director watch motion and QC watch the assembled cut. A successful API request only proves its own stage.
