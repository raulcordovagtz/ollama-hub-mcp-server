---
license: apache-2.0
library_name: mlx
pipeline_tag: text-to-speech
base_model:
- k2-fsa/OmniVoice
tags:
- mlx
- apple-silicon
- text-to-speech
- voice-cloning
- multilingual
language:
- multilingual
---

Part of the [OmniVoice MLX](https://huggingface.co/collections/mlx-community/omnivoice-6a06f610945a0b1d85b3b839) collection.

# OmniVoice-bfloat16 (MLX)

Apple MLX weights for [k2-fsa/OmniVoice](https://github.com/k2-fsa/OmniVoice), a massively multilingual zero-shot TTS model. This is a community MLX conversion for Apple Silicon; the upstream model card, license, and repository remain authoritative for non-MLX usage.

## TL;DR

| | |
|---|---|
| **Variant** | bfloat16 |
| **Best for** | smaller high-quality baseline for Apple Silicon |
| **Runtime** | [`ailuntx/OmniVoice-MLX`](https://github.com/ailuntx/OmniVoice-MLX) |
| **Official code** | [`k2-fsa/OmniVoice`](https://github.com/k2-fsa/OmniVoice) |
| **Format** | MLX safetensors + tokenizer/config assets |
| **Hardware** | Apple Silicon recommended; HF Spaces Linux CPU fallback can be slow |

## Quick Start

```bash
hf download mlx-community/OmniVoice-bfloat16 --local-dir ./models/OmniVoice-bfloat16

git clone https://github.com/ailuntx/OmniVoice-MLX.git
cd OmniVoice-MLX
python -m venv .venv
.venv/bin/pip install -e .
```

Run a minimal generation from the MLX helper repository:

```bash
.venv/bin/python scripts/infer_mlx.py \
  --model ./models/OmniVoice-bfloat16 \
  --text "Hello from OmniVoice MLX." \
  --language en \
  --output output.wav
```

## Variants

| Variant | Best for |
|---|---|
| [`OmniVoice`](https://huggingface.co/mlx-community/OmniVoice) | default entry |
| [`OmniVoice-fp32`](https://huggingface.co/mlx-community/OmniVoice-fp32) | high-precision baseline |
| [`OmniVoice-bfloat16`](https://huggingface.co/mlx-community/OmniVoice-bfloat16) | high-quality Apple Silicon use |
| [`OmniVoice-8bit`](https://huggingface.co/mlx-community/OmniVoice-8bit) | smaller local checkpoint |
| [`OmniVoice-4bit`](https://huggingface.co/mlx-community/OmniVoice-4bit) | smallest checkpoint and Space default |

## Layout

```text
OmniVoice-bfloat16/
├── config.json
├── model.safetensors / shards
├── tokenizer files
├── audio_tokenizer/
└── mlx_manifest.json
```

## Conversion Notes

| Component | Source | MLX handling |
|---|---|---|
| main model | `k2-fsa/OmniVoice` | converted to MLX weights |
| tokenizer/config | official checkpoint | copied for runtime compatibility |
| audio tokenizer | official OmniVoice assets | included as a required subcomponent |

## Validation

Local MLX smoke tests were used during conversion. For voice cloning checks, use a full audio tokenizer; slim tokenizer assets can decode audio but do not provide a reliable speaker-encoding path.

## License

License follows the upstream OmniVoice release.

## Citation

```bibtex
@misc{omnivoice-mlx,
  title  = {OmniVoice-MLX: Apple MLX port of OmniVoice},
  author = {ailuntx},
  year   = {2026},
  url    = {https://github.com/ailuntx/OmniVoice-MLX},
}

@article{zhu2026omnivoice,
  title   = {OmniVoice: Towards Omnilingual Zero-Shot Text-to-Speech with Diffusion Language Models},
  author  = {Zhu, Han and Ye, Lingxuan and Kang, Wei and Yao, Zengwei and Guo, Liyong and Kuang, Fangjun and Han, Zhifeng and Zhuang, Weiji and Lin, Long and Povey, Daniel},
  journal = {arXiv preprint arXiv:2604.00688},
  year    = {2026},
}
```
