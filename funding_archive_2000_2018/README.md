# funding_archive_2000_2018

This folder contains the raw source data and cleaning script for Idaho campaign finance contributions from 2000 to 2018, sourced from the Idaho Secretary of State data archive. This dataset is static and will not be updated by the state. The script should not need to be rerun unless the PostgreSQL table needs to be recreated from scratch.

## Contents

`clean_funding_archive.py` — reads the raw archive spreadsheet, applies standardization and cleanup transformations, outputs a cleaned single-sheet Excel file, and loads all records directly into PostgreSQL as a flat table.

`funding_data_archive_2000_2018.xlsx` — raw source data downloaded from the Idaho SOS archive. This file should never be replaced or modified. It is the permanent source of record for this dataset. Not tracked in git.

`funding_data_archive_2000_2018_cleaned.xlsx` — cleaned output file produced by the script. Single-sheet flat table combining all report years. Not tracked in git.

## To run

From the project root:

`py funding_archive_2000_2018\clean_funding_archive.py`

This will overwrite the cleaned Excel file and drop and recreate the `funding_archive_2000_2018` table in PostgreSQL.

## What the script does

- Trims leading and trailing whitespace from all string fields
- Strips trailing commas, semicolons, and colons from the end of any cell value
- Corrects specific known malformed city values: Spokane, Cranbury, and Milwaukee where trailing commas were present in the source data
- Converts numeric state codes to their correct two-letter abbreviations (8, 10, 55, 83 to ID; 11 to NY; 50 to ID)
- Corrects Ae to AE and uppercases any mixed or lowercase value that matches a valid USPS state or military mail abbreviation; non-standard values that cannot be resolved are left as-is and noted as government source data quality issues
- Converts all party abbreviations to full names (REP to Republican, DEM to Democratic, etc.)
- Standardizes Election values G and P to General and Primary; all other values including blank are set to NULL; Election data was not recorded in years 2000 through 2010 and NULL values in those years are expected, not a script error
- Sets ElectionYear to NULL where no data exists in the source; it is not inferred from the report year tab; ElectionYear data was not recorded in years 2000 through 2010 and NULL values in those years are expected, not a script error
- Adds a `report_year` column populated from the source tab name (2000 through 2018); this preserves the original report year grouping from the state's filing system after all tabs are merged into a single flat table
- Derives Contributor Type from the original ContrCP field; where contributor name matches candidate name exactly, the value is overridden to Self; drops ContrCP
- Derives Transaction Type from ContrType and contribution amount: negative amounts become Returned Contribution, positive loan amounts become Loan; derives Transaction Sub Type at a more detailed level: negative loan amounts become Loan Repayment rather than Returned Contribution, In-Kind and Loan map from their source codes, all other positive amounts default to Itemized; drops ContrType
- Standardizes ContrDate to YYYY-MM-DD format; unparseable dates are set to NULL
- Cleans zip codes to 5-digit format; zero-pads 4-digit codes; nulls invalid entries
- Adds a `ContrDateDiscrepancy` column flagging rows where the ContrDate year falls more than 2 years outside the report year tab with the value "ContrDate falls more than 2 years outside of report year"; this is informational only and no data is altered; unflagged rows are NULL in this column

## Data notes

- 2019 data is missing from the archive entirely. A public records request has been filed with the Idaho Secretary of State for this data.
- Election and ElectionYear were not consistently recorded in years 2000 through 2010. NULL values in those fields for those years reflect the source data, not a script error.
- Non-standard ContributorState values including Canadian provinces and unrecognized codes exist in the source data and have been left as-is. These are government data quality issues and are not corrected by this script.
- 90 rows are flagged in ContrDateDiscrepancy as having a contribution date more than 2 years outside their report year tab. These rows have not been altered.
- This dataset covers report years 2000, 2002, 2004, 2006, 2008, 2010, 2012, 2014, 2016, and 2018. There is no 2001, 2003, etc. because the source system grouped records by even-year election cycles.

## Dependencies

Raw source file `funding_data_archive_2000_2018.xlsx` must be present in this folder before running the script.