---
language:
  - zh
  - en
tags:
  - document-parsing
  - document-understanding
  - document-intelligence
  - ocr
  - layout-analysis
  - table-extraction
  - formula-recognition
  - code-extraction
  - multimodal
  - vision-language-model
datasets:
  - custom
pipeline_tag: image-text-to-text
library_name: transformers
---

# Dolphin-v2: Universal Document Parsing via Scalable Anchor Prompting

<a href="https://github.com/bytedance/Dolphin"><img src="https://img.shields.io/badge/Code-Github-blue"></a>


## Model Description

Dolphin-v2 is an enhanced universal document parsing model that substantially improves upon the original Dolphin. It seamlessly handles any document type—whether digital-born or photographed—through a document-type-aware two-stage architecture with scalable anchor prompting.

## 📑 Key Improvements

Dolphin-v2 introduces several major enhancements over the original Dolphin:

- **🌐 Universal Document Support**: Handles both digital-born and photographed documents with realistic distortions
- **📊 Expanded Element Coverage**: Supports 21 element categories (up from 14), including dedicated code blocks and formulas
- **🎯 Enhanced Precision**: Uses absolute pixel coordinates for more accurate spatial localization
- **⚡ Hybrid Parsing Strategy**: Element-wise parallel parsing for digital documents + holistic parsing for photographed documents
- **🔬 Specialized Modules**: Dedicated parsing for code blocks with indentation preservation

## 🏗️ Model Architecture

Dolphin-v2 follows a document-type-aware two-stage paradigm:

### Stage 1: Joint Classification and Layout Analysis
- **Document Type Classification**: Distinguishes between digital-born and photographed documents
- **Layout Analysis**: Generates element sequences in reading order with 21 supported categories

### Stage 2: Hybrid Content Parsing
- **Photographed Documents**: Holistic page-level parsing to handle distortions
- **Digital Documents**: Efficient element-wise parallel parsing with type-specific prompts
  - `P_formula`: Specialized LaTeX generation for formulas
  - `P_code`: Code block parsing with indentation preservation
  - `P_table`: HTML representation for tables
  - `P_paragraph`: Text recognition for paragraphs

Built on **Qwen2.5-VL-3B** backbone with:
- Vision encoder based on Native Resolution Vision Transformer (NaViT)
- Autoregressive decoder for structured output generation

## 📈 Performance

Dolphin-v2 achieves superior performance on comprehensive benchmarks:
**OmniDocBench (v1.5):**
- Overall Score: **89.45** (+14.78 over original Dolphin)
- Text Recognition: **0.054** Edit Distance
- Formula Parsing: **86.72** CDM
- Table Structure: **87.02** TEDS / **90.48** TEDS-S
- Reading Order: **0.054** Edit Distance


## 🎯 Supported Element Types
Dolphin-v2 supports 21 document element categories:

| Element Type | Description |
|--------------|-------------|
| `sec_0` - `sec_5` | Hierarchical headings (title, level 1-5) |
| `para` | Regular paragraphs |
| `half_para` | Spanning paragraphs |
| `equ` | Mathematical formulas (LaTeX) |
| `tab` | Tables (HTML) |
| `code` | Code blocks (with indentation) |
| `fig` | Figures |
| `cap` | Captions |
| `list` | Lists |
| `catalogue` | Catalogs |
| `reference` | References |
| `header` / `foot` | Headers/Footers |
| `fnote` | Footnotes |
| `watermark` | Watermarks |
| `anno` | Annotations |


## 📚 Citation
```bibtex
@inproceedings{dolphin2025,
  title={Dolphin: Document Image Parsing via Heterogeneous Anchor Prompting},
  author={Feng, Hao and Wei, Shu and Fei, Xiang and Shi, Wei and Han, Yingdong and Liao, Lei and Lu, Jinghui and Wu, Binghong and Liu, Qi and Lin, Chunhui and Tang, Jingqun and Liu, Hao and Huang, Can},
  booktitle={Proceedings of the 65th Annual Meeting of the Association for Computational Linguistics (ACL)},
  year={2025}
}
```

## 🙏 Acknowledgements

This model builds upon:
- [Hugging Face Transformers](https://github.com/huggingface/transformers)
- [Qwen2.5-VL](https://github.com/QwenLM/Qwen2-VL)
- [Donut](https://github.com/clovaai/donut/)
- [Nougat](https://github.com/facebookresearch/nougat)