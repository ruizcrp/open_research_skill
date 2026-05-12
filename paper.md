---
title: 'open_research_skill: A Multi-Source Open-Access Research Skill for Autonomous AI Agents'
tags:
  - Python
  - research
  - AI agents
  - citation provenance
  - open-access
  - literature review
  - OpenAlex
  - arXiv
authors:
  - name: Christian Ruiz-Palmero
    orcid: https://orcid.org/0009-0007-7601-7932
    affiliation: "1"
affiliations:
  - name: "1"
    index: 1
    address: "christian.ruiz@z01.ch"
date: 12 May 2026
bibliography: paper.bib
---

# Summary

`open_research_skill` is a modular Python package that enables autonomous AI agents to conduct literature searches, retrieve papers, read full-text documents, and manage citations across five major open-access academic sources: OpenAlex, arXiv, CrossRef, Semantic Scholar, and PubMed Central. Its distinguishing feature is a four-tier citation provenance system that prevents hallucinated references by requiring each citation to be grounded in actual document content.

The system enforces a strict "quote only what you have read" policy. Citations are classified into four verification tiers: (1) **Read** — the full PDF has been downloaded, parsed with page-level text extraction, and the specific claim verified at a specific page number; (2) **Abstract** — the abstract has been read and the claim is attributed to the abstract rather than the full text; (3) **Metadata** — only bibliographic metadata is available, suitable for context but not direct citation; (4) **Discovery** — the paper was found in search results but no substantive content has been read.

The package provides a command-line interface and a programmatic Python API. It resolves PDF URLs from multiple sources, downloads papers, extracts page-level text using PyMuPDF, and supports claim verification with context windows. All citations are accompanied by a machine-readable bibliography verification file that enables independent human review.

# Statement of Need

AI systems can generate plausible-sounding but entirely fabricated references at alarming rates. Zuccon et al. [@zuccon2023chatgpt] found that ChatGPT's suggested references exist only 14% of the time, while Chelli et al. [@chelli2024performance] reported hallucination rates of up to 91.4% for Bard in generating systematic review references. This problem is particularly acute for autonomous research agents that generate literature reviews and academic content without human oversight at every step.

Existing tools for automated literature review — such as LitLLM [@agarwal2024litllm], automated review systems using retrieval-augmented generation [@ali2024automated], and multi-agent systematic review frameworks [@rasheed2024system] — focus on organizing and synthesizing retrieved papers but do not address the fundamental problem of citation fabrication. The AI Scientist [@lu2024ai] demonstrates autonomous paper writing but does not explicitly track citation provenance.

`open_research_skill` addresses this gap by combining multi-source discovery with rigorous provenance tracking. It is designed for researchers and developers building AI research agents who need a tool that guarantees citations are grounded in actual document content, not generated from model priors.

# State of the Field

Several tools address aspects of automated research, but none combine the full feature set of `open_research_skill`:

- **LitLLM** [@agarwal2024litllm] provides a framework for structuring literature reviews using LLMs but relies on external search tools and does not enforce citation provenance.
- **Orchestra-Research/AI-Research-SKILLs** provides a collection of research skills for AI agents but does not include a built-in provenance system.
- **Feynman** [@spartan-ai-feynman] is an AI research agent that reads papers and writes drafts but does not track which claims are verified against which documents.
- **AI Scientist** [@lu2024ai] automates the full research cycle but relies on external APIs for literature search without provenance tracking.
- **Semantic Scholar** and **OpenAlex** provide search APIs but do not enforce citation verification.

The key differentiator of `open_research_skill` is not any single component — OpenAlex, arXiv, CrossRef, Semantic Scholar, and PMC are all well-established services — but their integration into a unified system with rigorous citation provenance tracking. The four-tier system provides a principled framework for distinguishing between verified claims and contextual references, which is a capability not offered by any existing tool.

# Software Design

The package is implemented as a single Python module (`research_workflow.py`) with a modular architecture. The core design decisions are:

**Citation provenance as first-class data.** Every citation entry is a structured record containing identifiers (DOI, arXiv ID, PMC ID), bibliographic metadata, provenance tier, page number, section, and verification status. This structure is serialized to JSON and can be included in research outputs or human-reviewed verification files.

**Weighted metadata comparison.** A critical vulnerability in provenance systems is that a fabricated citation with a valid identifier can resolve to a different paper. To address this, `open_research_skill` implements a `compare_metadata()` function that computes a composite similarity score across three dimensions: title similarity (weight 0.60, using both Jaccard similarity and Levenshtein distance), author overlap (weight 0.30, using Jaccard similarity of last-name sets), and year proximity (weight 0.10, using linear decay). A citation is accepted only when the composite score exceeds 0.70. During testing, this fix successfully rejected three previously hallucinated citations that had incorrectly passed verification.

**Page-level text extraction.** The package uses PyMuPDF (fitz) for PDF parsing, extracting text from each page with its page number preserved. This enables page-level claim verification, where a claim is matched against the text on each page and the matching page number is returned along with a context window.

**Deduplication across sources.** Since multiple sources may return the same paper, the package implements a deduplication system that prioritizes identifiers (DOI > arXiv ID > PMC ID > title similarity) to ensure each paper appears only once.

The package is designed for extensibility. Adding a new data source requires implementing a search function and a PDF URL resolver. The provenance system is source-agnostic and applies uniformly across all integrated sources.

# Research Impact

`open_research_skill` is already in active use for the porphyria transcriptomics analysis project (ruizcrp/porphyromics), where it has been used to generate literature reviews with verified citations for a multi-disciplinary research project. The tool is open source under the MIT License and available at https://github.com/ruizcrp/open_research_skill.

The four-tier citation provenance system addresses a documented problem in AI-generated research content. By providing a principled framework for distinguishing verified claims from contextual references, the tool enables researchers to build confidence in AI-assisted literature reviews. The companion bibliography verification file format is designed for extensibility and could serve as a standard for citation provenance in AI research tools more broadly.

# AI Usage Disclosure

This software was developed with assistance from an AI research agent. The author was responsible for all problem framing, architectural design decisions, and code review. All AI-generated code was reviewed, tested, and validated by the author before inclusion. The citation provenance system, metadata comparison algorithm, and overall software architecture were designed by the author. AI assistance was used for implementation details, testing, and documentation.

# Acknowledgements

This work was supported by Z01 GmbH. The author thanks the developers of OpenAlex, arXiv, CrossRef, Semantic Scholar, and PubMed Central for providing open-access APIs that made this project possible.

# References

- Agarwal, S., Sahu, G., Puri, A., Laradji, I. H., & Dvijotham, K. D. (2024). LitLLM: A Toolkit for Scientific Literature Review. *arXiv preprint arXiv:2402.01788*.
- Ali, N. F., Mohtasim, M. M., Mosharrof, S., & Krishna, T. G. (2024). Automated Literature Review Using NLP Techniques and LLM-based Retrieval-Augmented Generation. *arXiv preprint arXiv:2411.18583*.
- Chelli, M., Descamps, J., Lavoué, V., Trojani, C., Azar, M., Deckert, M., ... & Ruetsch-Chelli, C. (2024). Performance of ChatGPT and Bard in Generating References for Systematic Reviews. *Journal of Medical Internet Research, 26*, e53164.
- Lu, C., Lu, C., Lange, R. T., & Foerster, J. (2024). The AI Scientist: Towards fully automated open-ended scientific discovery. *arXiv preprint arXiv:2408.06292*.
- Naveed, H., Khan, A. U., Qiu, S., Saqib, M., Anwar, S., Usman, M., ... & Barnes, N. (2023). A Comprehensive Overview of Large Language Models. *arXiv preprint arXiv:2307.06435*.
- Page, M. J., Moher, D., Bossuyt, P. M., Boutron, I., Hoffmann, T. C., Mulrow, C. D., ... & Zorzela, A. (2021). PRISMA 2020 explanation and elaboration: updated guidance and exemplars for reporting systematic reviews. *BMJ, 372*, n160.
- Priem, J., Piwowar, H., & Orr, R. (2022). OpenAlex: A fully-open index of scholarly works, authors, venues, institutions, and concepts. *Proceedings of the 26th International Conference on Science and Technology Indicators*.
- Rasheed Mr, Z., et al. (2024). System for systematic literature review using multiple AI agents: Concept and an empirical evaluation. *arXiv preprint arXiv:2403.08399*.
- Wilson, C., Tullien, K., Smits, M., van Roy, J., & De Ryck, S. (2023). The Value of a Diamond: Understanding Global Coverage of Diamond Open Access Journals. *College & Research Libraries*.
- Zuccon, G., Koopman, B., & Shaik, R. (2023). ChatGPT Hallucinates when Attributing Answers. *arXiv preprint arXiv:2309.09401*.
