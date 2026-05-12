# open_research - Research Assistant Skill

**Purpose:** Comprehensive research assistant for finding, downloading, reading, and analyzing academic papers.

---

## ⚠️ CRITICAL: CITATION VERIFICATION POLICY

**NEVER add a citation to a bibliography without first verifying it through an API.**

### Why This Matters
- LLMs frequently generate **hallucinated citations** — fake papers with plausible-looking DOIs/arXiv IDs
- A fake citation can look completely real (correct format, real author names, fake DOI)
- Once published, hallucinated citations damage credibility and propagate misinformation
- **Example:** arXiv ID 2308.12345 was claimed to be about "ChatGPT hallucinated citations" but actually points to a cosmology paper about early gravity modification

### The Rule
**Every citation MUST pass through `verify_citation()` before being added to any bibliography or paper.**

### How to Verify
```python
from research_workflow import verify_citation

# Verify by DOI (most reliable)
result = verify_citation(doi="10.1101/2024.01.01.123456")

# Verify by arXiv ID
result = verify_citation(arxiv_id="2403.08399")

# Verify by title (fallback)
result = verify_citation(title="Your Paper Title", authors=["Smith, J"], year=2024)

if result:
    print(f"VERIFIED: {result['title']}")
    # Add to bibliography
else:
    print("REJECTED: Citation not found in any database")
    # Do NOT add to bibliography
```

### Verification Sources (in order of reliability)
1. **OpenAlex** — 100% open access, no paywalls, comprehensive
2. **arXiv API** — Direct verification of arXiv IDs
3. **CrossRef** — DOI resolution and metadata
4. **Semantic Scholar** — Fallback for metadata

### If Verification Fails
- **Do NOT** add the citation to the bibliography
- **Do NOT** guess or fabricate a DOI/arXiv ID
- **Do** search for the paper using the search functions in this skill
- **Do** use the actual paper you found and verified
- **Do** note in your memory that the original citation was rejected

---

## Installed Tools:
- **OpenAlex** (vREST) - PRIMARY source for open access papers (no package needed!)
- `arxiv` (v3.0.0) - arXiv paper search and download
- `crossref` (v0.1.2) - CrossRef API for DOI/metadata lookup
- `semanticscholar` (v0.12.0) - Semantic Scholar API (rate-limited, use sparingly)
- `requests` (v2.33.1) - HTTP requests for PMC API
- PyMuPDF/pdfplumber - PDF reading (already installed)

---

## Quick Start

### 1. Search for Papers

#### OpenAlex (PRIMARY - Open Access)
```python
import requests

# Search works (papers)
url = 'https://api.openalex.org/works'
params = {
    'search': 'porphyria transcriptomics',
    'per_page': 10,
    'mailto': 'you@example.com'  # recommended for rate limiting
}
r = requests.get(url, params=params, timeout=15)
d = r.json()

print(f"Found {d['meta']['count']} results")
for w in d['results']:
    print(f"- {w['display_name']}")
    print(f"  Year: {w['publication_year']} | Citations: {w['cited_by_count']}")
    print(f"  DOI: {w['doi']}")
    print(f"  Open Access: {w['open_access']['is_oa']}")
    if w.get('best_oa_location'):
        print(f"  PDF: {w['best_oa_location'].get('pdf_url', 'N/A')}")
    print()
```

**Key features:**
- 100% open access - no paywalls, no Sci-Hub needed
- Full metadata: citations, authorships, institutions, concepts, topics
- Direct PDF URLs for open access papers
- Related works, referenced works, citation networks
- Filter by year, open access, institutions, etc.
- No API key required, very generous rate limits

**Query patterns:**
```python
# Filter by open access only
params['filter'] = 'open_access.is_oa:true'

# Filter by year range
params['filter'] = 'publication_year:2020-2026'

# Sort by citation count
params['sort'] = 'cited_by_count:desc'

# Get related works for a paper
related_url = f"https://api.openalex.org/works/{work_id}/related_works"

# Get citations for a paper
cite_url = f"https://api.openalex.org/works/{work_id}/cited_by"
```

**Recommended `mailto` parameter:** `christian.ruiz@z01.ch`
import arxiv
results = list(arxiv.Search(query="your topic", max_results=10).results())
for r in results:
    print(f"{r.title} - {r.published.date()} - {r.summary[:200]}...")

# CrossRef search
import crossref
cr = crossref.CrossRefAPIClient()
response = cr.get_works(params={"query": "your topic"})
data = response.json()
for item in data['message']['items'][:10]:
    print(f"{item.get('title', ['N/A'])[0]} - DOI: {item.get('DOI')}")

# Semantic Scholar search (use sparingly - rate limited)
from semanticscholar import SemanticScholar
sh = SemanticScholar()
results = sh.search_paper("your topic", limit=5)
for r in results:
    print(f"{r.title} - {r.year} - Citations: {r.citationCount}")
```

### 2. Download Papers

```python
# Download arXiv paper
import arxiv
paper = arxiv.Search(query="topic", max_results=1).next()
paper.download_pdf()  # Downloads to current directory

# Download from DOI (CrossRef + arXiv/PMC)
import crossref
cr = crossref.CrossRefAPIClient()
response = cr.get_works(params={"query": "topic"})
data = response.json()
doi = data['message']['items'][0]['DOI']
# Use arXiv or PMC to get the PDF
```

### 3. Read PDFs

```python
import fitz  # PyMuPDF
doc = fitz.open("paper.pdf")
text = ""
for page in doc:
    text += page.get_text()
print(text[:1000])  # First 1000 chars
```

### 4. Search PMC Full Text

```python
import requests
# Search PMC
url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
params = {"db": "pmc", "term": "your topic", "retmax": 10, "retmode": "json"}
response = requests.get(url, params=params)
data = response.json()
pmc_ids = data['esearchresult']['idlist']

# Get full text
text_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
text_params = {"db": "pmc", "id": pmc_ids[0], "retmode": "xml"}
text_response = requests.get(text_url, params=text_params)
# Parse XML to extract text
import re
text_content = re.sub(r'<[^>]+>', ' ', text_response.text)
text_content = ' '.join(text_content.split())
```

---

## Research Workflow

1. **Search** → Use OpenAlex FIRST (open access, no paywalls), then arXiv + CrossRef + Semantic Scholar
2. **Filter** → Sort by relevance, citation count, date, open access status
3. **Download** → Get PDFs from OpenAlex OA links, arXiv, or PMC
4. **Extract** → Read PDFs with PyMuPDF
5. **Verify** → Verify ALL citations before adding to bibliography (CRITICAL!)
6. **Summarize** → Create structured summaries
7. **Store** → Save to workspace for future reference

### Adding Citations to Bibliography

**ALWAYS use this pattern:**

```python
from research_workflow import verify_and_add_to_bibliography

# Example: Add a verified citation
citation = {
    "title": "OpenAlex: A fully-open index of scholarly works",
    "doi": "10.5281/zenodo.6936227",
    "year": 2022
}

if verify_and_add_to_bibliography(citation, "references.bib"):
    print("Citation added to bibliography")
else:
    print("Citation rejected - not found in any database")
```

**Or verify manually:**

```python
from research_workflow import verify_citation

result = verify_citation(doi="10.5281/zenodo.6936227")
if result:
    print(f"Verified: {result['title']}")
    # Add to bibliography manually
else:
    print("Not verified - do NOT add to bibliography")
```

**Priority order for finding papers:**
1. OpenAlex (open access, full metadata, no paywalls)
2. arXiv (preprints, free)
3. PMC (biomedical, free full text)
4. CrossRef (metadata only, use for DOI lookups)
5. Semantic Scholar (use sparingly, rate-limited)

---

## Rate Limiting

- **OpenAlex:** Very generous, no strict limits. Include `mailto` param for courtesy.
- **Semantic Scholar:** 200 requests/5 minutes (free tier)
- **CrossRef:** No strict limits, but be respectful
- **arXiv:** No strict limits, but be respectful
- **PMC/NCBI:** 3 requests/second (use delays between calls)

---

## Error Handling

- Always check API response status codes
- Implement retry logic with exponential backoff
- Handle rate limiting gracefully
- Log errors for debugging

---

## File Storage

Save research outputs to:
- `research/` - Downloaded papers and notes
- `memory/` - Daily research notes
- `content/` - Analysis reports and summaries

---

## Notes

- **OpenAlex is the PRIMARY search source** - always try it first for open access papers
- arXiv API deprecated `.results()` method - use `Client.results()` instead
- CrossRef returns Response objects - parse JSON to get data
- Semantic Scholar is rate-limited - use sparingly
- PMC full text is free and unlimited - great for biomedical research
- Always verify gene symbols and data quality in research
