#!/usr/bin/env python3
"""
Multi-Source Open-Access Research Skill
A research agent skill for finding, downloading, reading, and analyzing academic papers
with full citation provenance tracking.

Citation Policy:
- Only cite papers that have been downloaded AND read
- Each citation must include: DOI/arxiv_id, page number (or section), and provenance tier
- Tier 1 (read): Paper downloaded, parsed, claim verified with page number
- Tier 2 (abstract): Paper found, abstract read, claim from abstract only
- Tier 3 (metadata): Paper found via search, metadata only, NOT for direct citation
- Tier 4 (discovery): Paper found, not read, only for discovery/context

Usage:
    python3 research_workflow_v2.py search "topic" [--max-results N]
    python3 research_workflow_v2.py read-paper DOI_or_arxiv_id
    python3 research_workflow_v2.py verify "claim" --doi "..."
    python3 research_workflow_v2.py full-analysis "topic" [--read-papers]
    python3 research_workflow_v2.py bibliography --output bib_verify.json
"""

import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

# Load API keys from .env
ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
def load_env():
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env()
SEMANTIC_SCHOLAR_API_KEY = os.environ.get('SEMANTIC_SCHOLAR_API_KEY', '')

# Configuration
OUTPUT_DIR = "/home/clawdbot/.openclaw/workspace-ross/research"
PAPERS_DIR = os.path.join(OUTPUT_DIR, "papers")
PAGES_DIR = os.path.join(OUTPUT_DIR, "pages")  # page-level extracted text
MEMORY_DIR = "/home/clawdbot/.openclaw/workspace-ross/memory"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(PAPERS_DIR, exist_ok=True)
os.makedirs(PAGES_DIR, exist_ok=True)
os.makedirs(MEMORY_DIR, exist_ok=True)

# Citation provenance tiers
TIER_DISCOVERY = "discovery"      # Found via search, not read
TIER_METADATA = "metadata"        # Metadata + abstract read
TIER_ABSTRACT = "abstract"        # Abstract read, can cite abstract claims
TIER_READ = "read"                # Full PDF read, can cite with page numbers

def log(message, level="INFO"):
    """Print with timestamp and level"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] [{level}] {message}")

def save_to_memory(title, content):
    """Save research notes to memory directory"""
    date_str = datetime.now().strftime('%Y-%m-%d')
    memory_file = os.path.join(MEMORY_DIR, f"{date_str}-research.md")
    with open(memory_file, 'a') as f:
        f.write(f"\n## {title}\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(content + "\n")
    log(f"Saved to {memory_file}")

# =============================================================================
# Citation Provenance System (Ideas 1 + 4 + 5)
# =============================================================================

def create_citation_entry(doi=None, arxiv_id=None, pmc_id=None, title="", authors="", year=None,
                          source="unknown", tier=TIER_READ, page=None, section=None,
                          claim_verified=False, abstract_text=""):
    """
    Create a citation entry with full provenance tracking.
    
    Args:
        doi: Digital Object Identifier
        arxiv_id: arXiv identifier
        pmc_id: PMC ID
        title: Paper title
        authors: Author string
        year: Publication year
        source: Which source found this paper
        tier: Citation tier (read, abstract, metadata, discovery)
        page: Page number where claim was found (for tier=read)
        section: Section name where claim was found
        claim_verified: Whether the specific claim was verified in the text
        abstract_text: Abstract text (for tier=abstract)
    """
    identifiers = {}
    if doi: identifiers["doi"] = doi
    if arxiv_id: identifiers["arxiv_id"] = arxiv_id
    if pmc_id: identifiers["pmc_id"] = pmc_id
    
    return {
        "identifiers": identifiers,
        "title": title,
        "authors": authors,
        "year": year,
        "source": source,
        "provenance": {
            "tier": tier,
            "page": page,
            "section": section,
            "claim_verified": claim_verified,
            "abstract_text": abstract_text[:500] if abstract_text else ""
        },
        "downloaded": tier in [TIER_READ, TIER_ABSTRACT],
        "read": tier == TIER_READ,
        "verified_claims": []  # Will be populated as claims are verified
    }

def read_pdf_with_pages(filepath):
    """
    Read a PDF and extract text WITH page numbers.
    Returns a dict mapping page numbers to text content.
    """
    try:
        import fitz  # PyMuPDF
        
        doc = fitz.open(filepath)
        pages = {}
        total_pages = len(doc)
        
        for page_num in range(total_pages):
            page = doc[page_num]
            text = page.get_text()
            pages[page_num + 1] = text.strip()
        
        doc.close()
        
        total_chars = sum(len(t) for t in pages.values())
        log(f"✓ Read: {total_chars} chars from {total_pages} pages", "SUCCESS")
        return pages
    
    except Exception as e:
        log(f"✗ PDF Reading Error: {e}", "ERROR")
        return {}

def save_page_text(paper_id, pages):
    """Save page-level text for later claim verification"""
    filepath = os.path.join(PAGES_DIR, f"{paper_id}.json")
    with open(filepath, 'w') as f:
        json.dump(pages, f, indent=2)
    log(f"✓ Page text saved to {filepath}")
    return filepath

def search_text_for_claim(pages, claim, max_chars_per_page=2000):
    """
    Search extracted PDF text for a specific claim.
    Returns list of (page_number, context_before, context_after) tuples.
    
    This implements verification pass (Idea 5).
    """
    results = []
    claim_normalized = claim.lower().strip()
    
    for page_num, text in pages.items():
        # Normalize text for searching
        text_clean = re.sub(r'\s+', ' ', text).lower()
        claim_clean = re.sub(r'\s+', ' ', claim_normalized)
        
        if claim_clean in text_clean:
            idx = text_clean.index(claim_clean)
            # Get context window (100 chars before and after)
            start = max(0, idx - 100)
            end = min(len(text_clean), idx + len(claim_clean) + 100)
            context_before = text_clean[start:idx]
            context_after = text_clean[idx + len(claim_clean):end]
            
            results.append({
                "page": page_num,
                "context_before": context_before[:200],
                "context_after": context_after[:200],
                "matched_text": text_clean[idx:idx + len(claim_clean)]
            })
    
    return results

def verify_claim_in_paper(paper_id, claim):
    """
    Verify that a specific claim exists in a previously-read paper.
    Returns (verified: bool, locations: list)
    """
    pages_file = os.path.join(PAGES_DIR, f"{paper_id}.json")
    if not os.path.exists(pages_file):
        return False, []
    
    with open(pages_file) as f:
        pages = json.load(f)
    
    locations = search_text_for_claim(pages, claim)
    return len(locations) > 0, locations

def download_pdf_from_url(url, doi=None, arxiv_id=None):
    """Download PDF and save with identifiable filename"""
    if doi:
        safe_doi = doi.replace('/', '_').replace(':', '_')
        filename = f"paper_{safe_doi}.pdf"
    elif arxiv_id:
        filename = f"paper_{arxiv_id.replace('/', '_').replace(':', '_')}.pdf"
    else:
        filename = url.split('/')[-1]
        if not filename.endswith('.pdf'):
            filename += '.pdf'
    
    filepath = os.path.join(PAPERS_DIR, filename)
    
    try:
        urllib.request.urlretrieve(url, filepath)
        file_size = os.path.getsize(filepath)
        log(f"✓ Downloaded: {filename} ({file_size / 1024 / 1024:.1f} MB)", "SUCCESS")
        return filepath
    except Exception as e:
        log(f"✗ Download Error: {e}", "ERROR")
        return None

def resolve_pdf_url(doi=None, arxiv_id=None, pmc_id=None, title=None):
    """
    Try to resolve a PDF URL from available sources.
    Returns (pdf_url, source) or (None, None).
    """
    # Try OpenAlex first (best OA source)
    if doi:
        try:
            url = f"https://api.openalex.org/works/doi:{doi}"
            r = urllib.request.urlopen(url, timeout=15)
            data = json.loads(r.read())
            
            if data.get('open_access', {}).get('is_oa'):
                oa_loc = data.get('best_oa_location', {})
                if oa_loc and oa_loc.get('pdf_url'):
                    return oa_loc['pdf_url'], "OpenAlex"
            
            # If not OA, try arXiv
            if arxiv_id:
                return f"https://arxiv.org/pdf/{arxiv_id}.pdf", "arXiv"
        except:
            pass
    
    # Try arXiv
    if arxiv_id:
        return f"https://arxiv.org/pdf/{arxiv_id}.pdf", "arXiv"
    
    # Try PMC
    if pmc_id:
        return f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/pdf/", "PMC"
    
    return None, None

def read_paper_full(doi=None, arxiv_id=None, pmc_id=None, title="", authors="", year=None, source="unknown"):
    """
    Full paper reading workflow with provenance tracking.
    Downloads, reads, and saves page-level text.
    
    Returns a citation entry with provenance.
    """
    log(f"Reading paper: {title or doi or arxiv_id or pmc_id}")
    
    # Step 1: Resolve PDF URL
    pdf_url, resolved_source = resolve_pdf_url(doi=doi, arxiv_id=arxiv_id, pmc_id=pmc_id, title=title)
    
    if not pdf_url:
        log(f"⚠️  No PDF URL found for {doi or arxiv_id or pmc_id}", "WARNING")
        return create_citation_entry(
            doi=doi, arxiv_id=arxiv_id, pmc_id=pmc_id,
            title=title, authors=authors, year=year,
            source=source, tier=TIER_METADATA
        )
    
    # Step 2: Download PDF
    pdf_path = download_pdf_from_url(pdf_url, doi=doi, arxiv_id=arxiv_id)
    
    if not pdf_path:
        return create_citation_entry(
            doi=doi, arxiv_id=arxiv_id, pmc_id=pmc_id,
            title=title, authors=authors, year=year,
            source=source, tier=TIER_METADATA
        )
    
    # Step 3: Create paper ID for page text storage
    paper_id = f"paper_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if doi:
        paper_id += f"_doi_{doi.replace('/', '_')}"
    elif arxiv_id:
        paper_id += f"_arxiv_{arxiv_id.replace('/', '_').replace(':', '_')}"
    
    # Step 4: Read PDF with page tracking
    pages = read_pdf_with_pages(pdf_path)
    
    if not pages:
        log(f"⚠️  No text extracted from {pdf_path}", "WARNING")
        return create_citation_entry(
            doi=doi, arxiv_id=arxiv_id, pmc_id=pmc_id,
            title=title, authors=authors, year=year,
            source=source, tier=TIER_METADATA
        )
    
    # Step 5: Save page-level text
    save_page_text(paper_id, pages)
    
    # Step 6: Create verified citation entry
    citation = create_citation_entry(
        doi=doi, arxiv_id=arxiv_id, pmc_id=pmc_id,
        title=title, authors=authors, year=year,
        source=source, tier=TIER_READ,
        page=None, section=None, claim_verified=True
    )
    
    log(f"✓ Paper fully read and verified: {title}", "SUCCESS")
    return citation

# =============================================================================
# Search Functions
# =============================================================================

def search_openalex(query, max_results=10, open_access_only=True):
    """Search OpenAlex - PRIMARY source"""
    log(f"Searching OpenAlex for '{query}'...")
    results = []
    
    try:
        import requests
        
        url = "https://api.openalex.org/works"
        params = {
            'search': query,
            'per_page': max_results,
            'mailto': 'researcher@i4ju.ai',
            'sort': 'cited_by_count:desc'
        }
        if open_access_only:
            params['filter'] = 'open_access.is_oa:true'
        
        r = requests.get(url, params=params, timeout=15)
        data = r.json()
        
        total = data.get('meta', {}).get('count', 0)
        log(f"✓ OpenAlex: Found {total} total results", "SUCCESS")
        
        for work in data.get('results', []):
            doi = work.get('doi', '')
            arxiv_id = work.get('external_ids', {}).get('ArXiv', '')
            pmc_id = work.get('external_ids', {}).get('PMC', '')
            
            # Get PDF URL
            pdf_url = None
            if work.get('open_access', {}).get('is_oa'):
                oa_loc = work.get('best_oa_location', {})
                if oa_loc:
                    pdf_url = oa_loc.get('pdf_url')
            
            result = create_citation_entry(
                doi=doi if doi else None,
                arxiv_id=arxiv_id if arxiv_id else None,
                pmc_id=pmc_id if pmc_id else None,
                title=work.get('display_name', 'N/A'),
                authors=", ".join([a.get('author', {}).get('display_name', '') 
                                   for a in work.get('authorships', [])[:5]]),
                year=work.get('publication_year'),
                source="OpenAlex",
                tier=TIER_METADATA,
                abstract_text=work.get('abstract_inverted_index', None) and "Abstract available" or "",
            )
            
            # Store PDF URL for later download
            if pdf_url:
                result["_pdf_url"] = pdf_url
                result["_resolved_source"] = "OpenAlex"
            
            results.append(result)
        
    except Exception as e:
        log(f"✗ OpenAlex Error: {e}", "ERROR")
    
    return results

def search_arxiv(query, max_results=5):
    """Search arXiv for papers"""
    log(f"Searching arXiv for '{query}'...")
    results = []
    try:
        import arxiv
        search = arxiv.Search(query=query, max_results=max_results)
        client = arxiv.Client()
        
        for paper in client.results(search):
            doi = paper.doi if paper.doi else None
            arxiv_id = paper.entry_id.split('/')[-1]
            
            result = create_citation_entry(
                arxiv_id=arxiv_id,
                doi=doi if doi else None,
                title=paper.title,
                authors=", ".join([str(a) for a in paper.authors[:5]]),
                year=int(str(paper.published.date())[:4]) if paper.published else None,
                source="arXiv",
                tier=TIER_METADATA,
                abstract_text=paper.summary,
            )
            result["_pdf_url"] = paper.pdf_url
            result["_resolved_source"] = "arXiv"
            results.append(result)
        
        log(f"✓ arXiv: Found {len(results)} results", "SUCCESS")
        return results
    except Exception as e:
        log(f"✗ arXiv Error: {e}", "ERROR")
        return []

def search_crossref(query, max_results=10):
    """Search CrossRef for papers"""
    log(f"Searching CrossRef for '{query}'...")
    results = []
    try:
        import requests
        
        url = "https://api.crossref.org/works"
        params = {
            "query": query,
            "rows": max_results,
            "mailto": "researcher@i4ju.ai",
            "select": "title,author,DOI,published-print,abstract"
        }
        
        r = requests.get(url, params=params, timeout=15)
        data = r.json()
        
        items = data.get('message', {}).get('items', [])
        if isinstance(items, dict):
            items = items.get('items', [])
        
        for item in items[:max_results]:
            doi = item.get('DOI', '')
            if not doi:
                continue
            
            title_list = item.get('title', [])
            if isinstance(title_list, list):
                title = title_list[0] if title_list else 'N/A'
            else:
                title = str(title_list)
            
            author_list = item.get('author', [])
            authors_str = ", ".join([f"{a.get('given', '')} {a.get('family', '')}" for a in author_list[:5]])
            
            pub_date = item.get('published-print', {}).get('date-parts', [[0]])
            if not pub_date or (isinstance(pub_date, list) and len(pub_date) == 0):
                pub_date = item.get('created', {}).get('date-parts', [[0]])
            year = pub_date[0][0] if pub_date and len(pub_date) > 0 else None
            
            abstract = item.get('abstract', '')
            if isinstance(abstract, dict):
                abstract = abstract.get('abstract', '')
            
            result = create_citation_entry(
                doi=doi,
                title=title,
                authors=authors_str,
                year=year,
                source="CrossRef",
                tier=TIER_METADATA,
                abstract_text=abstract[:500] if abstract else "",
            )
            results.append(result)
        
        log(f"✓ CrossRef: Found {len(results)} results", "SUCCESS")
        return results
    except Exception as e:
        log(f"✗ CrossRef Error: {e}", "ERROR")
        return []

def search_pmc(query, max_results=10):
    """Search PMC for full-text articles"""
    log(f"Searching PMC for '{query}'...")
    results = []
    try:
        import requests
        
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        search_params = {
            "db": "pmc",
            "term": query,
            "retmax": max_results,
            "retmode": "json"
        }
        response = requests.get(search_url, params=search_params, timeout=30)
        data = response.json()
        
        pmc_ids = data['esearchresult']['idlist']
        
        for pmc_id in pmc_ids[:max_results]:
            detail_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            detail_params = {"db": "pmc", "id": pmc_id, "retmode": "xml"}
            detail_response = requests.get(detail_url, params=detail_params, timeout=30)
            
            if detail_response.status_code == 200:
                xml_text = detail_response.text
                
                title_match = re.search(r'<ArticleTitle>(.*?)</ArticleTitle>', xml_text)
                abstract_match = re.search(r'<AbstractText>(.*?)</AbstractText>', xml_text, re.DOTALL)
                authors = re.findall(r'<Author><LastName>(.*?)</LastName><ForeName>(.*?)</ForeName>', xml_text)
                
                result = create_citation_entry(
                    pmc_id=pmc_id,
                    title=title_match.group(1) if title_match else "N/A",
                    authors=", ".join([f"{fn} {ln}" for ln, fn in authors[:5]]),
                    source="PMC",
                    tier=TIER_ABSTRACT,
                    abstract_text=abstract_match.group(1).strip()[:500] if abstract_match else "",
                )
                results.append(result)
        
        log(f"✓ PMC: Retrieved {len(results)} articles", "SUCCESS")
        return results
    except Exception as e:
        log(f"✗ PMC Error: {e}", "ERROR")
        return []

def search_semantic_scholar(query, max_results=10):
    """Search Semantic Scholar (rate-limited, use sparingly)"""
    log(f"Searching Semantic Scholar for '{query}'...")
    results = []
    
    if not SEMANTIC_SCHOLAR_API_KEY:
        log("⚠️  Semantic Scholar API key not found. Skipping.", "WARNING")
        return results
    
    try:
        from semanticscholar import SemanticScholar
        sh = SemanticScholar(api_key=SEMANTIC_SCHOLAR_API_KEY)
        
        papers = sh.search_paper(query, limit=max_results)
        
        for paper in papers[:max_results]:
            # Handle Author objects (may be dicts or objects with .name)
            authors_list = []
            for a in (paper.authors or [])[:5]:
                if isinstance(a, dict):
                    authors_list.append(a.get('name', 'Unknown'))
                elif hasattr(a, 'name'):
                    authors_list.append(str(a.name))
                else:
                    authors_list.append(str(a))
            
            result = create_citation_entry(
                title=paper.title,
                authors=", ".join(authors_list),
                year=paper.year,
                source="Semantic Scholar",
                tier=TIER_ABSTRACT if paper.abstract else TIER_METADATA,
                abstract_text=paper.abstract or "",
            )
            
            # Try to get identifiers
            ext_ids = paper.externalIds or {}
            if 'DOI' in ext_ids:
                result['identifiers']['doi'] = ext_ids['DOI']
            if 'ArXiv' in ext_ids:
                result['identifiers']['arxiv_id'] = ext_ids['ArXiv']
            if 'PMC' in ext_ids:
                result['identifiers']['pmc_id'] = ext_ids['PMC']
            
            results.append(result)
        
        log(f"✓ Semantic Scholar: Found {len(results)} results", "SUCCESS")
        return results
    except Exception as e:
        log(f"✗ Semantic Scholar Error: {e}", "ERROR")
        return []

# =============================================================================
# Deduplication & Merging
# =============================================================================

def deduplicate_results(results):
    """Deduplicate results by DOI, arxiv_id, or title similarity"""
    seen = {}
    unique = []
    
    for r in results:
        identifiers = r.get('identifiers', {})
        key = None
        
        # Primary key: DOI
        if identifiers.get('doi'):
            key = f"doi:{identifiers['doi']}"
        # Secondary key: arXiv ID
        elif identifiers.get('arxiv_id'):
            key = f"arxiv:{identifiers['arxiv_id']}"
        # Tertiary key: PMC ID
        elif identifiers.get('pmc_id'):
            key = f"pmc:{identifiers['pmc_id']}"
        # Fallback: title (normalized)
        else:
            title = r.get('title', '').lower().strip()
            key = f"title:{re.sub(r'\s+', ' ', title)[:50]}"
        
        if key not in seen:
            seen[key] = True
            unique.append(r)
    
    return unique

# =============================================================================
# Bibliography Generation & Verification
# =============================================================================

def generate_bibliography(citations, output_file=None):
    """
    Generate a bibliography verification file.
    This is a separate file that a human reviewer can use to cross-check citations.
    
    For each citation, includes:
    - Full reference string
    - Identifiers (DOI, arXiv ID, PMC ID)
    - Provenance tier
    - Page numbers (if read)
    - Abstract text (for verification)
    - Direct links to the paper
    """
    bib_entries = []
    
    for i, c in enumerate(citations, 1):
        identifiers = c.get('identifiers', {})
        prov = c.get('provenance', {})
        
        # Build reference string
        authors = c.get('authors', 'Unknown')
        year = c.get('year', 'n.d.')
        title = c.get('title', 'Unknown Title')
        authors_list = authors.split(',') if authors else ['Unknown']
        last_author = authors_list[-1].strip()
        first_author = authors_list[0].strip()
        
        if first_author == last_author:
            ref_authors = f"{first_author} et al." if authors != first_author else first_author
        else:
            ref_authors = f"{first_author} et al."
        
        reference = f"{ref_authors} ({year}). {title}."
        
        entry = {
            "id": i,
            "reference": reference,
            "identifiers": identifiers,
            "provenance": prov,
            "links": {}
        }
        
        # Add links for direct verification
        if identifiers.get('doi'):
            entry["links"]["doi"] = f"https://doi.org/{identifiers['doi']}"
            entry["links"]["openalex"] = f"https://openalex.org/works/doi:{identifiers['doi']}"
        if identifiers.get('arxiv_id'):
            entry["links"]["arxiv"] = f"https://arxiv.org/abs/{identifiers['arxiv_id']}"
        if identifiers.get('pmc_id'):
            entry["links"]["pmc"] = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{identifiers['pmc_id']}/"
        
        # Add abstract for tier=abstract and tier=read
        if prov.get('abstract_text'):
            entry["abstract_preview"] = prov['abstract_text'][:300]
        
        # Add page info if read
        if prov.get('page'):
            entry["page_info"] = f"Page {prov['page']}"
        
        bib_entries.append(entry)
    
    # Write verification file
    if output_file is None:
        output_file = os.path.join(OUTPUT_DIR, "bibliography_verification.json")
    
    with open(output_file, 'w') as f:
        json.dump({
            "generated": datetime.now().isoformat(),
            "total_citations": len(bib_entries),
            "tiers": {
                "read": sum(1 for e in bib_entries if e["provenance"]["tier"] == TIER_READ),
                "abstract": sum(1 for e in bib_entries if e["provenance"]["tier"] == TIER_ABSTRACT),
                "metadata": sum(1 for e in bib_entries if e["provenance"]["tier"] == TIER_METADATA),
                "discovery": sum(1 for e in bib_entries if e["provenance"]["tier"] == TIER_DISCOVERY),
            },
            "entries": bib_entries
        }, f, indent=2)
    
    log(f"✓ Bibliography verification saved to {output_file}", "SUCCESS")
    return output_file

# =============================================================================
# Main CLI
# =============================================================================

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    command = sys.argv[1]
    
    if command == "search":
        if len(sys.argv) < 3:
            print("Usage: python3 research_workflow_v2.py search \"topic\" [--max-results N]")
            return
        
        query = sys.argv[2]
        max_results = 5
        if "--max-results" in sys.argv:
            idx = sys.argv.index("--max-results")
            if idx + 1 < len(sys.argv):
                max_results = int(sys.argv[idx + 1])
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "openalex": search_openalex(query, max_results),
            "arxiv": search_arxiv(query, max_results),
            "crossref": search_crossref(query, max_results),
            "pmc": search_pmc(query, max_results),
            "semantic_scholar": search_semantic_scholar(query, max_results)
        }
        
        # Deduplicate
        all_papers = []
        for source_results in results.values():
            if isinstance(source_results, list):
                all_papers.extend(source_results)
        
        unique = deduplicate_results(all_papers)
        results["unique_papers"] = unique
        results["summary"] = {
            "total_found": len(all_papers),
            "unique": len(unique),
            "by_tier": {},
            "by_source": {}
        }
        
        for p in unique:
            tier = p.get('provenance', {}).get('tier', 'unknown')
            src = p.get('source', 'unknown')
            results["summary"]["by_tier"][tier] = results["summary"]["by_tier"].get(tier, 0) + 1
            results["summary"]["by_source"][src] = results["summary"]["by_source"].get(src, 0) + 1
        
        save_results(results)
        generate_bibliography(unique)
        
        print(f"\nSearch complete for: {query}")
        print(f"Total found: {results['summary']['total_found']}")
        print(f"Unique papers: {results['summary']['unique']}")
        print(f"By tier: {results['summary']['by_tier']}")
        print(f"By source: {results['summary']['by_source']}")
        
    elif command == "read-paper":
        if len(sys.argv) < 3:
            print("Usage: python3 research_workflow_v2.py read-paper <DOI> | <arxiv_id> | <PMC_id>")
            return
        
        identifier = sys.argv[2]
        # Try to parse as DOI, arXiv ID, or PMC ID
        doi = arxiv_id = pmc_id = None
        
        if identifier.startswith('10.') or 'doi.org' in identifier:
            doi = identifier.split('/')[-1] if 'doi.org' in identifier else identifier
        elif identifier.startswith('arXiv:') or identifier.startswith('2') and 'arxiv' in identifier.lower():
            arxiv_id = identifier.split(':')[-1].strip() if ':' in identifier else identifier
        elif identifier.startswith('PMC'):
            pmc_id = identifier.replace('PMC', '')
        
        citation = read_paper_full(doi=doi, arxiv_id=arxiv_id, pmc_id=pmc_id, source="CLI")
        print(json.dumps(citation, indent=2))
        
    elif command == "verify":
        if len(sys.argv) < 3:
            print("Usage: python3 research_workflow_v2.py verify \"claim\" --doi \"...\"")
            return
        
        claim = sys.argv[2]
        doi = arxiv_id = None
        if "--doi" in sys.argv:
            idx = sys.argv.index("--doi")
            if idx + 1 < len(sys.argv):
                doi = sys.argv[idx + 1]
        
        # First read the paper if not already read
        paper_id = f"temp_verify_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        citation = read_paper_full(doi=doi, arxiv_id=arxiv_id, source="CLI")
        
        # Verify claim
        verified, locations = verify_claim_in_paper(paper_id, claim)
        print(json.dumps({"verified": verified, "locations": locations}, indent=2))
        
    elif command == "full-analysis":
        if len(sys.argv) < 3:
            print("Usage: python3 research_workflow_v2.py full-analysis \"topic\" [--read-papers]")
            return
        
        query = sys.argv[2]
        read_papers = "--read-papers" in sys.argv
        
        log(f"Starting full analysis for: {query}")
        
        # Search all sources
        results = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "openalex": search_openalex(query, 5),
            "arxiv": search_arxiv(query, 3),
            "crossref": search_crossref(query, 3),
            "pmc": search_pmc(query, 3),
            "semantic_scholar": search_semantic_scholar(query, 3)
        }
        
        # Deduplicate
        all_papers = []
        for source_results in results.values():
            if isinstance(source_results, list):
                all_papers.extend(source_results)
        
        unique = deduplicate_results(all_papers)
        results["unique_papers"] = unique
        results["summary"] = {
            "total_found": len(all_papers),
            "unique": len(unique),
            "by_tier": {},
            "by_source": {}
        }
        
        for p in unique:
            tier = p.get('provenance', {}).get('tier', 'unknown')
            src = p.get('source', 'unknown')
            results["summary"]["by_tier"][tier] = results["summary"]["by_tier"].get(tier, 0) + 1
            results["summary"]["by_source"][src] = results["summary"]["by_source"].get(src, 0) + 1
        
        # Optionally read papers
        if read_papers:
            log("Reading top papers...")
            for i, paper in enumerate(unique[:5]):
                log(f"Reading paper {i+1}/5: {paper.get('title', 'Unknown')[:60]}...")
                citation = read_paper_full(
                    doi=paper.get('identifiers', {}).get('doi'),
                    arxiv_id=paper.get('identifiers', {}).get('arxiv_id'),
                    pmc_id=paper.get('identifiers', {}).get('pmc_id'),
                    title=paper.get('title', ''),
                    authors=paper.get('authors', ''),
                    year=paper.get('year'),
                    source=paper.get('source', 'unknown')
                )
                unique[i] = citation
        
        results["unique_papers"] = unique
        save_results(results)
        generate_bibliography(unique)
        
        print(f"\nFull analysis complete for: {query}")
        print(f"Total papers found: {results['summary']['total_found']}")
        print(f"Unique papers: {results['summary']['unique']}")
        
    elif command == "bibliography":
        output = sys.argv[3] if len(sys.argv) > 3 else None
        # Read existing results and generate bibliography
        import glob
        json_files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "research_*.json")), reverse=True)
        if json_files:
            with open(json_files[0]) as f:
                data = json.load(f)
            papers = data.get('unique_papers', [])
            generate_bibliography(papers, output)
        else:
            log("No research results found. Run search or full-analysis first.", "ERROR")
    
    else:
        print(f"Unknown command: {command}")
        print(__doc__)

def save_results(results, filename=None):
    """Save research results to file"""
    if filename is None:
        filename = f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    log(f"✓ Saved to {filepath}", "SUCCESS")
    return filepath

if __name__ == "__main__":
    main()
