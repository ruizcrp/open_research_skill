#!/usr/bin/env python3
"""
Test that correct citations still pass verification.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from research_workflow import verify_citation

# These are the 8 citations that were correctly verified
CORRECT = [
    {
        "key": "ram2014arxiv",
        "doi": "10.32614/cran.package.arxiv",
        "title": "aRxiv: Interface to the arXiv API",
        "authors": ["Ram, K.", "Broman, K. W."],
        "year": "2014",
    },
    {
        "key": "wilson2023diamond",
        "doi": "10.29173/cais1845",
        "title": "The Value of a Diamond: Understanding Global Coverage of Diamond Open Access Journals in Web of Science, Scopus, and OpenAlex to Support an Open Future",
        "authors": ["Simard, Marc-And\u00e9", "Basson, Isabel", "Hare, Madelaine", "Larivi\u00e8re, Vincent", "Mongeon, Philippe"],
        "year": "2024",
    },
    {
        "key": "chelli2024chatgpt",
        "doi": "10.2196/53164",
        "title": "Hallucination Rates and Reference Accuracy of ChatGPT and Bard for Systematic Reviews: Comparative Analysis",
        "authors": ["Chelli, Mika\u00ebl", "Descamps, Jules", "Lavou\u00e9, Vincent", "Trojani, Christophe", "Azar, Michel", "Deckert, Marcel", "Raynier, Jean-Luc", "Clowez, Gilles", "Boileau, Pascal", "Ruetsch-Chelli, Caroline"],
        "year": "2024",
    },
]

print("=" * 70)
print("TEST: Correct citations should PASS")
print("=" * 70)
print()

passed = 0
total = len(CORRECT)

for citation in CORRECT:
    print(f"--- Testing: {citation['key']} ---")
    print(f"  Title: {citation['title']}")
    print(f"  DOI: {citation['doi']}")

    result = verify_citation(
        doi=citation["doi"],
        title=citation["title"],
        authors=citation["authors"],
        year=citation["year"],
    )

    if result and result.get('verified'):
        print(f"  ✅ PASSED - '{result['title']}'")
        passed += 1
    else:
        print(f"  ❌ FAILED - This correct citation was rejected!")

    print()

print("=" * 70)
print(f"RESULT: {passed}/{total} correct citations passed")
print("=" * 70)

if passed == total:
    print("✅ ALL CORRECT CITATIONS PASSED - No regressions!")
    sys.exit(0)
else:
    print("❌ SOME CORRECT CITATIONS REJECTED - Regression!")
    sys.exit(1)
