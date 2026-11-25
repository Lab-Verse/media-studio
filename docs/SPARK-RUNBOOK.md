# DGX Spark implementation runbook

## 1. Identify the current baseline

Use the existing NVIDIA Sync connection or approved SSH alias. Establish the actual host, active project root, ComfyUI binding, dependency versions, model files and current reservation procedure with the operator. Read the existing DGX project instructions and latest run records before touching the running media services. Use the operator-approved local records; workstation-specific paths are excluded from this public snapshot. The historical film path uses the native Wan 2.2 A14B experts and retains a legacy node identifier for graph compatibility. Confirm the current editable and API graph rather than guessing from the node label or using an old 5B export.

Run the following read-only inventory on the Spark. Replace port 8188 if the installed service uses another port.

```bash
hostname
uname -m
free -h
df -h
nvidia-smi
ffmpeg -version | head -n 1
curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8188/system_stats
curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8188/queue
```

Check the actual ComfyUI Python environment for torch/CUDA, active device, model/graph revisions, custom nodes, free disk for temporary and final artifacts, applicable license records, and current runtime owners. Record current health for any service involved in the documented memory procedure. Treat model installation, API health, render, decode and editorial quality as distinct evidence.

If the workstation needs browser or direct HTTP access, use your existing private forward, or a local loopback tunnel using the established SSH alias. An optional example on the workstation is below.

```text
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:18188:127.0.0.1:8188 <existing-spark-ssh-alias>
```

The workstation would call `http://127.0.0.1:18188`. Confirm actual access and binding policy before use. Keep ComfyUI and control endpoints private. [NVIDIA ComfyUI playbook](https://github.com/NVIDIA/dgx-spark-playbooks/blob/main/nvidia/playbook-comfyui/README.md) ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· [ComfyUI routes](https://docs.comfy.org/development/comfyui-server/comms_routes)

## 2. Establish a production folder

Under the approved media root create a versioned, isolated folder per production. Keep the input package with approved brief, references and start hashes. Put outputs, logs and source media in child directories. Copy only the selected inputs through the existing private transfer method. Store model files once in the current library. Record larger assets by private locator and hash, backups by destination and restore date. Save both the editable graph and exact API recipe used in receipts.

Begin with the existing native film operator for graphs that require ownership checks and service coordination. Confirm actual command discovery with the existing operator docs. If a standard graph can run directly, preflight its pinned nodes with `/object_info`, allow only the agreed fields for shot overrides, and use `POST /prompt` with API-format JSON wrapped in the documented `prompt` payload. Put a unique production/shot/attempt token in the output node's filename prefix or the adapter's verified server-visible correlation field. Record it with the frozen inputs before submitting. Verify the pinned service exposes that value in its queue/history data or operator logs. Retrieve status and output with `/history/{prompt_id}` and `/view` or the approved transfer path. Retain the server-issued ID as soon as submission returns.

## 3. Prove one run and its recovery

1. Ensure the production owns the existing media reservation before submitting a heavy run. Run one heavy job at a time. If capacity conditions require it, apply the established controlled Qwen pause/restore procedure with the operator's authorization. Record before/after health. Keep controller and cache configuration.
2. Use a trusted source and one owned take, about five seconds at the recorded 720p smoke profile if applicable. Record job ID, graph and checkpoint versions, source and recipe hashes, seed, steps, resolution, coded fps, memory pressure and elapsed time.
3. Allow the owned run to finish across a deliberate client observation disconnect during qualification. On reconnect reconcile ID, queue position and history. If the response was lost, search for the exact take token across the queue, history and operator logs. If there is no reliable match or several possible jobs, stop and reconcile with the operator. Submit a fresh attempt only when the operator establishes the original was never accepted or an owned attempt has reached a terminal state. Retrieve and validate the final output. Reuse an identical complete, verified result when restarting assembly.
4. In a separate test, cancel only the owned queued or running job after confirming the adapter's cancellation scope. Avoid global interrupt or queue clearing against a shared instance. A cancellation or failed run still needs verified release and service restoration. Retry transient failures at most twice for the pilot and save distinct attempt records. Escalate repeated resource, dependency or ownership failures.
5. Save streams, full decode, hash, and human playback findings. Close the media reservation only after the owned workload is idle and the previously active services are checked. When the host crashes, reconcile job/lease/service state before scheduling the next job.

Example on the Spark for a local approved output. Run a separate audio probe or presence check against the delivery spec when an audio track is required.

```bash
ffprobe -v error -show_format -show_streams -of json "take.mp4" > "take.probe.json" &&
ffmpeg -v error -xerror -i "take.mp4" -map 0:v:0 -map '0:a?' -f null - &&
sha256sum "take.mp4"
```

## 4. Qualify candidates in isolation

Use an isolated ComfyUI environment when a model needs a newer runtime. Confirm Linux aarch64, CUDA, PyTorch and kernels before downloading the full model set. Check disk and system memory, pin revisions and hashes and test each new node/package in isolation. Use official LTX-2.5 local workflows and weights, with exact Community License review and owner acceptance for gated weights where required. Start with one known I2V reference and 4ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ5 seconds. Treat NVFP4 as a specific runtime combination to validate on this GB10. Check offloading behavior, storage and output quality. Never infer multiclip reliability from one success.

Benchmark a close-up with a restrained action, two-character continuity/reverse coverage, and a vertical moving or blocking shot. Use the same references, requested duration, aspect, output comparison scale and acceptance rubric. Record each model's supported schedule, native cadence, quantization, actual dimensions and prompt differences. Run two or three seeds per shot, including cold/warm timings. Judge matched results blind when possible. Measure identity, wardrobe, camera obedience, motion defects, continuity at cuts, crop safety, lip-sync, speech accuracy, reroll rate and accepted seconds per GPU-hour. Screen recordings and listening evidence accompany scores.

Use human-recorded dialogue and existing Faster-Whisper for the first caption trial. Optional speech evaluation uses the same 12ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ20 Urdu lines across speakers or intentions, including names, colloquial phrasing and code-switching. Have native listeners score intelligibility, pronunciation, naturalness and emotional fit, with zero meaning-changing spoken errors as the short pilot release standard. Timing, caption layout and lip sync require actual playback review.

## 5. Optional Codex tools

Begin with the approved private SSH or existing film command and ComfyUI API. Comfy's official MCP offers local stdio use and can route submission/jobs/uploads via `COMFYUI_URL`; its environment/lifecycle tools may refer to the host running the MCP process. Use the Spark HTTP route or Spark-side SSH for remote inventory. A pilot MCP configuration would use a pinned revision, no hosted partner credentials and a scoped tool policy. Verify read-only inventory, owned submission, scoped status/history, output retrieval and fault recovery before relying on it. [Comfy MCP docs](https://docs.comfy.org/agent-tools/mcp) ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· [Comfy MCP source](https://github.com/Comfy-Org/comfy-mcp)

## Rollback and handoff

End only owned test jobs, restore the services previously running through the existing operator, confirm queue and model health, and rerun the known small baseline if the candidate affected runtime state. Retain failed receipts with error classification and next steps. Remove only reviewed disposable pilot artifacts when authorized. Give the parent Codex session the approved takes, hashes, QC evidence, retry history and service verification.
