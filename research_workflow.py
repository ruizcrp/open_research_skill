#!/usr/bin/env python3
"""
open_research - Research Workflow
Comprehensive research assistant for finding, downloading, and analyzing papers.

Tools:
- arXiv API (free, no key)
- CrossRef API (free, no key)
- PMC/NCBI E-utilities (free, no key)
- Semantic Scholar API (rate-limited, needs API key for higher limits)
- OpenAlex API (free, no key, primary source)
- PyMuPDF for PDF reading

Usage:
    python3 research_workflow.py search "topic" [--max-results N]
    python3 research_workflow.py download DOI_or_arxiv_id
    python3 research_workflow.py read paper.pdf
    python3 research_workflow.py pmc-search "topic" [--max-results N]
    python3 research_workflow.py full-analysis "topic"
"""

import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

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

def retry_with_backoff(func, max_retries=3, base_delay=10):
    """Retry a function with exponential backoff for rate limiting"""
    for attempt in range(max_retries):
        try:
            result = func()
            if result is not None:
                return result
        except Exception as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                log(f"  Retry {attempt + 1}/{max_retries} after {delay}s...", "WARNING")
                time.sleep(delay)
            else:
                raise
    return None

# Configuration
OUTPUT_DIR = "/home/clawdbot/.openclaw/workspace-ross/research"
MEMORY_DIR = "/home/clawdbot/.openclaw/workspace-ross/memory"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(MEMORY_DIR, exist_ok=True)

def log(message, level="INFO"):
    """Print with timestamp and level"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] [{level}] {message}")

# =============================================================================
# CITATION VERIFICATION (CRITICAL - prevents hallucinated references)
# =============================================================================

def verify_openalex(doi=None, arxiv_id=None, title=None, authors=None, year=None):
    """
    Verify a citation exists in OpenAlex (100% open access, no paywalls).
    Returns verified metadata dict or None if not found.
    """
    log("Verifying via OpenAlex...", "INFO")
    try:
        import requests
        params = {'mailto': 'christian.ruiz@z01.ch', 'per_page': 1}

        if doi:
            params['select'] = 'title,authorships,publication_year,cited_by_count,open_access'
            url = f"https://api.openalex.org/works/doi:{doi}"
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 200:
                data = r.json()
                actual_title = data.get('title', '')
                actual_authors = [a.get('author', {}).get('display_name', '')
                                 for a in data.get('authorships', [])[:5]]
                actual_year = data.get('publication_year')

                # CRITICAL: Compare actual metadata against claimed metadata
                if title or authors or year:
                    match, score, details = compare_metadata(
                        actual_title, title or "",
                        actual_authors, authors or [],
                        actual_year, year
                    )
                    if not match:
                        log(f"✗ DOI {doi} resolves to DIFFERENT paper!", "ERROR")
                        log(f"   Claimed: '{title}' by {authors} ({year})", "INFO")
                        log(f"   Actual:  '{actual_title}' by {actual_authors} ({actual_year})", "INFO")
                        log(f"   Match score: {score:.2f} ({details})", "INFO")
                        return None

                log(f"✓ OpenAlex verified: {actual_title}", "SUCCESS")
                return {
                    "source": "openalex",
                    "verified": True,
                    "title": actual_title,
                    "doi": doi,
                    "authors": actual_authors,
                    "year": actual_year,
                    "citations": data.get('cited_by_count', 0),
                    "open_access": data.get('open_access', {}).get('is_oa', False),
                    "match_score": score if title or authors or year else 1.0
                }
            elif r.status_code == 404:
                log("✗ OpenAlex: DOI not found", "WARNING")
                return None
            else:
                log(f"✗ OpenAlex error: {r.status_code}", "ERROR")
                return None

        if title:
            encoded_title = quote_plus(title)
            url = f"https://api.openalex.org/works?search={encoded_title}"
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 200:
                data = r.json()
                results = data.get('results', [])
                if results:
                    best = results[0]
                    actual_title = best.get('title', '')

                    # Safely extract authors
                    actual_authors = []
                    for a in best.get('authorships', [])[:5]:
                        author_info = a.get('author', {})
                        if author_info:
                            actual_authors.append(author_info.get('display_name', ''))

                    actual_year = best.get('publication_year')

                    # CRITICAL: Compare actual metadata against claimed metadata
                    if authors or year:
                        match, score, details = compare_metadata(
                            actual_title, title or "",
                            actual_authors, authors or [],
                            actual_year, year
                        )
                        if not match:
                            log(f"✗ OpenAlex title search found DIFFERENT paper!", "ERROR")
                            log(f"   Claimed: '{title}' by {authors} ({year})", "INFO")
                            log(f"   Actual:  '{actual_title}' by {actual_authors} ({actual_year})", "INFO")
                            log(f"   Match score: {score:.2f} ({details})", "INFO")
                            return None

                    log(f"✓ OpenAlex verified: {actual_title}", "SUCCESS")
                    primary_loc = best.get('primary_location') or {}
                    source = primary_loc.get('source') or {}
                    return {
                        "source": "openalex",
                        "verified": True,
                        "title": actual_title,
                        "doi": best.get('doi'),
                        "arxiv_id": source.get('issn_l'),
                        "authors": actual_authors,
                        "year": actual_year,
                        "citations": best.get('cited_by_count', 0),
                        "open_access": best.get('open_access', {}).get('is_oa', False),
                        "match_score": score if authors or year else 1.0
                    }
                else:
                    log("✗ OpenAlex: No results for title", "WARNING")
                    return None

    except Exception as e:
        log(f"✗ OpenAlex verification error: {e}", "ERROR")
        return None

    return None


def normalize_string(s):
    """Normalize a string for comparison: lowercase, strip, collapse whitespace."""
    if not s:
        return ""
    s = s.lower().strip()
    s = re.sub(r'[^\w\s]', '', s)  # Remove punctuation
    s = re.sub(r'\s+', ' ', s)  # Collapse whitespace
    return s


def compare_metadata(actual_title, claimed_title, actual_authors, claimed_authors, actual_year, claimed_year, tolerance=0.3):
    """
    Compare actual paper metadata against claimed metadata.
    Returns (match: bool, score: float, details: str).

    This is the CRITICAL check that prevents hallucinated citations.
    A hallucinated citation has a real arXiv ID/DOI that resolves to a DIFFERENT paper.
    """
    if not actual_title or not claimed_title:
        return False, 0.0, "Missing title"

    # Title comparison (most important)
    norm_actual = normalize_string(actual_title)
    norm_claimed = normalize_string(claimed_title)

    # Exact match
    if norm_actual == norm_claimed:
        title_score = 1.0
    else:
        # Check if claimed title is a substring of actual (or vice versa)
        if norm_claimed in norm_actual or norm_actual in norm_claimed:
            title_score = 0.8
        else:
            # Use ratio-based similarity
            from difflib import SequenceMatcher
            title_score = SequenceMatcher(None, norm_actual, norm_claimed).ratio()

    # Author comparison
    author_score = 0.0
    if actual_authors and claimed_authors:
        norm_actual_authors = [normalize_string(a) for a in actual_authors[:3]]
        norm_claimed_authors = [normalize_string(a) for a in claimed_authors[:3]]

        # Check for at least one matching author
        matches = sum(1 for ca in norm_claimed_authors if any(ca in aa for aa in norm_actual_authors))
        author_score = min(matches / max(len(norm_claimed_authors), 1), 1.0)

    # Year comparison
    year_score = 0.0
    if actual_year and claimed_year:
        try:
            year_diff = abs(int(actual_year) - int(claimed_year))
            year_score = max(0, 1.0 - (year_diff * 0.25))  # 1 point diff = 0.75, 4+ = 0
        except (ValueError, TypeError):
            pass

    # Weighted composite score
    composite = (title_score * 0.6) + (author_score * 0.3) + (year_score * 0.1)

    # Determine match
    match = composite >= (1.0 - tolerance)

    details = f"title={title_score:.2f}, authors={author_score:.2f}, year={year_score:.2f}, composite={composite:.2f}"

    if not match:
        details += f" | ACTUAL: '{actual_title}'" if title_score < 0.5 else ""

    return match, composite, details


def verify_arxiv(arxiv_id, claimed_title=None, claimed_authors=None, claimed_year=None):
    """
    Verify an arXiv paper exists via arXiv API AND matches claimed metadata.
    Returns verified metadata dict with match info, or None if mismatch.
    """
    log("Verifying via arXiv API...", "INFO")
    try:
        import arxiv
        # Clean arXiv ID (remove https://arxiv.org/abs/ prefix if present)
        clean_id = re.sub(r'https?://arxiv\.org/abs/', '', arxiv_id)
        clean_id = clean_id.replace('arxiv.', '').replace('v', '')

        search = arxiv.Search(id_list=[clean_id], max_results=1)
        client = arxiv.Client()

        for paper in client.results(search):
            actual_title = paper.title
            actual_authors = [str(a) for a in paper.authors[:5]]
            actual_year = paper.published.year if paper.published else None

            # CRITICAL: Compare actual metadata against claimed metadata
            if claimed_title or claimed_authors or claimed_year:
                match, score, details = compare_metadata(
                    actual_title, claimed_title or "",
                    actual_authors, claimed_authors or [],
                    actual_year, claimed_year
                )
                if not match:
                    log(f"✗ arXiv ID {clean_id} resolves to DIFFERENT paper!", "ERROR")
                    log(f"   Claimed: '{claimed_title}' by {claimed_authors} ({claimed_year})", "INFO")
                    log(f"   Actual:  '{actual_title}' by {actual_authors} ({actual_year})", "INFO")
                    log(f"   Match score: {score:.2f} ({details})", "INFO")
                    return None

            log(f"✓ arXiv verified: {actual_title}", "SUCCESS")
            return {
                "source": "arxiv",
                "verified": True,
                "title": actual_title,
                "arxiv_id": paper.entry_id,
                "authors": actual_authors,
                "year": actual_year,
                "doi": paper.doi if paper.doi else None,
                "match_score": score if claimed_title or claimed_authors or claimed_year else 1.0
            }

        log("✗ arXiv: Paper not found", "WARNING")
        return None
    except Exception as e:
        log(f"✗ arXiv verification error: {e}", "ERROR")
        return None


def verify_crossref(doi, claimed_title=None, claimed_authors=None, claimed_year=None):
    """
    Verify a DOI via CrossRef API AND match claimed metadata.
    Returns verified metadata dict or None if mismatch.
    """
    log("Verifying via CrossRef...", "INFO")
    try:
        import requests
        url = f"https://api.crossref.org/works/{doi}"
        r = requests.get(url, timeout=15)

        if r.status_code == 200:
            data = r.json()
            msg = data.get('message', {})
            actual_title = msg.get('title', ['Unknown'])[0]
            actual_authors = [f"{a.get('given', '')} {a.get('family', '')}".strip()
                             for a in msg.get('author', [])[:5]]
            actual_year = (msg.get('published-print', {}).get('date-parts', [[None]])[0][0] or
                           msg.get('published-online', {}).get('date-parts', [[None]])[0][0])

            # CRITICAL: Compare actual metadata against claimed metadata
            if claimed_title or claimed_authors or claimed_year:
                match, score, details = compare_metadata(
                    actual_title, claimed_title or "",
                    actual_authors, claimed_authors or [],
                    actual_year, claimed_year
                )
                if not match:
                    log(f"✗ DOI {doi} resolves to DIFFERENT paper!", "ERROR")
                    log(f"   Claimed: '{claimed_title}' by {claimed_authors} ({claimed_year})", "INFO")
                    log(f"   Actual:  '{actual_title}' by {actual_authors} ({actual_year})", "INFO")
                    log(f"   Match score: {score:.2f} ({details})", "INFO")
                    return None

            log(f"✓ CrossRef verified: {actual_title}", "SUCCESS")
            return {
                "source": "crossref",
                "verified": True,
                "title": actual_title,
                "doi": doi,
                "authors": actual_authors,
                "year": actual_year,
                "journal": msg.get('container-title', ['Unknown'])[0],
                "match_score": score if claimed_title or claimed_authors or claimed_year else 1.0
            }
        elif r.status_code == 404:
            log(f"✗ CrossRef: DOI {doi} not found", "WARNING")
            return None
        else:
            log(f"✗ CrossRef error: {r.status_code}", "ERROR")
            return None
    except Exception as e:
        log(f"✗ CrossRef verification error: {e}", "ERROR")
        return None


def verify_citation(doi=None, arxiv_id=None, title=None, authors=None, year=None):
    """
    MASTER VERIFICATION FUNCTION - verifies a citation through multiple sources.
    MUST be called before adding ANY citation to the bibliography.
    CRITICAL: Compares actual paper metadata against claimed metadata.
    Returns verified dict or None if citation is not found or metadata mismatch.
    """
    log("=" * 60)
    log("CITATION VERIFICATION STARTED", "INFO")
    log(f"  DOI: {doi}, arXiv: {arxiv_id}", "INFO")
    log(f"  Claimed: '{title}' by {authors} ({year})", "INFO")
    log("=" * 60)

    # Strategy 1: Verify by DOI (most reliable)
    if doi:
        result = verify_openalex(doi=doi, title=title, authors=authors, year=year)
        if result:
            return result
        result = verify_crossref(doi, claimed_title=title, claimed_authors=authors, claimed_year=year)
        if result:
            return result

    # Strategy 2: Verify by arXiv ID
    if arxiv_id:
        result = verify_arxiv(arxiv_id, claimed_title=title, claimed_authors=authors, claimed_year=year)
        if result:
            return result

    # Strategy 3: Verify by title (least reliable, but better than nothing)
    if title:
        result = verify_openalex(title=title, authors=authors, year=year)
        if result:
            return result

    # If we get here, verification failed
    log("=" * 60)
    log("CITATION VERIFICATION FAILED - Paper not found in any database", "ERROR")
    log("=" * 60)
    return None


def build_verified_bibliography(citations):
    """
    Build a bibliography by verifying each citation.
    Only verified citations are included.
    Unverified citations are logged and excluded.

    Args:
        citations: List of dicts with keys: doi, arxiv_id, title, authors, year

    Returns:
        Tuple of (verified_entries, unverified_entries)
    """
    verified = []
    unverified = []

    for i, citation in enumerate(citations, 1):
        log(f"\nVerifying citation {i}/{len(citations)}: {citation.get('title', 'Unknown')}")

        result = verify_citation(
            doi=citation.get('doi'),
            arxiv_id=citation.get('arxiv_id'),
            title=citation.get('title'),
            authors=citation.get('authors'),
            year=citation.get('year')
        )

        if result:
            result['original'] = citation
            verified.append(result)
            log(f"✓ Citation {i} VERIFIED", "SUCCESS")
        else:
            unverified.append(citation)
            log(f"✗ Citation {i} REJECTED - not found in any database", "ERROR")

    log(f"\n{'=' * 60}")
    log(f"VERIFICATION COMPLETE: {len(verified)} verified, {len(unverified)} rejected", "INFO")
    log(f"{'=' * 60}\n")

    return verified, unverified

def save_to_memory(title, content):
    """Save research notes to memory directory"""
    date_str = datetime.now().strftime('%Y-%m-%d')
    memory_file = os.path.join(MEMORY_DIR, f"{date_str}-research.md")
    
    with open(memory_file, 'a') as f:
        f.write(f"\n## {title}\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(content + "\n")
    
    log(f"Saved to {memory_file}")

def search_arxiv(query, max_results=5):
    """Search arXiv for papers"""
    log(f"Searching arXiv for '{query}'...")
    results = []
    try:
        import arxiv
        search = arxiv.Search(query=query, max_results=max_results)
        client = arxiv.Client()
        
        for i, paper in enumerate(client.results(search)):
            results.append({
                "title": paper.title,
                "published": str(paper.published.date()),
                "authors": [str(a) for a in paper.authors[:5]],
                "summary": paper.summary,
                "pdf_url": paper.pdf_url,
                "arxiv_id": paper.entry_id,
                "doi": paper.doi if paper.doi else None
            })
            if i >= max_results - 1:
                break
        
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
        import crossref
        cr = crossref.CrossRefAPIClient()
        response = cr.get_works(params={"query": query})
        data = response.json()
        
        items = data.get('message', {}).get('items', [])
        for item in items[:max_results]:
            results.append({
                "title": item.get('title', ['N/A'])[0],
                "doi": item.get('DOI', 'N/A'),
                "published": item.get('published-print', {}).get('date-parts', [[0]])[0][0],
                "authors": [author.get('given', '') + ' ' + author.get('family', '') 
                           for author in item.get('author', [])[:5]],
                "citation_count": item.get('is-referenced-by-count', 0),
                "journal": item.get('container-title', ['N/A'])[0] if item.get('container-title') else 'N/A'
            })
        
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
        
        # Search
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
        total_count = data['esearchresult']['count']
        
        log(f"✓ PMC: Found {total_count} total articles", "SUCCESS")
        
        # Get details for each article
        for pmc_id in pmc_ids[:max_results]:
            # Get article details
            detail_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            detail_params = {
                "db": "pmc",
                "id": pmc_id,
                "retmode": "xml",
                "rettype": "xml"
            }
            detail_response = requests.get(detail_url, params=detail_params, timeout=30)
            
            if detail_response.status_code == 200:
                # Parse XML to extract title and abstract
                xml_text = detail_response.text
                
                # Extract title
                title_match = re.search(r'<ArticleTitle>(.*?)</ArticleTitle>', xml_text)
                title = title_match.group(1) if title_match else "N/A"
                
                # Extract abstract
                abstract_match = re.search(r'<AbstractText>(.*?)</AbstractText>', xml_text, re.DOTALL)
                abstract = abstract_match.group(1).strip() if abstract_match else "N/A"
                
                # Extract authors
                authors = re.findall(r'<Author><LastName>(.*?)</LastName><ForeName>(.*?)</ForeName>', xml_text)
                authors_str = ", ".join([f"{fn} {ln}" for ln, fn in authors[:5]])
                
                results.append({
                    "pmc_id": pmc_id,
                    "title": title,
                    "authors": authors_str,
                    "abstract": abstract[:500] + "..." if len(abstract) > 500 else abstract,
                    "full_text_url": f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/"
                })
        
        log(f"✓ PMC: Retrieved {len(results)} articles", "SUCCESS")
        return results
    except Exception as e:
        log(f"✗ PMC Error: {e}", "ERROR")
        return []

def search_semantic_scholar(query, max_results=10):
    """Search Semantic Scholar for papers (uses API key if available)"""
    log(f"Searching Semantic Scholar for '{query}'...")
    results = []
    
    if not SEMANTIC_SCHOLAR_API_KEY:
        log("⚠️  Semantic Scholar API key not found. Skipping.", "WARNING")
        return results
    
    def do_search():
        import requests
        
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query,
            "limit": max_results,
            "fields": "title,year,citationCount,abstract,authors,externalIds",
            "apiKey": SEMANTIC_SCHOLAR_API_KEY
        }
        
        # Semantic Scholar API only accepts apiKey as query param, not header
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 429:
            log("⚠️  Semantic Scholar rate limited. Returning empty results.", "WARNING")
            return []
        elif response.status_code != 200:
            log(f"✗ Semantic Scholar Error: {response.status_code}", "ERROR")
            return []
        
        data = response.json()
        papers = data.get('data', [])
        
        for paper in papers[:max_results]:
            authors = paper.get('authors', [])
            authors_str = ", ".join([f"{a.get('name', 'Unknown')}" for a in authors[:5]])
            
            results.append({
                "title": paper.get('title', 'N/A'),
                "year": paper.get('year'),
                "citationCount": paper.get('citationCount', 0),
                "abstract": paper.get('abstract', 'N/A'),
                "authors": authors_str,
                "externalIds": paper.get('externalIds', {})
            })
        
        log(f"✓ Semantic Scholar: Found {len(results)} results", "SUCCESS")
        return results
    
    try:
        result = retry_with_backoff(do_search, max_retries=2, base_delay=30)
        return result if result is not None else []
    except Exception as e:
        log(f"✗ Semantic Scholar Error: {e}", "ERROR")
        return []

def download_pdf(url, output_dir=None):
    """Download PDF from URL"""
    if output_dir is None:
        output_dir = OUTPUT_DIR
    
    try:
        filename = url.split('/')[-1]
        if not filename.endswith('.pdf'):
            filename += '.pdf'
        
        filepath = os.path.join(output_dir, filename)
        urllib.request.urlretrieve(url, filepath)
        
        file_size = os.path.getsize(filepath)
        log(f"✓ Downloaded: {filename} ({file_size / 1024 / 1024:.1f} MB)", "SUCCESS")
        return filepath
    except Exception as e:
        log(f"✗ Download Error: {e}", "ERROR")
        return None

def read_pdf(filepath):
    """Read PDF and extract text"""
    try:
        import fitz
        
        doc = fitz.open(filepath)
        text = ""
        for page in doc:
            text += page.get_text()
        
        log(f"✓ Read: {len(text)} chars from {len(doc)} pages", "SUCCESS")
        return text
    except Exception as e:
        log(f"✗ PDF Reading Error: {e}", "ERROR")
        return None

def generate_bibtex(verified_citations):
    """
    Generate BibTeX entries from verified citations only.
    This ensures ONLY real, API-verified papers are in the bibliography.
    """
    bibtex_entries = []

    for citation in verified_citations:
        entry_type = 'article'
        if citation.get('source') == 'arxiv':
            entry_type = 'misc'

        doi = citation.get('doi', '')
        arxiv_id = citation.get('arxiv_id', '')
        title = citation.get('title', 'Unknown')
        authors = citation.get('authors', [])
        if isinstance(authors, list):
            authors_str = ' and '.join(authors[:10])  # BibTeX uses ' and ' separator
        else:
            authors_str = str(authors)

        year = citation.get('year') or 'N/A'
        journal = citation.get('journal', '') or citation.get('source', '')

        # Generate a clean citation key from first author + year
        first_author = authors[0].split()[-1] if authors else 'Unknown'
        first_author = re.sub(r'[^a-zA-Z]', '', first_author).lower()
        citation_key = f"{first_author}{year}"

        # Build BibTeX entry
        bibtex = f"@{entry_type}{{{citation_key},\n"
        bibtex += f'  title={{{title}}},\n'
        bibtex += f'  author={{{authors_str}}},\n'

        if entry_type == 'article':
            bibtex += f'  journal={{{journal}}},\n'
            bibtex += f'  year={{{year}}},\n'
        else:  # arxiv
            bibtex += f'  journal={{arXiv preprint arXiv:{arxiv_id}}},\n'
            bibtex += f'  year={{{year}}},\n'

        if doi:
            bibtex += f'  doi={{{doi}}},\n'
        if arxiv_id:
            bibtex += f'  url={{https://arxiv.org/abs/{arxiv_id}}},\n'

        bibtex += '}\n'
        bibtex_entries.append(bibtex)

    return '\n\n'.join(bibtex_entries)


def analyze_paper(paper_info):
    """Analyze a paper and generate summary"""
    log(f"Analyzing: {paper_info.get('title', 'Unknown')}")
    
    # Extract key information
    title = paper_info.get('title', 'Unknown')
    authors = paper_info.get('authors', [])
    if isinstance(authors, list):
        authors_str = ", ".join(authors[:5])
    else:
        authors_str = str(authors)
    
    summary = paper_info.get('summary', '') or paper_info.get('abstract', '')
    published = paper_info.get('published', 'N/A')
    
    # Generate analysis
    analysis = f"""
# Paper Analysis: {title}

## Basic Info
- **Authors:** {authors_str}
- **Published:** {published}
- **DOI:** {paper_info.get('doi', 'N/A')}
- **arXiv ID:** {paper_info.get('arxiv_id', 'N/A')}
- **PMC ID:** {paper_info.get('pmc_id', 'N/A')}

## Summary
{summary[:1000]}...

## Key Findings
(TODO: Extract key findings from the paper)

## Methods
(TODO: Extract methods used)

## Relevance to Our Research
(TODO: Assess relevance to porphyria transcriptomics)
"""
    
    log("✓ Analysis complete", "SUCCESS")
    return analysis

def save_results(results, filename=None):
    """Save research results to file"""
    if filename is None:
        filename = f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2)
    
    log(f"✓ Saved to {filepath}", "SUCCESS")
    return filepath

def main():
    """Main research workflow"""
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    command = sys.argv[1]
    
    if command == "search":
        if len(sys.argv) < 3:
            print("Usage: python3 research_workflow.py search \"topic\" [--max-results N]")
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
            "arxiv": search_arxiv(query, max_results),
            "crossref": search_crossref(query, max_results),
            "pmc": search_pmc(query, max_results),
            "semantic_scholar": search_semantic_scholar(query, max_results)
        }
        
        save_results(results)
        print(f"\nResearch complete for: {query}")
        print(f"arXiv: {len(results['arxiv'])} results")
        print(f"CrossRef: {len(results['crossref'])} results")
        print(f"PMC: {len(results['pmc'])} results")
        print(f"Semantic Scholar: {len(results['semantic_scholar'])} results")
        
    elif command == "pmc-search":
        if len(sys.argv) < 3:
            print("Usage: python3 research_workflow.py pmc-search \"topic\" [--max-results N]")
            return
        
        query = sys.argv[2]
        max_results = 10
        if "--max-results" in sys.argv:
            idx = sys.argv.index("--max-results")
            if idx + 1 < len(sys.argv):
                max_results = int(sys.argv[idx + 1])
        
        results = search_pmc(query, max_results)
        save_results({"timestamp": datetime.now().isoformat(), "query": query, "pmc": results})
        print(f"\nPMC search complete for: {query}")
        print(f"Found: {len(results)} articles")
        
    elif command == "download":
        if len(sys.argv) < 3:
            print("Usage: python3 research_workflow.py download <url_or_doi>")
            return
        
        url_or_doi = sys.argv[2]
        # TODO: Implement DOI to URL resolution
        log(f"Download requested: {url_or_doi}")
        
    elif command == "read":
        if len(sys.argv) < 3:
            print("Usage: python3 research_workflow.py read <pdf_path>")
            return
        
        pdf_path = sys.argv[2]
        if os.path.exists(pdf_path):
            text = read_pdf(pdf_path)
            if text:
                # Save extracted text
                base_name = os.path.basename(pdf_path).replace('.pdf', '_text.txt')
                text_path = os.path.join(OUTPUT_DIR, base_name)
                with open(text_path, 'w') as f:
                    f.write(text)
                log(f"✓ Text saved to {text_path}", "SUCCESS")
        else:
            log(f"File not found: {pdf_path}", "ERROR")
            
    elif command == "full-analysis":
        if len(sys.argv) < 3:
            print("Usage: python3 research_workflow.py full-analysis \"topic\"")
            return
        
        query = sys.argv[2]
        log(f"Starting full analysis for: {query}")
        
        # Search all sources
        arxiv_results = search_arxiv(query, 3)
        crossref_results = search_crossref(query, 3)
        pmc_results = search_pmc(query, 3)
        ss_results = search_semantic_scholar(query, 3)
        
        # Combine results
        all_results = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "arxiv": arxiv_results,
            "crossref": crossref_results,
            "pmc": pmc_results,
            "semantic_scholar": ss_results,
            "summary": {
                "total_papers": len(arxiv_results) + len(crossref_results) + len(pmc_results) + len(ss_results),
                "sources": ["arXiv", "CrossRef", "PMC", "Semantic Scholar"]
            }
        }
        
        save_results(all_results)
        
        # Save to memory
        save_to_memory(
            f"Research: {query}",
            f"Found {len(arxiv_results)} arXiv papers, {len(crossref_results)} CrossRef papers, {len(pmc_results)} PMC articles, {len(ss_results)} Semantic Scholar papers"
        )
        
        print(f"\nFull analysis complete for: {query}")
        print(f"Total papers found: {all_results['summary']['total_papers']}")
        
    elif command == "verify":
        # Verify a citation by DOI, arXiv ID, or title
        if len(sys.argv) < 3:
            print("Usage: python3 research_workflow.py verify <doi> | <arxiv_id> | --title \"Title\"")
            return

        query = sys.argv[2]
        doi = None
        arxiv_id = None
        title = None
        authors = None
        year = None

        if query.startswith("10."):
            # Assume DOI
            doi = query
        elif "arxiv.org" in query or query.startswith("2"):
            # Assume arXiv ID or URL
            arxiv_id = query
        elif query.startswith("--title"):
            # Title search
            title = sys.argv[3] if len(sys.argv) > 3 else None

        result = verify_citation(doi=doi, arxiv_id=arxiv_id, title=title, authors=authors, year=year)

        if result:
            print(f"\n✓ CITATION VERIFIED:\n")
            print(f"  Title: {result['title']}")
            print(f"  Authors: {result.get('authors', 'N/A')}")
            print(f"  Year: {result.get('year', 'N/A')}")
            print(f"  DOI: {result.get('doi', 'N/A')}")
            print(f"  Source: {result['source']}")
            print(f"  Open Access: {result.get('open_access', 'N/A')}")
        else:
            print(f"\n✗ CITATION NOT VERIFIED")
            print(f"  The paper could not be found in any database.")
            print(f"  Do NOT add this to a bibliography.")

    elif command == "check-bib":
        # Verify all citations in a bibliography file
        if len(sys.argv) < 3:
            print("Usage: python3 research_workflow.py check-bib <bibliography.json>")
            return

        bib_file = sys.argv[2]
        if not os.path.exists(bib_file):
            print(f"File not found: {bib_file}")
            return

        with open(bib_file, 'r') as f:
            citations = json.load(f)

        if isinstance(citations, dict):
            citations = [citations]

        print(f"\nVerifying {len(citations)} citations from {bib_file}...\n")
        verified, unverified = build_verified_bibliography(citations)

        # Save results
        result_file = bib_file.replace('.json', '_verified.json')
        with open(result_file, 'w') as f:
            json.dump({
                "verified": verified,
                "unverified": unverified,
                "summary": {
                    "total": len(citations),
                    "verified_count": len(verified),
                    "unverified_count": len(unverified)
                }
            }, f, indent=2)

        print(f"Results saved to: {result_file}")

    else:
        print(f"Unknown command: {command}")
        print(__doc__)

def verify_and_add_to_bibliography(citation, bib_file="references.bib"):
    """
    Verify a citation and add it to the bibliography if verified.
    This is the MAIN function to use when adding citations.

    Args:
        citation: Dict with keys: doi, arxiv_id, title, authors, year
        bib_file: Path to the bibliography file

    Returns:
        True if citation was verified and added, False otherwise
    """
    result = verify_citation(
        doi=citation.get('doi'),
        arxiv_id=citation.get('arxiv_id'),
        title=citation.get('title'),
        authors=citation.get('authors'),
        year=citation.get('year')
    )

    if result:
        # Generate BibTeX entry
        bibtex = generate_bibtex([result])

        # Append to bibliography file
        with open(bib_file, 'a') as f:
            f.write('\n' + bibtex + '\n')

        log(f"✓ Added verified citation to {bib_file}", "SUCCESS")
        return True
    else:
        log(f"✗ Citation rejected: {citation.get('title', 'Unknown')}", "ERROR")
        return False


def verify_existing_bibliography(bib_file="references.bib"):
    """
    Verify all citations in an existing bibliography file.
    Returns a list of verified entries and a list of unverified entries.
    """
    if not os.path.exists(bib_file):
        log(f"Bibliography file not found: {bib_file}", "ERROR")
        return [], []

    # Parse BibTeX entries (simplified parser)
    with open(bib_file, 'r') as f:
        content = f.read()

    # Extract entries
    entries = re.findall(r'@\w+\{([^}]+),\n(.*?)\n\}', content, re.DOTALL)

    citations = []
    for key, fields in entries:
        citation = {}
        for field in ['title', 'author', 'doi', 'year', 'journal', 'url']:
            match = re.search(f'{field}=(.*?)\n', fields)
            if match:
                citation[field] = match.group(1).strip()

        # Extract arXiv ID from URL or journal
        url_match = re.search(r'url=\{?(https?://arxiv\.org/abs/(\S+?))\}?', fields)
        if url_match:
            citation['arxiv_id'] = url_match.group(2)

        citations.append(citation)

    return build_verified_bibliography(citations)


if __name__ == "__main__":
    main()
