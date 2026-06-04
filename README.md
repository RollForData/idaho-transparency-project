# Idaho Legislative Transparency Project

A public-facing database and dashboard that aggregates publicly available data on every Idaho state legislator, making it easy for any Idaho voter to look up their representative and understand who funds them, how they vote, and how their district has changed during their tenure.

## What This Project Does

Most civic data exists but is scattered across dozens of government websites with no easy way to connect it. This project pulls from public sources including the Idaho Legislature, Idaho Secretary of State, U.S. Census Bureau, Bureau of Labor Statistics, and campaign finance databases to build a unified, searchable profile for all 105 Idaho state legislators.

Each legislator profile includes:

- **Identity and background** - chamber, district, terms served, time registered to vote in Idaho
- **Demographic mirror** - how the legislator compares to their own district in age, wealth, race, and party registration
- **Funding sources** - campaign donors, independent expenditures, and out-of-state money broken down by industry and type
- **Notable votes** - key votes on Medicaid expansion and a documented pattern of votes to restrict Idaho's ballot initiative process, each paired with district-level impact data
- **District quality of life** - how key metrics like uninsured rate, homeownership, unemployment, and per-pupil education spending have changed since the legislator took office

## How It Works

Data is collected through Python web scrapers and API connections that run on a schedule via GitHub Actions. All data is stored in a PostgreSQL database and visualized through Tableau Public.

## Data Sources

- Idaho Legislature membership directory
- Idaho Secretary of State campaign finance portal
- U.S. Census Bureau / Census Reporter API
- Bureau of Labor Statistics
- FollowTheMoney.org campaign finance API
- LegiScan legislative tracking API
- County assessor records

## Project Status

Currently in active development. Proof of concept being built for Mike Moyle, Idaho House Speaker and longest-serving member of the Idaho Legislature.

## Built By

RollForData