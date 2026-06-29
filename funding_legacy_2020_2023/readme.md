# funding_legacy_2020_2023

This folder contains the script that pulls Idaho campaign finance contribution data from the Idaho Secretary of State legacy campaign finance portal and loads it directly into PostgreSQL.

## Contents

`pull_funding_legacy.py` — pulls all donation activity from the legacy SOS API and loads it into the `funding_legacy_2020_2023` table in PostgreSQL. Drops and recreates the table on every run.

## To run the pull

From the project root run: `py funding_legacy_2020_2023\pull_funding_legacy.py`

## What the script does

- Connects to the legacy campaign finance API at canvass.sos.idaho.gov
- Pulls all donation activity from 01/01/2020 through 01/01/2027 across all candidates, offices, and PACs with a dollar range of $1 to $1,000,000
- Paginates through all results in batches of 1,000 records
- Drops and recreates the funding_legacy_2020_2023 table on every run
- Commits to PostgreSQL in batches so progress is not lost if the script fails mid-run
- Total dataset is 250,688 records covering 01/01/2020 through 01/12/2024

## Data notes

- The legacy system covers data through 12/20/2023 per the state's own documentation but actual data runs through 01/12/2024 with one stray record
- All return amounts are stored as positive numbers with donate_type of Return, not as negative amounts
- from_is_dupe appears to flag recurring donors but behavior is inconsistent and should not be used for filtering
- 15 fields were evaluated and excluded from this table due to being fully null across the entire dataset
- Future join logic to the legislators table has not yet been defined

## Dependencies

Requires PostgreSQL connection credentials in .env file. No other tables required currently. Future dependency on legislators table likely when join logic is defined.