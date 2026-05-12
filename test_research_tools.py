#!/usr/bin/env python3
"""
Research Tools Test Suite
Tests all research APIs and saves results to workspace.
"""

import json
import os
import re
import time
from datetime import datetime

# Create output directory
output_dir = "/home/clawdbot/.openclaw/workspace-ross/research"
os.makedirs(output_dir, exist_ok=True)

def log(message):
    """Print with timestamp"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def test_arxiv():
    """Test arXiv API"""
    log("Testing arXiv API...")
    results = []
    try:
        import arxiv
        # Test with broader query
        search = arxiv.Search(query="machine learning genomics", max_results=5)
        client = arxiv.Client()
        for i, paper in enumerate(client.results(search)):
            results.append({
                "title": paper.title,
                "published": str(paper.published.date()),
                "authors": [str(a) for a in paper.authors[:3]],
                "summary": paper.summary[:200] + "..." if len(paper.summary) > 200 else paper.summary,
                "pdf_url": paper.pdf_url,
                "arxiv_id": paper.entry_id
            })
            if i >= 4:
                break
        
        log(f"✓ arXiv: Found {len(results)} results")
        return {"status": "OK", "results": results}
    except Exception as e:
        log(f"✗ arXiv Error: {e}")
        return {"status": "ERROR", "error": str(e)}

def test_crossref():
    """Test CrossRef API"""
    log("Testing CrossRef API...")
    results = []
    try:
        import crossref
        cr = crossref.CrossRefAPIClient()
        response = cr.get_works(params={"query": "porphyria transcriptomics"})
        data = response.json()
        
        items = data.get('message', {}).get('items', [])
        for item in items[:5]:
            results.append({
                "title": item.get('title', ['N/A'])[0],
                "doi": item.get('DOI', 'N/A'),
                "published": item.get('published-print', {}).get('date-parts', [[0]])[0][0],
                "authors": item.get('author', []),
                "citation_count": item.get('is-referenced-by-count', 0)
            })
        
        log(f"✓ CrossRef: Found {len(results)} results")
        return {"status": "OK", "results": results}
    except Exception as e:
        log(f"✗ CrossRef Error: {e}")
        return {"status": "ERROR", "error": str(e)}

def test_semantic_scholar():
    """Test Semantic Scholar API (with rate limit handling)"""
    log("Testing Semantic Scholar API...")
    results = []
    try:
        from semanticscholar import SemanticScholar
        sh = SemanticScholar()
        
        # Try with timeout and retry
        for attempt in range(3):
            try:
                papers = sh.search_paper("transcriptomics", limit=3)
                for paper in papers:
                    results.append({
                        "title": paper.title[:80] if paper.title else "N/A",
                        "year": paper.year,
                        "citationCount": paper.citationCount,
                        "abstract": paper.abstract[:200] + "..." if paper.abstract and len(paper.abstract) > 200 else paper.abstract
                    })
                log(f"✓ Semantic Scholar: Found {len(results)} results")
                return {"status": "OK", "results": results}
            except Exception as e:
                if "429" in str(e) or "TooManyRequests" in str(e):
                    log(f"  Rate limited, waiting 60s...")
                    time.sleep(60)
                elif attempt < 2:
                    log(f"  Error, retrying ({attempt+1}/3)...")
                    time.sleep(10)
                else:
                    raise
        
        log(f"✓ Semantic Scholar: Found {len(results)} results")
        return {"status": "OK", "results": results}
    except Exception as e:
        log(f"✗ Semantic Scholar Error: {e}")
        return {"status": "ERROR", "error": str(e)}

def test_pmc():
    """Test PMC API"""
    log("Testing PMC API...")
    results = []
    try:
        import requests
        
        # Search PMC
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        search_params = {
            "db": "pmc",
            "term": "porphyria transcriptomics",
            "retmax": 5,
            "retmode": "json"
        }
        response = requests.get(search_url, params=search_params, timeout=30)
        data = response.json()
        
        pmc_ids = data['esearchresult']['idlist']
        total_count = data['esearchresult']['count']
        
        log(f"✓ PMC: Found {total_count} total articles, testing {len(pmc_ids)}...")
        
        # Get full text for first article
        if pmc_ids:
            pmc_id = pmc_ids[0]
            text_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            text_params = {
                "db": "pmc",
                "id": pmc_id,
                "retmode": "xml",
                "rettype": "xml"
            }
            text_response = requests.get(text_url, params=text_params, timeout=30)
            
            if text_response.status_code == 200:
                # Extract text from XML
                text_content = re.sub(r'<[^>]+>', ' ', text_response.text)
                text_content = ' '.join(text_content.split())
                
                results.append({
                    "pmc_id": pmc_id,
                    "full_text_length": len(text_content),
                    "preview": text_content[:500] + "..." if len(text_content) > 500 else text_content
                })
                log(f"✓ PMC: Successfully fetched full text ({len(text_content)} chars)")
            else:
                log(f"✗ PMC: Failed to fetch full text (status {text_response.status_code})")
        
        return {"status": "OK", "total_articles": total_count, "results": results}
    except Exception as e:
        log(f"✗ PMC Error: {e}")
        return {"status": "ERROR", "error": str(e)}

def test_pdf_reading():
    """Test PDF reading with PyMuPDF"""
    log("Testing PDF reading...")
    try:
        import fitz
        import urllib.request
        
        # Download a test PDF
        pdf_url = "https://arxiv.org/pdf/2401.00001.pdf"
        pdf_path = os.path.join(output_dir, "test_paper.pdf")
        
        # Download
        urllib.request.urlretrieve(pdf_url, pdf_path)
        log(f"✓ Downloaded test PDF ({os.path.getsize(pdf_path)} bytes)")
        
        # Read with PyMuPDF
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        
        log(f"✓ PyMuPDF: Extracted {len(text)} chars from {len(doc)} pages")
        
        # Clean up
        os.remove(pdf_path)
        
        return {"status": "OK", "pages": len(doc), "chars": len(text)}
    except Exception as e:
        log(f"✗ PDF Reading Error: {e}")
        return {"status": "ERROR", "error": str(e)}

def main():
    log("Starting Research Tools Test Suite...")
    log("=" * 50)
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "tests": {}
    }
    
    # Run all tests
    results["tests"]["arxiv"] = test_arxiv()
    time.sleep(1)  # Rate limit handling
    
    results["tests"]["crossref"] = test_crossref()
    time.sleep(1)
    
    results["tests"]["semantic_scholar"] = test_semantic_scholar()
    time.sleep(1)
    
    results["tests"]["pmc"] = test_pmc()
    time.sleep(1)
    
    results["tests"]["pdf_reading"] = test_pdf_reading()
    
    # Save results
    output_file = os.path.join(output_dir, "test_results.json")
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    log("=" * 50)
    log(f"Test results saved to {output_file}")
    
    # Print summary
    log("\nSummary:")
    for test_name, test_result in results["tests"].items():
        status = test_result.get("status", "UNKNOWN")
        log(f"  {test_name}: {status}")
    
    # Check if all tests passed
    all_passed = all(r.get("status") == "OK" for r in results["tests"].values())
    if all_passed:
        log("\n🎉 All tests passed! Research infrastructure is ready.")
    else:
        log("\n⚠️  Some tests failed. Check the results for details.")
    
    return results

if __name__ == "__main__":
    main()
