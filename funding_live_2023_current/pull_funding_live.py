import pandas as pd
import re
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------
input_file = r"C:\Users\cathe\Documents\idaho-transparency-project\funding_live_2023_current\LIVE [Raw Data] funding_data_New_2023_current.xlsx"
output_file = r"C:\Users\cathe\Documents\idaho-transparency-project\funding_live_2023_current\LIVE [Clean Data] funding_data_New_2023_current.xlsx"

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------
RAW_COLUMNS = [
    'Filing Entity ID', 'Filing Entity Name', 'Campaign Name', 'Registration Type',
    'Transaction Id', 'Transaction Type', 'Transaction Sub Type', 'Contributor Type',
    'Contributor Last Name', 'Contributor First Name', 'Contributor Company Name',
    'Contributor Address Line 1', 'Contributor Address Line 2', 'Contributor Address City',
    'Contributor Address State', 'Contributor Address Zip Code', 'Transaction Date',
    'Transaction Amount', 'Loan Interest Amount', 'Total Loan Amount', 'Election Type',
    'Election Year', 'Transaction Description', 'Amended', 'Timed Report Name',
    'Timed Report Date', 'Report Name', 'Report Filed Date'
]

VALID_TRANSACTION_TYPES = {
    'Contribution',
    'Loan Received',
    'Loan Forgiven',
    'Return Contribution',
    'Outstanding Loan'
}

DOLLAR_FIELDS = ['Transaction Amount', 'Loan Interest Amount', 'Total Loan Amount']

AMOUNT_REQUIRED_TYPES = {'Contribution', 'Loan Received', 'Return Contribution'}

VALID_USPS_ABBREVIATIONS = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
    'DC', 'AS', 'GU', 'MP', 'PR', 'VI', 'AA', 'AE', 'AP'
}

STATE_CORRECTIONS = {
    'MIS': 'MS',
}

# ---------------------------------------------------------------------------
# CONFIRMED ROW-SPECIFIC PATCHES
# Reviewed and locked in on 2026-07-07. Keyed to (source_sheet, source_row_number),
# which is permanently stable since the raw workbook never gets re-downloaded.
# ---------------------------------------------------------------------------
ROW_PATCHES = {
    ('2025', '80809'): {
        'Transaction Description': (
            'Design for 3 different signage applications for Jim Young  Designs used '
            'for applications including Apparel, signs, decals, and digital media" '
            'Designs released to Jim Young for publication and free use"'
        ),
        'Amended': 'N',
        'Timed Report Name': 'Timed Contribution Report',
        'Timed Report Date': '2025-10-07',
        'Report Name': '2025 October Monthly Report',
        'Report Filed Date': '2025-11-10',
    },
    ('2026', '42198'): {
        'Transaction Description': (
            'Corrugated Plastic 4mm, 18 x 24" (standard), Double Sided, 2 color, '
            'For Wire Stakes"'
        ),
        'Amended': 'N',
        'Timed Report Name': None,
        'Timed Report Date': None,
        'Report Name': 'First $500 Report',
        'Report Filed Date': '2026-03-20',
    },
    ('2026', '2935'): {
        'Contributor Address Line 1': '20086 Nancy Ln',
        'Contributor Address Line 2': None,
        'Contributor Address City': 'Caldwell',
        'Contributor Address State': 'ID',
        'Contributor Address Zip Code': '83607',
        'Transaction Date': '2026-03-14',
        'Transaction Amount': '35',
        'Loan Interest Amount': '0',
        'Total Loan Amount': '0',
        'Election Type': None,
        'Election Year': None,
        'Transaction Description': 'Handmade Soap',
        'Amended': 'N',
        'Timed Report Name': None,
        'Timed Report Date': None,
        'Report Name': '2026 March Monthly Report',
        'Report Filed Date': '2026-04-09',
    },
    ('2026', '33172'): {
        'Contributor First Name': 'Sandra',
        'Contributor Company Name': None,
        'Contributor Address Line 1': '2075 N 5 E',
        'Contributor Address Line 2': None,
        'Contributor Address City': 'Mountain Home',
        'Contributor Address State': 'ID',
        'Contributor Address Zip Code': '83647-3647',
        'Transaction Date': '2026-03-18',
        'Transaction Amount': '200',
        'Loan Interest Amount': '0',
        'Total Loan Amount': '0',
        'Election Type': None,
        'Election Year': None,
        'Transaction Description': None,
        'Amended': 'N',
        'Timed Report Name': None,
        'Timed Report Date': None,
        'Report Name': '2026 March Monthly Report',
        'Report Filed Date': '2026-04-10',
    },
}

# ---------------------------------------------------------------------------
# CONFIRMED PERMANENT EXCLUSIONS
# Reviewed and locked in on 2026-07-07. This is a fixed list of specific rows,
# NOT an automated rule. New rows that resemble these patterns in future runs
# still go to "Needs Manual Review" and must be reviewed individually.
# ---------------------------------------------------------------------------
REASON_DATE_AMOUNT_MISSING = 'State did not report a Transaction Date or Transaction Amount for this transaction.'
REASON_IDENTITY_MISSING = 'Filing entity and/or contributor identity fields missing entirely; incomplete government record.'
REASON_JOINT_FILER_SPLIT = 'Joint filer record split across rows with no recoverable identity data.'

EXCLUDED_ROWS = {}

_group1 = [('2023', '2551'), ('2023', '2599'), ('2023', '2602'), ('2023', '19458'), ('2023', '35049'),
           ('2024', '36268'), ('2025', '5979'), ('2025', '6018'), ('2025', '6020'), ('2025', '6022'),
           ('2025', '6024'), ('2025', '6026'), ('2025', '6028'), ('2025', '6030'), ('2025', '6032'),
           ('2025', '6034'), ('2025', '6036'), ('2025', '6038'), ('2025', '6040'), ('2025', '6042'),
           ('2025', '6044'), ('2025', '6046'), ('2025', '6048'), ('2025', '6050'), ('2025', '6052'),
           ('2025', '6054'), ('2025', '6056'), ('2025', '6058'), ('2025', '6089'), ('2025', '6170'),
           ('2025', '6172'), ('2025', '6174'), ('2025', '6176'), ('2025', '6178'), ('2025', '6180'),
           ('2025', '6182'), ('2025', '6184'), ('2025', '6186'), ('2025', '6188'), ('2025', '6190'),
           ('2025', '6192'), ('2025', '6194'), ('2025', '6196'), ('2025', '6198'), ('2025', '6200'),
           ('2025', '6202'), ('2025', '6204'), ('2025', '29467'), ('2025', '29512'), ('2026', '4050'),
           ('2026', '4083'), ('2026', '4085'), ('2026', '4087'), ('2026', '4089'), ('2026', '4091'),
           ('2026', '4093'), ('2026', '4095'), ('2026', '4097'), ('2026', '4099'), ('2026', '4101'),
           ('2026', '4114'), ('2026', '4116'), ('2026', '4118'), ('2026', '4120'), ('2026', '4122'),
           ('2026', '4124'), ('2026', '4126'), ('2026', '4128'), ('2026', '4130'), ('2026', '4132'),
           ('2026', '7454'), ('2026', '11403')]
for k in _group1:
    EXCLUDED_ROWS[k] = REASON_DATE_AMOUNT_MISSING

_group2 = [('2023', '19459'), ('2023', '35050'), ('2024', '36269'), ('2025', '5980'), ('2025', '6019'),
           ('2025', '6021'), ('2025', '6023'), ('2025', '6025'), ('2025', '6027'), ('2025', '6029'),
           ('2025', '6031'), ('2025', '6033'), ('2025', '6035'), ('2025', '6037'), ('2025', '6039'),
           ('2025', '6041'), ('2025', '6043'), ('2025', '6045'), ('2025', '6047'), ('2025', '6049'),
           ('2025', '6051'), ('2025', '6053'), ('2025', '6055'), ('2025', '6057'), ('2025', '6059'),
           ('2025', '6090'), ('2025', '6171'), ('2025', '6173'), ('2025', '6175'), ('2025', '6177'),
           ('2025', '6179'), ('2025', '6181'), ('2025', '6183'), ('2025', '6185'), ('2025', '6187'),
           ('2025', '6189'), ('2025', '6191'), ('2025', '6193'), ('2025', '6195'), ('2025', '6197'),
           ('2025', '6199'), ('2025', '6201'), ('2025', '6203'), ('2025', '6205'), ('2025', '29468'),
           ('2025', '29513'), ('2026', '4051'), ('2026', '4084'), ('2026', '4086'), ('2026', '4088'),
           ('2026', '4090'), ('2026', '4092'), ('2026', '4094'), ('2026', '4096'), ('2026', '4098'),
           ('2026', '4100'), ('2026', '4102'), ('2026', '4115'), ('2026', '4117'), ('2026', '4119'),
           ('2026', '4121'), ('2026', '4123'), ('2026', '4125'), ('2026', '4127'), ('2026', '4129'),
           ('2026', '4131'), ('2026', '4133'), ('2026', '7455'), ('2026', '11404')]
for k in _group2:
    EXCLUDED_ROWS[k] = REASON_IDENTITY_MISSING

_group3 = [('2023', '2552'), ('2023', '2553'), ('2023', '2600'), ('2023', '2601'),
           ('2023', '2603'), ('2023', '2604')]
for k in _group3:
    EXCLUDED_ROWS[k] = REASON_JOINT_FILER_SPLIT


# ---------------------------------------------------------------------------
# GENERAL REPAIR RULE: corrupted apostrophe treated as a field delimiter
# (e.g. "O'Farrell", "Coeur d'Alene"). The corrupted apostrophe consistently
# appears as two literal U+FFFD replacement characters. Whichever column it
# lands in, merge it with the column before it and shift everything after
# left by one position.
# ---------------------------------------------------------------------------
CORRUPT_MARKER = '\ufffd\ufffd'


def repair_apostrophe_split(row_values):
    """
    row_values: list of the 28 RAW_COLUMNS values (in order) for one row,
    extended with any overflow ('Unnamed: N') values at the end.
    Returns a repaired list of exactly len(RAW_COLUMNS) values, or the
    original first 28 values unchanged if the pattern isn't found.
    """
    split_index = None
    for i, val in enumerate(row_values):
        if isinstance(val, str) and val.startswith(CORRUPT_MARKER):
            split_index = i
            break

    if split_index is None or split_index == 0:
        return row_values[:len(RAW_COLUMNS)]

    prefix = row_values[split_index - 1]
    prefix = '' if pd.isna(prefix) else str(prefix)
    suffix = str(row_values[split_index]).replace(CORRUPT_MARKER, '')

    merged = prefix + "'" + suffix

    repaired = list(row_values[:split_index - 1]) + [merged] + list(row_values[split_index + 1:])
    repaired = repaired[:len(RAW_COLUMNS)]
    while len(repaired) < len(RAW_COLUMNS):
        repaired.append(None)
    return repaired


# ---------------------------------------------------------------------------
# CLEANING HELPERS
# ---------------------------------------------------------------------------
def clean_dollar_series(series):
    cleaned = series.astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False)
    cleaned = cleaned.where(series.notna(), None)
    return pd.to_numeric(cleaned, errors='coerce')


def clean_zip_series(series):
    def _clean(val):
        if pd.isna(val):
            return None
        s = str(val).strip()
        if s == '':
            return None
        match = re.match(r'="?(\d{4,10}(-\d{4})?)"?', s)
        if match:
            s = match.group(1)
        if len(s) == 4 and s.isdigit():
            s = '0' + s
        return s
    return series.apply(_clean)


def parse_date_series(series):
    parsed = pd.to_datetime(series, errors='coerce', format='mixed')
    return parsed.dt.strftime('%Y-%m-%d')


def clean_text_series(series):
    """Strip leading/trailing whitespace and trailing comma/semicolon/colon."""
    def _clean(val):
        if pd.isna(val):
            return None
        s = str(val).strip()
        s = re.sub(r'[,;:]+$', '', s).strip()
        if s == '':
            return None
        return s
    return series.apply(_clean)


def clean_state_series(series):
    """Uppercase state codes and correct known bad values against the USPS list."""
    def _clean(val):
        if pd.isna(val):
            return None
        s = str(val).strip().upper()
        if s == '':
            return None
        if s in STATE_CORRECTIONS:
            return STATE_CORRECTIONS[s]
        return s
    return series.apply(_clean)


def safe_numeric(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def safe_int(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def nan_to_none(val):
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    return val


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def run():
    xl = pd.ExcelFile(input_file)

    clean_frames = []
    review_frames = []
    excluded_frames = []

    for sheet in xl.sheet_names:
        report_year = sheet.strip()
        df = pd.read_excel(xl, sheet_name=sheet, dtype=str)

        df['source_row_number'] = df.index + 2
        df['source_sheet'] = report_year

        overflow_cols = [c for c in df.columns if str(c).startswith('Unnamed:')]

        # --- Apply the general apostrophe-split repair row by row ---
        needs_repair_mask = df[RAW_COLUMNS].apply(
            lambda col: col.astype(str).str.startswith(CORRUPT_MARKER)
        ).any(axis=1)

        if needs_repair_mask.any():
            all_cols_for_repair = RAW_COLUMNS + overflow_cols
            for idx in df[needs_repair_mask].index:
                row_values = [df.at[idx, c] for c in all_cols_for_repair]
                repaired = repair_apostrophe_split(row_values)
                for col, val in zip(RAW_COLUMNS, repaired):
                    df.at[idx, col] = val
                for c in overflow_cols:
                    df.at[idx, c] = None

        # --- Apply confirmed row-specific patches ---
        for idx in df.index:
            key = (report_year, str(df.at[idx, 'source_row_number']))
            if key in ROW_PATCHES:
                for col, val in ROW_PATCHES[key].items():
                    df.at[idx, col] = val
                for c in overflow_cols:
                    df.at[idx, c] = None

        # --- Split off confirmed permanent exclusions ---
        keys = list(zip([report_year] * len(df), df['source_row_number'].astype(str)))
        is_excluded = pd.Series([k in EXCLUDED_ROWS for k in keys], index=df.index)

        excluded_df = df[is_excluded].copy()
        excluded_df['exclusion_reason'] = [EXCLUDED_ROWS[k] for k in keys if k in EXCLUDED_ROWS]
        excluded_frames.append(excluded_df)

        df = df[~is_excluded].copy()

        # --- Vectorized validation on everything remaining ---
        txn_id_valid = df['Transaction Id'].astype(str).str.strip().str.isdigit().fillna(False)

        txn_type_clean = df['Transaction Type'].astype(str).str.strip()
        txn_type_valid = txn_type_clean.isin(VALID_TRANSACTION_TYPES)

        parsed_dates = pd.to_datetime(df['Transaction Date'], errors='coerce', format='mixed')
        date_valid = parsed_dates.notna()

        amount_numeric = clean_dollar_series(df['Transaction Amount'])
        amount_required = txn_type_clean.isin(AMOUNT_REQUIRED_TYPES)
        amount_valid = (~amount_required) | amount_numeric.notna()

        if overflow_cols:
            has_overflow = df[overflow_cols].notna().any(axis=1)
        else:
            has_overflow = pd.Series([False] * len(df), index=df.index)

        row_valid = txn_id_valid & txn_type_valid & date_valid & amount_valid & (~has_overflow)

        reasons = pd.Series([''] * len(df), index=df.index)
        reasons = reasons.mask(~txn_id_valid, reasons + 'Transaction Id missing or not numeric; ')
        reasons = reasons.mask(~txn_type_valid, reasons + 'Transaction Type not recognized; ')
        reasons = reasons.mask(~date_valid, reasons + 'Transaction Date missing or unparseable; ')
        reasons = reasons.mask(~amount_valid, reasons + 'Transaction Amount missing or unparseable; ')
        reasons = reasons.mask(has_overflow, reasons + 'Row has data spilling past expected columns; ')

        review_df = df[~row_valid].copy()
        review_df['review_reason'] = reasons[~row_valid].str.rstrip('; ')
        review_frames.append(review_df)

        clean_df = df[row_valid].copy()

        for col in RAW_COLUMNS:
            clean_df[col] = clean_text_series(clean_df[col])

        clean_df['Contributor Address State'] = clean_state_series(clean_df['Contributor Address State'])

        for field in DOLLAR_FIELDS:
            clean_df[field] = clean_dollar_series(clean_df[field])

        clean_df['Contributor Address Zip Code'] = clean_zip_series(
            clean_df['Contributor Address Zip Code']
        )

        clean_df['Transaction Date'] = parse_date_series(clean_df['Transaction Date'])

        original_election_type = clean_df['Election Type'].copy()
        original_election_year = clean_df['Election Year'].copy()
        clean_df['Election Type'] = original_election_year
        clean_df['Election Year'] = original_election_type

        try:
            clean_df['report_year'] = int(report_year)
        except ValueError:
            clean_df['report_year'] = report_year

        if overflow_cols:
            clean_df = clean_df.drop(columns=overflow_cols)

        clean_frames.append(clean_df)

        print(f"{sheet!r}: {len(clean_df)} clean, {len(review_df)} flagged for review, "
              f"{len(excluded_df)} excluded")

    clean_combined = pd.concat(clean_frames, ignore_index=True) if clean_frames else pd.DataFrame()
    review_combined = pd.concat(review_frames, ignore_index=True) if review_frames else pd.DataFrame()
    excluded_combined = pd.concat(excluded_frames, ignore_index=True) if excluded_frames else pd.DataFrame()

    if os.path.exists(output_file):
        os.remove(output_file)

    print("Writing clean output file...")
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        clean_combined.to_excel(writer, sheet_name='Clean Data', index=False)
        review_combined.to_excel(writer, sheet_name='Needs Manual Review', index=False)
        excluded_combined.to_excel(writer, sheet_name='Excluded Incomplete Records', index=False)

    print(f"Done. {len(clean_combined)} clean rows, {len(review_combined)} need manual review, "
          f"{len(excluded_combined)} excluded.")
    print(f"Output written to: {output_file}")

    # -----------------------------------------------------------------------
    # LOAD TO POSTGRESQL
    # -----------------------------------------------------------------------
    print("Connecting to PostgreSQL...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    print("Dropping and recreating funding_live_2023_current table...")
    cur.execute("DROP TABLE IF EXISTS funding_live_2023_current;")
    cur.execute("""
    CREATE TABLE funding_live_2023_current (
        filing_entity_id VARCHAR,
        filing_entity_name VARCHAR,
        campaign_name VARCHAR,
        registration_type VARCHAR,
        transaction_id INTEGER,
        transaction_type VARCHAR,
        transaction_sub_type VARCHAR,
        contributor_type VARCHAR,
        contributor_last_name VARCHAR,
        contributor_first_name VARCHAR,
        contributor_company_name VARCHAR,
        contributor_address_line1 VARCHAR,
        contributor_address_line2 VARCHAR,
        contributor_address_city VARCHAR,
        contributor_address_state VARCHAR,
        contributor_address_zip_code VARCHAR,
        transaction_date DATE,
        transaction_amount NUMERIC,
        loan_interest_amount NUMERIC,
        total_loan_amount NUMERIC,
        election_type VARCHAR,
        election_year VARCHAR,
        transaction_description VARCHAR,
        amended VARCHAR,
        timed_report_name VARCHAR,
        timed_report_date VARCHAR,
        report_name VARCHAR,
        report_filed_date VARCHAR,
        source_row_number INTEGER,
        source_sheet VARCHAR,
        report_year INTEGER
    );
    """)
    conn.commit()

    INSERT_SQL = """
    INSERT INTO funding_live_2023_current (
        filing_entity_id, filing_entity_name, campaign_name, registration_type,
        transaction_id, transaction_type, transaction_sub_type, contributor_type,
        contributor_last_name, contributor_first_name, contributor_company_name,
        contributor_address_line1, contributor_address_line2, contributor_address_city,
        contributor_address_state, contributor_address_zip_code, transaction_date,
        transaction_amount, loan_interest_amount, total_loan_amount, election_type,
        election_year, transaction_description, amended, timed_report_name,
        timed_report_date, report_name, report_filed_date, source_row_number,
        source_sheet, report_year
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    """

    total = 0
    for _, row in clean_combined.iterrows():
        cur.execute(INSERT_SQL, (
            nan_to_none(row.get('Filing Entity ID')), nan_to_none(row.get('Filing Entity Name')),
            nan_to_none(row.get('Campaign Name')), nan_to_none(row.get('Registration Type')),
            safe_int(row.get('Transaction Id')), nan_to_none(row.get('Transaction Type')),
            nan_to_none(row.get('Transaction Sub Type')), nan_to_none(row.get('Contributor Type')),
            nan_to_none(row.get('Contributor Last Name')), nan_to_none(row.get('Contributor First Name')),
            nan_to_none(row.get('Contributor Company Name')), nan_to_none(row.get('Contributor Address Line 1')),
            nan_to_none(row.get('Contributor Address Line 2')), nan_to_none(row.get('Contributor Address City')),
            nan_to_none(row.get('Contributor Address State')), nan_to_none(row.get('Contributor Address Zip Code')),
            nan_to_none(row.get('Transaction Date')), safe_numeric(row.get('Transaction Amount')),
            safe_numeric(row.get('Loan Interest Amount')), safe_numeric(row.get('Total Loan Amount')),
            nan_to_none(row.get('Election Type')), nan_to_none(row.get('Election Year')),
            nan_to_none(row.get('Transaction Description')), nan_to_none(row.get('Amended')),
            nan_to_none(row.get('Timed Report Name')), nan_to_none(row.get('Timed Report Date')),
            nan_to_none(row.get('Report Name')), nan_to_none(row.get('Report Filed Date')),
            safe_int(row.get('source_row_number')), nan_to_none(row.get('source_sheet')),
            safe_int(row.get('report_year'))
        ))
        total += 1
        if total % 5000 == 0:
            conn.commit()
            print(f"  {total} rows committed...")

    conn.commit()
    cur.close()
    conn.close()
    print(f"Done. {total} rows loaded into funding_live_2023_current.")


if __name__ == '__main__':
    run()