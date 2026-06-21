# Source Analysis

This folder documents one-time research used to evaluate data sources for legislator biographical fields (birth year, birthplace, gender, religious affiliation) before building the production research process.

Four sourcing approaches were tested:

- **VoteSmart API**: rejected, requires a paid account for bulk access
- **Ballotpedia**: 77% page coverage across all 105 legislators, but only 0% birth year extraction and 10% religion extraction
- **Wikipedia (direct search)**: 34% page coverage, low extraction across all fields
- **Wikipedia (via DuckDuckGo search)**: 87% page coverage, the strongest result and the approach that informed the manual research process

`analysis_wikipedia_duckduckgo.py` contains the final, working version of this analysis.