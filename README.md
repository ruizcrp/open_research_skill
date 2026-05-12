# open_research_skill

Open-source research assistant for finding, downloading, reading, and analyzing academic papers.

## Overview

Comprehensive research assistant with support for multiple academic sources (arXiv, CrossRef, PMC, Semantic Scholar, OpenAlex), PDF reading, and automated analysis workflows.

## Available Tools

### 1. arXiv API
- **Package:** `arxiv` (v3.0.0)
- **Cost:** Free, no API key needed
- **Use case:** Preprint papers (CS, physics, math, biology)
- **Limitations:** No full-text for all papers, rate limiting

### 2. CrossRef API
- **Package:** `crossref` (v0.1.2)
- **Cost:** Free, no API key needed
- **Use case:** DOI lookup, citation metadata, journal information
- **Limitations:** No full text, metadata only

### 3. PMC/NCBI E-utilities
- **Package:** `requests` (built-in)
- **Cost:** Free, no API key needed
- **Use case:** Full-text biomedical articles
- **Limitations:** XML parsing required

### 4. Semantic Scholar API
- **Package:** `semanticscholar` (v0.12.0)
- **Cost:** Free tier (200 req/5 min), API key for higher limits
- **Use case:** Citation networks, paper recommendations
- **Limitations:** Rate limited

### 5. OpenAlex API ⭐ PRIMARY
- **Cost:** Free, no API key needed
- **Use case:** Open access papers, citations, metadata
- **Advantages:** 100% open access, no paywalls, generous rate limits

### 6. PDF Reading
- **Packages:** PyMuPDF (fitz), pdfplumber, pdfminer.six
- **Cost:** Free, open source
- **Use case:** Extract text from PDFs

## Quick Start

### Install Dependencies
```bash
pip install arxiv crossref semanticscholar requests PyMuPDF pdfplumber
```

### Search for Papers
```bash
# Search all sources
python3 research_workflow.py search "topic" --max-results 5

# Search PMC specifically
python3 research_workflow.py pmc-search "topic" --max-results 10

# Read a PDF
python3 research_workflow.py read paper.pdf

# Full analysis
python3 research_workflow.py full-analysis "topic"
```

### API Usage
```python
# OpenAlex (recommended)
import requests
url = 'https://api.openalex.org/works'
params = {'search': 'topic', 'per_page': 10}
r = requests.get(url, params=params, timeout=15)
papers = r.json()['results']

# arXiv
import arxiv
results = list(arxiv.Client().Search(query="topic", max_results=5).results())

# CrossRef
import crossref
cr = crossref.CrossRefAPIClient()
response = cr.get_works(params={"query": "topic"})
data = response.json()
```

## File Structure
```
open_research_skill/
├── README.md                  # This file
├── SKILL.md                   # Skill documentation
├── research_workflow.py       # Main workflow script
├── research_workflow_v2.py    # Alternative workflow
├── test_research_tools.py     # Test suite
├── test_correct_citations.py  # Citation verification tests
└── test_metadata_mismatch.py  # Metadata mismatch tests
```

## Rate Limiting
- **Semantic Scholar:** 200 requests/5 minutes (free tier)
- **CrossRef:** No strict limits, be respectful
- **arXiv:** No strict limits, be respectful
- **PMC/NCBI:** 3 requests/second
- **OpenAlex:** No strict limits, very generous

## Development
Run the test suite:
```bash
python3 test_research_tools.py
```

## Rate Limit Workarounds
- Use OpenAlex as primary source (no rate limits, full metadata)
- arXiv + CrossRef + PMC as fallback sources
- Semantic Scholar API key for higher limits: set `S2_API_KEY` env var

## Notes
- arXiv API uses `Client().Search()` method (`.results()` is deprecated)
- CrossRef returns Response objects — parse JSON
- PMC full text is free and unlimited
- Always verify gene symbols and data quality in research
- **Citation verification is mandatory** — never add unverified citations

## License
MIT
