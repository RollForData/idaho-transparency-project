# Idaho Legislative Transparency Project

A public-facing database and dashboard profiling all 105 Idaho state legislators, making it easy for any Idaho voter to look up their representative and understand who funds them, how they vote, and how their district has changed during their tenure.

## What This Project Does

Civic data in Idaho is publicly available but deliberately fragmented across multiple government systems with no easy way to connect it. This project pulls from public sources to build a unified, searchable profile for every Idaho state legislator.

Each legislator profile will include:

- **Identity and background** - chamber, district, party, terms served, occupation
- **Funding sources** - campaign donors broken down by type, in-state vs out-of-state, PAC contributions, and top donors
- **Notable votes** - key votes paired with donor data to surface connections between funding sources and voting records
- **Demographic context** - how the legislator compares to the constituents they represent

## How It Works

Data is collected through Python scripts that scrape the Idaho Legislature website and pull from campaign finance APIs. All data is stored in a PostgreSQL database. Visualization layer is planned for Tableau Public.

## What Is Currently Built

**legislators table** — populated by `scraper_legislators.py`, which scrapes the Idaho Legislature House and Senate membership pages and upserts all 105 legislators into PostgreSQL.

**legislator_manual_research table** — a 1:1 extension of the legislators table containing manually researched demographic data. Managed via Google Sheets and synced to the database using `sync_manual_research.py`.

**funding_archive_2000_2018** — raw campaign finance data downloaded from the Idaho Secretary of State archive covering 2000 to 2018. Cleaned and standardized using `clean_funding_archive.py`. Pending load into PostgreSQL.

## Data Sources

- Idaho Legislature membership directory (legislature.idaho.gov)
- Idaho Secretary of State campaign finance archive (sos.idaho.gov)
- Idaho Sunshine campaign finance portal (sunshine.voteidaho.gov)
- Manual research via Wikipedia and DuckDuckGo

## Project Status

Active development. Core legislator infrastructure is live in PostgreSQL. Campaign finance data pipeline is in progress across three systems covering 2000 to present.

## Built By

RollForData