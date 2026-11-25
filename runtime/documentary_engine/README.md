# Documentary runtime source

This directory contains the existing documentary engine plus ComfyUI/Shorts adapters, with limited portability/security changes recorded in the repository provenance. Operate it with reviewed manifests on your own qualified environment. It does not install or control a Spark service and does not upload to Drive or YouTube.

## Local source and contract checks

From the repository root, Python 3.12 can run the dependency-free adapter tests listed in the root README. Additional tests require Pillow/requests (`test_reference_images.py`), NumPy/soundfile plus FFmpeg/FFprobe (`test_score_worker.py`), or qualified PyTorch/Diffusers/SafeTensors (`test_prompt_cache.py`). A missing dependency is not a passed test. Consult docs/VERIFICATION.md for the executed set.

## Fixture diagnostic

The synthetic fixture skips stock-provider/model inference and speech recognition. It still needs Python with NumPy, Pillow, requests, python-dotenv and soundfile; FFmpeg with libx264/drawtext; FFprobe; and a usable monospaced font. Use an isolated environment. Review `requirements.txt` before installing model dependencies; those source version ranges are not a portable lockfile or a newly verified installation recipe. Install the GPU build appropriate to your own host separately if using inference.

```sh
cd runtime/documentary_engine
# Set FFMPEG and FFPROBE to your installed binaries if not on PATH.
# Set DOCUMENTARY_MONO_FONT to an installed font if automatic discovery fails.
python pipeline.py --test --fixture --software
```

This uses `projects/smoke/manifest.json`, writes a clearly named `output/test_fixture_render.mp4`, metadata, thumbnail, caption sidecars and verification receipt, and generates temporary intermediates in `cache/`. It provides no evidence of real narration, generated imagery, GPU performance or creative acceptance. Inspect the receipt and full decode before interpreting the diagnostic.

`python pipeline.py --test` is a different **live inference** mode and is not a qualified quickstart for this snapshot. Its contract requires a successful stock source for the first scene and independent AI imagery for the second; provider failure must fail that check. The bundled scene directions preserve this distinction, but only their synthetic fixture mode is documented for local diagnosis. Do not run live inference unless model downloads, provider requests and compute use are authorized and qualified. Media tools can make external requests and consume GPU/disk resources. No live test is needed to browse this repository.

## Actual production

Use `python pipeline.py --manifest <reviewed-manifest.json>` only after reviewing the runtime/source contracts and target environment. Export capabilities and resolution are runner-specific. Keep ComfyUI private and provide a qualified API graph explicitly through the adapter's `--workflow` option; the supplied episode graphs are not distributed here. `tools/render_short.py` uses a separate Shorts manifest schema and must not be given the documentary chapter schema.

Copy `.env.example` to your own ignored `.env` only if needed, and fill values privately. Keep weights, caches, archival originals and soundtrack/voice references outside public Git. Source credits and model availability do not establish commercial rights.
