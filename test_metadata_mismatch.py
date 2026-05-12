#!/usr/bin/env python3
"""
Test that metadata mismatch detection catches hallucinated citations.

These are the 3 citations that previously slipped through because:
- The arXiv IDs resolved to REAL papers
- But those papers were COMPLETELY DIFFERENT from what was claimed

This test proves the fix catches them.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from research_workflow import verify_citation, compare_metadata

# The 3 hallucinated citations that slipped through
HALLUCINATED = [
    {
        "key": "kratzwallner2013arxiv",
        "claimed_title": "The arXiv API",
        "claimed_authors": ["Kratzwallner, Adam"],
        "claimed_year": "2013",
        "arxiv_id": "1308.5633",
        "note": "arXiv:1308.5633 is actually about Navier-Stokes equations (math)",
    },
    {
        "key": "li2024automated",
        "claimed_title": "Automated Literature Review with LLMs",
        "claimed_authors": ["Li, et al."],
        "claimed_year": "2024",
        "arxiv_id": "2412.13612",
        "note": "arXiv:2412.13612 is by Tang et al., NOT Li et al.",
    },
    {
        "key": "wang2024litllm",
        "claimed_title": "LitLLM: An LLM-Based Toolkit for Literature Review",
        "claimed_authors": ["Wang, et al."],
        "claimed_year": "2024",
        "arxiv_id": "2402.08565",
        "note": "arXiv:2402.08565 is by Bolanos et al., NOT Wang et al.",
    },
]

print("=" * 70)
print("TEST: Metadata mismatch detection")
print("=" * 70)
print()
print("These 3 citations previously passed verification because the")
print("arXiv IDs resolved to REAL papers — just NOT the ones claimed.")
print()

caught = 0
total = len(HALLUCINATED)

for citation in HALLUCINATED:
    print(f"--- Testing: {citation['key']} ---")
    print(f"  Claimed: '{citation['claimed_title']}'")
    print(f"  arXiv ID: {citation['arxiv_id']}")
    print(f"  Note: {citation['note']}")
    print()

    result = verify_citation(
        arxiv_id=citation["arxiv_id"],
        title=citation["claimed_title"],
        authors=citation["claimed_authors"],
        year=citation["claimed_year"],
    )

    if result is None:
        print(f"  ✅ REJECTED - metadata mismatch detected!")
        caught += 1
    else:
        print(f"  ❌ PASSED - THIS IS A BUG! Citation should have been rejected.")
        print(f"  Actual paper: {result.get('title', 'Unknown')}")
        print(f"  Match score: {result.get('match_score', 'N/A')}")

    print()

print("=" * 70)
print(f"RESULT: {caught}/{total} hallucinated citations caught")
print("=" * 70)

if caught == total:
    print("✅ ALL HALLUCINATED CITATIONS DETECTED - Fix is working!")
    sys.exit(0)
else:
    print("❌ SOME HALLUCINATED CITATIONS SLIPPED THROUGH - Fix incomplete!")
    sys.exit(1)
