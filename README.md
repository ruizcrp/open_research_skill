# i4ju Research Infrastructure

## Overview

Comprehensive research assistant for finding, downloading, reading, and analyzing academic papers.

## Available Tools

### 1. arXiv API
- **Package:** `arxiv` (v3.0.0)
- **Cost:** Free, no API key needed
- **Use case:** Preprint papers, especially in CS, physics, math, biology
- **Limitations:** No full-text PDFs for all papers, rate limiting

### 2. CrossRef API
- **Package:** `crossref` (v0.1.2)
- **Cost:** Free, no API key needed
- **Use case:** DOI lookup, citation metadata, journal information
- **Limitations:** No full text, just metadata

### 3. PMC/NCBI E-utilities
- **Package:** `requests` (built-in)
- **Cost:** Free, no API key needed
- **Use case:** Full-text biomedical articles (11,730+ on porphyria)
- **Limitations:** XML parsing required, slower than APIs

### 4. Semantic Scholar API
- **Package:** `semanticscholar` (v0.12.0)
- **Cost:** Free tier (200 req/5 min), API key for higher limits
- **Use case:** Citation networks, paper recommendations
- **Limitations:** Rate limited, needs API key for production use

### 5. PDF Reading
- **Packages:** PyMuPDF (fitz), pdfplumber, pdfminer.six
- **Cost:** Free, open source
- **Use case:** Extract text from PDFs
- **Limitations:** Cannot read images/scans without OCR

## Quick Start

### Search for Papers
```python
# arXiv
import arxiv
results = list(arxiv.Search(query="topic", max_results=5).results())

# CrossRef
import crossref
cr = crossref.CrossRefAPIClient()
response = cr.get_works(params={"query": "topic"})
data = response.json()
items = data['message']['items']

# PMC
import requests
url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
params = {"db": "pmc", "term": "topic", "retmax": 10, "retmode": "json"}
response = requests.get(url, params=params)
data = response.json()
pmc_ids = data['esearchresult']['idlist']
```

### Download and Read PDFs
```python
# Download
import urllib.request
urllib.request.urlretrieve("https://arxiv.org/pdf/2401.00001.pdf", "paper.pdf")

# Read
import fitz
doc = fitz.open("paper.pdf")
text = ""
for page in doc:
    text += page.get_text()
```

### Research Workflow Script
```bash
# Search all sources
python3 research_workflow.py search "porphyria transcriptomics" --max-results 5

# Search PMC specifically
python3 research_workflow.py pmc-search "porphyria" --max-results 10

# Read a PDF
python3 research_workflow.py read paper.pdf

# Full analysis
python3 research_workflow.py full-analysis "topic"
```

## File Structure
```
research/
├── README.md              # This file
├── SKILL.md               # Skill documentation
├── research_workflow.py   # Main workflow script
├── test_research_tools.py # Test suite
├── test_results.json      # Test results
└── research_*.json        # Research output files
```

## Rate Limiting
- **Semantic Scholar:** 200 requests/5 minutes (free tier)
- **CrossRef:** No strict limits, be respectful
- **arXiv:** No strict limits, be respectful
- **PMC/NCBI:** 3 requests/second

## Future Enhancements
1. Add Semantic Scholar API key for higher rate limits
2. Implement citation network analysis
3. Add full-text search across downloaded papers
4. Create interactive dashboard for research results
5. Add support for institutional access (paywalled content)

## Notes
- arXiv API deprecated `.results()` method - use `Client.results()` instead
- CrossRef returns Response objects - parse JSON to get data
- PMC full text is free and unlimited - great for biomedical research
- Always verify gene symbols and data quality in research
