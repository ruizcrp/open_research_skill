# open_research_skill

> **Multi-source open-access research for AI agents — with citation provenance that prevents hallucinated references.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Research Skill](https://img.shields.io/badge/research-skill-blue)](https://github.com/topics/research)
[![Open Access](https://img.shields.io/badge/open%20access-%E2%9C%93-brightgreen)](https://www.doaj.org/)

---

## What is it?

`open_research_skill` is a research automation tool for AI agents that searches across **five open-access academic sources**, reads full papers, and enforces a **citation provenance system** that prevents hallucinated references.

Every citation is grounded in actual document content — no more fabricated papers, wrong DOIs, or made-up quotes.

## Why it exists

AI systems generate plausible-sounding but entirely fabricated references at alarming rates:
- ChatGPT's references exist only **14% of the time** [Zuccon et al., 2023]
- Bard hallucinated **91.4%** of systematic review references [Chelli et al., 2024]

This tool solves that problem by requiring **every cited claim to be verified** against actual document content.

## Features

### 🔍 Multi-source search
| Source | Coverage | Full Text | API Key |
|--------|----------|-----------|---------|
| **OpenAlex** ⭐ | 250M+ works | Selective (OA) | No |
| **arXiv** | 2.3M+ papers | Yes (PDF) | No |
| **CrossRef** | 150M+ DOIs | Metadata | No |
| **Semantic Scholar** | 200M+ papers | Selective | Optional |
| **PubMed Central** | 8M+ articles | Yes (XML) | No |

### 📄 Four-tier citation provenance

| Tier | What was read | Can cite? |
|------|--------------|-----------|
| **Read** | Full PDF, page-level | ✅ Yes, with page numbers |
| **Abstract** | Abstract text | ✅ Yes, abstract claims only |
| **Metadata** | Title, authors, year, DOI | ⚠️ Context only |
| **Discovery** | Search result only | ❌ No |

### ✅ Claim verification
- Download PDFs and extract text with page numbers
- Search for specific claims and return page-level evidence
- Generate bibliography verification files for human review

### 🧹 Deduplication
- Identifies the same paper across multiple sources
- Priority: DOI → arXiv ID → PMC ID → title similarity

## Quick Start

```bash
# Install dependencies
pip install arxiv crossref semanticscholar requests PyMuPDF pdfplumber

# Search across all sources
python research_workflow.py search "porphyria transcriptomics" --max-results 5

# Read a full paper
python research_workflow.py read-paper 10.5281/zenodo.6936227

# Full analysis with paper reading
python research_workflow.py full-analysis "AI research agents" --read-papers

# Generate bibliography verification
python research_workflow.py bibliography --output bib_verify.json
```

### Programmatic usage

```python
from research_workflow import (
    search_openalex, search_arxiv, search_crossref,
    search_pmc, search_semantic_scholar,
    read_paper_full, verify_claim_in_paper,
    generate_bibliography
)

# Search
papers = search_openalex("gene therapy", max_results=10)

# Read a paper with provenance tracking
citation = read_paper_full(
    doi="10.1016/j.example.2024.01.001",
    title="Example Paper Title",
    authors="Author, A.",
    year=2024,
    source="OpenAlex"
)

# Verify a claim in a previously-read paper
verified, locations = verify_claim_in_paper("paper_20260512_120000", "the treatment improved outcomes by 40%")
```

## Project Structure

```
openresearch/
├── research_workflow.py          # Main workflow (897 lines)
├── CITATION.cff                  # Machine-readable citation metadata
├── .zenodo.json                  # Zenodo archive metadata
├── test_research_tools.py        # Test suite
├── references.bib                # Bibliography (BibTeX)
├── research_paper.tex       # Research paper (LaTeX)
├── papers/                       # Downloaded PDFs
├── pages/                        # Page-level extracted text
└── *.json                        # Search results
```

## Citation Provenance in Action

```json
{
  "identifiers": {"doi": "10.5281/zenodo.6936227"},
  "title": "OpenAlex: A fully-open index of scholarly works...",
  "provenance": {
    "tier": "read",
    "page": 3,
    "section": "Introduction",
    "claim_verified": true,
    "abstract_text": "OpenAlex is a fully-open index..."
  },
  "verified_claims": [
    {
      "claim": "OpenAlex contains 250M+ works",
      "verified": true,
      "page": 3,
      "context": "...OpenAlex provides a comprehensive index of over 250 million scholarly works..."
    }
  ]
}
```

## Limitations

- **Open access only** — paywalled papers are identified but cannot be read
- **PDF parsing** — works well for most PDFs, may struggle with scanned documents
- **Semantic Scholar** — free tier is rate-limited; API key recommended for production use

## License

MIT License — feel free to use, modify, and contribute.

## BibTeX

```bibtex
@software{ruizpalmero2026open_research_skill,
  title = {{open\_research\_skill: Multi-Source Open-Access Research for AI Agents}},
  author = {Ruiz-Palmero, Christian},
  year = {2026},
  version = {1.0.0},
  url = {https://github.com/ruizcrp/open_research_skill},
  license = {MIT}
}
```

## Related Work

- [Orchestra-Research/AI-Research-SKILLs](https://github.com/Orchestra-Research/AI-Research-SKILLs) — Comprehensive AI research skills library
- [Feynman](https://github.com/Spartan-AI/Feynman) — AI research agent that reads papers and writes drafts
- [AI Scientist](https://github.com/autoagent-ai/AI-Scientist) — Autonomous scientific discovery with LLMs
- [LitLLM](https://github.com/.../litllm) — Literature review toolkit for LLMs

## Contributing

Contributions are welcome! Whether it's bug fixes, new search sources, or documentation improvements — just open an issue or PR.

## Citation

If you use this tool in your research, please cite it:

```bibtex
@software{ruizpalmero2026open_research_skill,
  title = {{open\_research\_skill: Multi-Source Open-Access Research for AI Agents}},
  author = {Ruiz-Palmero, Christian},
  year = {2026},
  version = {1.0.0},
  url = {https://github.com/ruizcrp/open_research_skill},
  license = {MIT}
}
```
