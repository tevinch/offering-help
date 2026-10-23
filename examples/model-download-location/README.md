# Choose where MOSS-Image model files are downloaded

For MOSS-Image's official Python and Gradio entry points, set `HF_HUB_CACHE` before starting Python to choose the shared download cache. To keep a complete model in a regular directory, use `hf download --local-dir` and pass that directory as the model.

These examples use `OpenMOSS-Team/MOSS-Image-Base`. Substitute `OpenMOSS-Team/MOSS-Image-SFT` if that is the model you want. They assume you have already installed MOSS-Image using its [official setup instructions](https://github.com/OpenMOSS/MOSS-Image#installation).

## 1. Choose a shared cache

Linux or macOS, from the MOSS-Image repository:

```sh
export HF_HUB_CACHE="/absolute/path/model-cache"
python gradio_app.py --model OpenMOSS-Team/MOSS-Image-Base
```

Windows PowerShell:

```powershell
$env:HF_HUB_CACHE = "D:\models\hub-cache"
python gradio_app.py --model OpenMOSS-Team/MOSS-Image-Base
```

The same environment variable applies when running the official Python quickstart with a Hub model ID. Set it in the shell before launching Python. If using a notebook, set it before importing Hugging Face libraries; restart the kernel if they are already imported.

The cache uses a structure such as:

```text
model-cache/
  models--OpenMOSS-Team--MOSS-Image-Base/
    blobs/
    snapshots/<revision>/
```

This selects future downloads and reuse in the chosen cache. It does not move existing downloads. `HF_HUB_CACHE` takes precedence over the default `HF_HOME/hub` location; an explicit `cache_dir` passed by application code can override it. The current official MOSS-Image loader does not pass one. Passing an existing local model directory uses that directory instead.

`HF_HUB_CACHE` controls Hub downloads, not every runtime file. Diffusers can also copy custom pipeline code into its separate [modules cache](https://github.com/huggingface/diffusers/blob/v0.41.0/src/diffusers/utils/constants.py), which defaults to `HF_HOME/modules`. Set `HF_HOME` before launch if you also want to relocate that default; an explicit `HF_MODULES_CACHE` takes precedence for modules.

## 2. Download a complete model into a regular directory

First preview the files and download size without downloading their contents:

```sh
hf download OpenMOSS-Team/MOSS-Image-Base --local-dir "/absolute/path/models/MOSS-Image-Base" --dry-run
```

Then download the complete repository and launch the existing Gradio app with its local path:

```sh
hf download OpenMOSS-Team/MOSS-Image-Base --local-dir "/absolute/path/models/MOSS-Image-Base"
python gradio_app.py --model "/absolute/path/models/MOSS-Image-Base"
```

Use a Windows path in PowerShell, for example `"D:\models\MOSS-Image-Base"`. The `hf` command is provided by `huggingface-hub`.

Do not combine `--local-dir` and `--cache-dir`. Local-directory downloads keep the repository's file layout and a small `.cache/huggingface` metadata directory inside the destination. Keep the complete bundle: `model_index.json`, `pipeline_moss_image.py`, and the `transformer`, `text_encoder`, `tokenizer`, `vae` and `scheduler` directories, including their configurations, tokenizer assets, code, shard indexes and all weight shards. Downloading just the transformer weights is insufficient for this entry point. Follow the model's own license for its files; this guide's MIT license covers only this guide and verification script.

For the official Python quickstart, replace the Hub ID passed to `DiffusionPipeline.from_pretrained(...)` with the same complete local path, keeping its other loading arguments.

`--model-root` in the Gradio app discovers existing local model directories; it is not a download destination setting. `--output-dir` controls generated images. ComfyUI's native split-weight directories and the HF Loader's local `model_path` are separate; follow the [official ComfyUI instructions](https://github.com/OpenMOSS/MOSS-Image/blob/main/comfyui/README.md) for that workflow.

## Check file placement with a tiny download

The included script downloads only two JSON configuration files, totaling 906 bytes, from a fixed public Base-model revision. It parses them, verifies that their resolved paths are inside your chosen directory, and prints their sizes and SHA-256 hashes. It downloads no weights or Python code and does not run a model. These two files alone are not a usable model bundle.

In a separate Python 3.10+ environment, from this guide's directory:

```sh
python -m venv .venv
# Linux/macOS:
. .venv/bin/activate
# Windows PowerShell instead:
# .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

python verify_location.py cache "./location check/cache"
python verify_location.py cache "./location check/cache" --offline
python verify_location.py local "./location check/local"
python verify_location.py local "./location check/local" --offline
```

Both online runs should print the same two file hashes; both offline runs should succeed without downloading again. Cache mode uses `HF_HUB_CACHE` without an explicit `cache_dir`, so it checks the environment setting itself. Local mode uses the same `local_dir` option as the CLI. An empty destination with `--offline` must fail:

```sh
python verify_location.py cache "./location check/not-downloaded" --offline
```

Checked with `huggingface-hub==2.3.0`: real downloads to fresh directories with spaces, offline reuse with unchanged contents and timestamps, and failure for empty offline destinations and an omitted cache setting. The full-repository CLI dry run checks the intended download scope. Validation covers download placement and reuse; it does not cover model loading, image generation, the Gradio UI or ComfyUI.

The loading arguments were checked against [MOSS-Image's loader](https://github.com/OpenMOSS/MOSS-Image/blob/52b87fca23acedc399d062d593bec388aee9926a/inference_runtime.py) and [Gradio entry point](https://github.com/OpenMOSS/MOSS-Image/blob/52b87fca23acedc399d062d593bec388aee9926a/gradio_app.py). Hugging Face documents [environment-variable precedence](https://huggingface.co/docs/huggingface_hub/package_reference/environment_variables) and [local-directory downloads](https://huggingface.co/docs/huggingface_hub/guides/download#download-files-to-a-local-folder).

## Optional coffee

This guide is free. If it saved you time, an optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
