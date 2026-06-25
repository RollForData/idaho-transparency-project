# funding_archive_2000_2018

This folder contains the cleaning script and raw source data for Idaho campaign finance contributions from 2000 to 2018, sourced from the Idaho Secretary of State data archive.

## Contents

`clean_funding_archive.py` — reads the raw archive spreadsheet, applies standardization and cleanup transformations, and outputs a cleaned version ready for loading into PostgreSQL.

`funding_data_archive_2000_2018.xlsx` — raw source data downloaded from the Idaho SOS archive. Local working file only, not tracked in git.

`funding_data_archive_2000_2018_cleaned.xlsx` — cleaned output file produced by the script. Local working file only, not tracked in git.

## To run a cleanup

1. Make sure `funding_data_archive_2000_2018.xlsx` is present in this folder
2. From the project root run: `py funding_archive_2000_2018\clean_funding_archive.py`
3. The cleaned file will be saved to this folder as `funding_data_archive_2000_2018_cleaned.xlsx`

## What the script does

- Standardizes all party abbreviations to full names (REP to Republican, DEM to Democratic, etc.)
- Renames ContrCP to Contributor Type and adds Self classification where candidate and contributor names match
- Renames ContrType to Transaction Type and adds Transaction Sub Type based on contribution classification
- Fills ElectionYear from the sheet tab name where blank
- Standardizes Election values (G to General, P to Primary, blank to Unknown)
- Strips all string fields of leading and trailing whitespace
- Standardizes ContrDate to YYYY-MM-DD format
- Cleans zip codes to 5 digits, zero pads 4 digit codes, nulls out invalid entries

## Data notes

- 2019 data is missing from the archive with no explanation from the state
- Election and Election Year were not tracked in years 2000 through 2010 and have been inferred or set to Unknown
- Contributor type classification for years 2000 through 2010 was inconsistent and has been standardized
- P as a ContrType value in 2002 through 2006 could not be definitively classified and has been treated as a standard Contribution
- Loan repayment tracking disappears after 2010 and is not consistently recorded in later years

## Dependencies

Raw source files must be present in this folder before running the script.