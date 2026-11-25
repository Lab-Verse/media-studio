"""Generate local image assets with Diffusers FLUX.1-schnell or SDXL."""

import os
import hashlib
from functools import lru_cache
from pathlib import Path
from tempfile import NamedTemporaryFile

DEFAULT_MODELS = {
    "flux": "black-forest-labs/FLUX.1-schnell",
    "flux2_klein": "black-forest-labs/FLUX.2-klein-4B",
    "sdxl": "stabilityai/stable-diffusion-xl-base-1.0",
}


def prompt_cache_key(prompt: str, backend: str, model_id: str, max_length: int) -> str:
    """Bind safe tensor embeddings to their exact model and prompt contract."""
    import json
    return hashlib.sha256(json.dumps([backend, model_id, max_length, prompt],
                                    ensure_ascii=False).encode('utf-8')).hexdigest()


def cached_prompt(prompt: str, backend: str, model_id: str, max_length: int):
    """Read a finite CPU tensor without deserializing executable pickle data."""
    import torch
    from safetensors import safe_open
    directory = Path(os.environ['IMAGE_PROMPT_CACHE']).resolve()
    name = prompt_cache_key(prompt, backend, model_id, max_length)
    path = directory / (name + '.safetensors')
    if path.is_symlink() or path.resolve().parent != directory:
        raise ValueError('Unsafe prompt cache path')
    with safe_open(path, framework='pt', device='cpu') as file:
        if (file.metadata() or {}).get('cache_key') != name or set(file.keys()) != {'prompt_embeds'}:
            raise ValueError('Prompt cache metadata does not match the selected prompt')
        tensor = file.get_tensor('prompt_embeds')
    if (tensor.ndim != 3 or tensor.shape[0] != 1 or not 0 < tensor.shape[1] <= max_length
            or tensor.shape[2] < 1 or not tensor.is_floating_point() or not torch.isfinite(tensor).all()):
        raise ValueError('Invalid prompt embedding tensor')
    return tensor


def model_name() -> str:
    """Return the configured checkpoint for asset provenance."""
    backend = os.getenv("IMAGE_BACKEND", "flux")
    if backend not in DEFAULT_MODELS:
        raise ValueError("IMAGE_BACKEND must be flux, flux2_klein, or sdxl")
    return os.getenv("IMAGE_MODEL", DEFAULT_MODELS[backend])


@lru_cache(maxsize=1)
def _load(backend: str, model_id: str, device: str, offload: bool, variant: str | None):
    import torch
    from diffusers import Flux2KleinPipeline, FluxPipeline, StableDiffusionXLPipeline

    if device.startswith("cuda") and os.getenv("IMAGE_TEXT_DEVICE") == "cpu" and backend != "flux2_klein":
        raise ValueError("CPU prompt encoding with GPU image generation requires FLUX.2 Klein")
    pipeline_class = {"flux": FluxPipeline, "flux2_klein": Flux2KleinPipeline,
                      "sdxl": StableDiffusionXLPipeline}[backend]
    if device.startswith("cuda"):
        dtype = torch.bfloat16 if backend.startswith("flux") else torch.float16
    else:
        dtype = torch.bfloat16 if os.getenv("IMAGE_CPU_BF16") == "1" else torch.float32
    variant_option = {"variant": variant} if variant else {}
    cached = bool(os.getenv('IMAGE_PROMPT_CACHE'))
    offload_mode = os.getenv('IMAGE_OFFLOAD_MODE', 'model')
    if offload_mode not in {'model', 'sequential'} or (offload_mode == 'sequential' and not cached):
        raise ValueError('Sequential image offload requires a preencoded prompt cache')
    if cached and backend != 'flux2_klein':
        raise ValueError('Preencoded prompt cache requires FLUX.2 Klein')
    component_options = {'text_encoder': None} if cached else {}
    pipeline = pipeline_class.from_pretrained(
        model_id, torch_dtype=dtype, use_safetensors=True, low_cpu_mem_usage=True, **variant_option,
        **component_options,
    )
    if os.getenv("IMAGE_STORAGE_FP8") == "1":
        if not backend.startswith("flux") or not device.startswith("cuda"):
            raise ValueError("IMAGE_STORAGE_FP8 requires a CUDA Flux model")
        pipeline.transformer.enable_layerwise_casting(
            storage_dtype=torch.float8_e4m3fn, compute_dtype=torch.bfloat16)
    if offload:
        if not device.startswith("cuda"):
            raise ValueError("IMAGE_CPU_OFFLOAD requires a CUDA image device")
        if cached or os.getenv("IMAGE_TEXT_DEVICE") != "cpu":
            if offload_mode == 'sequential':
                pipeline.enable_sequential_cpu_offload(device=device)
            else:
                pipeline.enable_model_cpu_offload(device=device)
    else:
        pipeline.to(device)
    return pipeline


def generate(
    prompt: str,
    destination: Path,
    *,
    seed: int,
    width: int = 1024,
    height: int = 576,
) -> None:
    """Save a deterministic scene still as PNG for a given model and seed."""
    import torch

    if not prompt.strip():
        raise ValueError("Image generation requires a text prompt")
    if any(dimension <= 0 or dimension % 16 for dimension in (width, height)):
        raise ValueError("Generated image dimensions must be positive multiples of 16")
    backend = os.getenv("IMAGE_BACKEND", "flux")
    model_id = model_name()
    device = os.getenv("IMAGE_DEVICE") or ("cuda" if torch.cuda.is_available() else "cpu")
    offload = os.getenv("IMAGE_CPU_OFFLOAD", "0") == "1"
    pipeline = _load(backend, model_id, device, offload, os.getenv("IMAGE_VARIANT") or None)
    options = {
        "guidance_scale": 0.0,
        "num_inference_steps": 4,
        "max_sequence_length": 256,
    } if backend == "flux" else {"guidance_scale": 5.0, "num_inference_steps": 25}
    if backend == "flux2_klein":
        options = {"guidance_scale": 1.0, "num_inference_steps": 4, "max_sequence_length": 128}
    if os.getenv("IMAGE_STEPS"):
        steps = int(os.environ["IMAGE_STEPS"])
        if not 1 <= steps <= 100:
            raise ValueError("IMAGE_STEPS must be between 1 and 100")
        options["num_inference_steps"] = steps
    generator = torch.Generator(device="cpu").manual_seed(seed)
    retry_cpu = False
    try:
        with torch.inference_mode():
            preencoded = bool(os.getenv('IMAGE_PROMPT_CACHE'))
            hybrid = device.startswith("cuda") and os.getenv("IMAGE_TEXT_DEVICE") == "cpu"
            if preencoded:
                embeds = cached_prompt(prompt, backend, model_id, options['max_sequence_length'])
                image = pipeline(prompt=None, prompt_embeds=embeds.to(device), width=width,
                                 height=height, generator=generator, **options).images[0]
            elif hybrid:
                prompt_embeds, _ = pipeline.encode_prompt(
                    prompt, device=torch.device("cpu"),
                    max_sequence_length=options.get("max_sequence_length", 128))
                text_encoder = pipeline.text_encoder
                pipeline.register_modules(text_encoder=None)
                try:
                    pipeline.enable_model_cpu_offload(device=device)
                    image = pipeline(
                        prompt=None, prompt_embeds=prompt_embeds.to(device), width=width,
                        height=height, generator=generator, **options).images[0]
                finally:
                    pipeline.remove_all_hooks()
                    pipeline.register_modules(text_encoder=text_encoder)
            else:
                image = pipeline(prompt=prompt, width=width, height=height, generator=generator, **options).images[0]
    except (torch.OutOfMemoryError, torch.AcceleratorError) as error:
        if not device.startswith("cuda") or "out of memory" not in str(error).lower():
            raise
        if os.getenv('IMAGE_REQUIRE_GPU') == '1':
            raise RuntimeError(f'GPU image allocation failed: {error}') from error
        print(f"GPU image allocation exhausted; retrying generation on CPU. {error}", flush=True)
        retry_cpu = True
    if retry_cpu:
        del pipeline
        _load.cache_clear()
        import gc
        gc.collect()
        torch.cuda.empty_cache()
        os.environ["IMAGE_DEVICE"] = "cpu"
        os.environ["IMAGE_CPU_OFFLOAD"] = "0"
        os.environ["IMAGE_CPU_BF16"] = "1"
        os.environ["IMAGE_STORAGE_FP8"] = "0"
        return generate(prompt, destination, seed=seed, width=width, height=height)

    destination.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=destination.parent, suffix=".png", delete=False) as file:
        temporary = Path(file.name)
    try:
        image.convert("RGB").save(temporary, format="PNG")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)




def release():
    """Return model allocations and cached GPU blocks before hardware encoding."""
    import gc
    import torch

    _load.cache_clear()
    gc.collect()
    if torch.cuda.is_initialized():
        torch.cuda.empty_cache()
