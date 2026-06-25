# legislators

This folder contains the scraper that populates the `legislators` table in PostgreSQL with current membership data for all 105 Idaho state legislators.

## Contents

`scraper_legislators.py` — scrapes the Idaho Legislature website for House and Senate membership and upserts the data into the `legislators` table.

## To run the scraper

From the project root run: `py legislators\scraper_legislators.py`

## What the script does

- Scrapes the House and Senate membership pages at legislature.idaho.gov
- Extracts full name, chamber, district number, party affiliation, total terms, seat designation, occupation, headshot URL, and bio text for each legislator
- Calculates next election year based on the current year
- Upserts all records into the `legislators` table using full name as the unique key. Existing legislators are updated in place, new legislators are inserted. IDs never change.

## Important notes

- Do NOT manually delete from the `legislators` table before running. The upsert handles everything.
- The `legislators` table must be populated before running any script that depends on it, including `sync_manual_research.py`
- The scraper pulls live data from the legislature website. If the site structure changes, the scraper may need to be updated.

## Dependencies

Requires the `legislators` table to exist in PostgreSQL before running. See `schema.sql` in the project root for the table definition.