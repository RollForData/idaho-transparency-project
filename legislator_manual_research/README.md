# legislator_manual_research

This folder contains the sync script that loads manually researched legislator data into the PostgreSQL database.

## Contents

`sync_manual_research.py` — reads a local CSV export from Google Sheets and syncs it to the `legislator_manual_research` table.

`legislator_manual_research.csv` — local working file only, not tracked in git. Export this fresh from the Google Sheets tab `analysis_wikipedia_duckduckgo` before each sync run.

## To run a sync

1. Open Google Sheets and make your edits in the `analysis_wikipedia_duckduckgo` tab
2. Export that tab as CSV and save it to this folder, overwriting the existing file
3. Run: `py sync_manual_research.py`

## How this script works

Full delete and reinsert every run. It wipes the entire `legislator_manual_research` table and rebuilds it from whatever is in the CSV. This is safe because `legislator_id` values come directly from your spreadsheet and trace back to stable IDs in the `legislators` table.

## Dependencies

Requires the `legislators` table to be populated first. `legislator_id` is a foreign key referencing `legislators(id)`. If an ID in the CSV does not match a real legislator, the insert will fail.