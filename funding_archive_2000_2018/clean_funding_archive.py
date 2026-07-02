import pandas as pd
import re
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

input_file = r"C:\Users\cathe\Documents\idaho-transparency-project\funding_archive_2000_2018\funding_data_archive_2000_2018.xlsx"
output_file = r"C:\Users\cathe\Documents\idaho-transparency-project\funding_archive_2000_2018\funding_data_archive_2000_2018_cleaned.xlsx"

party_map = {
    'REP': 'Republican',
    'DEM': 'Democratic',
    'LIB': 'Libertarian',
    'CON': 'Constitution',
    'IND': 'Independent',
    'NON': 'Non-Partisan',
    'NAT': 'Natural Law',
    'REF': 'Reform',
    'UNI': 'Reform',
    'UNK': 'Unknown',
    'Non-partisan': 'Non-Partisan'
}

election_map = {
    'G': 'General',
    'P': 'Primary',
    'g': 'General',
    'p': 'Primary'
}

numeric_state_map = {
    '10': 'ID',
    '11': 'NY',
    '83': 'ID',
    '8': 'ID',
    '55': 'ID',
    '50': 'ID'
}

valid_usps_abbreviations = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
    'DC', 'AS', 'GU', 'MP', 'PR', 'VI',
    'AA', 'AE', 'AP'
}

def strip_trailing_punctuation(val):
    if isinstance(val, str):
        return re.sub(r'[,;:]+$', '', val).strip()
    return val

def clean_state(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    val = str(val).strip()
    if val == '':
        return None
    if val == 'Ae':
        return 'AE'
    if val in numeric_state_map:
        return numeric_state_map[val]
    if val.upper() in valid_usps_abbreviations:
        return val.upper()
    return val

def clean_city(val):
    if not isinstance(val, str):
        return val
    city_fixes = {
        'Spokane,': 'Spokane',
        'Cranbury,': 'Cranbury',
        'Milwaukee,': 'Milwaukee'
    }
    val = val.strip()
    if val in city_fixes:
        return city_fixes[val]
    return val

def clean_zip(val):
    if val is None or val == 'nan' or val == '':
        return None
    val = str(val).strip()
    if val.startswith('*'):
        return None
    val = val.split('.')[0]
    if len(val) == 4 and val.isdigit():
        val = '0' + val
    match = re.match(r'(\d{5})', val)
    if match:
        return match.group(1)
    return None

def get_transaction_type(row):
    amount = row['ContrAmount']
    contr_type = str(row['ContrType']).strip() if pd.notna(row['ContrType']) else ''
    if amount < 0:
        return 'Returned Contribution'
    if contr_type in ['L', 'Loan']:
        return 'Loan'
    return 'Contribution'

def get_transaction_subtype(row):
    amount = row['ContrAmount']
    contr_type = str(row['ContrType']).strip() if pd.notna(row['ContrType']) else ''
    if amount < 0:
        if contr_type in ['L', 'Loan']:
            return 'Loan Repayment'
        return 'Returned Contribution'
    if contr_type in ['I', 'In Kind']:
        return 'In-Kind'
    if contr_type in ['L', 'Loan']:
        return 'Loan'
    return 'Itemized'

def get_contributor_type(row):
    cand_last = str(row['CandLast']).strip().lower() if pd.notna(row['CandLast']) else ''
    cand_first = str(row['CandFirst']).strip().lower() if pd.notna(row['CandFirst']) else ''
    contr_last = str(row['ContrLast']).strip().lower() if pd.notna(row['ContrLast']) else ''
    contr_first = str(row['ContrFirst']).strip().lower() if pd.notna(row['ContrFirst']) else ''
    current_cp = str(row['ContrCP']).strip() if pd.notna(row['ContrCP']) else ''
    if cand_last == contr_last and cand_first == contr_first and cand_last != '':
        return 'Self'
    return current_cp.strip()

def check_date_discrepancy(contr_date, tab_year):
    if contr_date is None or contr_date == '':
        return None
    try:
        contr_year = pd.to_datetime(contr_date).year
        if abs(contr_year - int(tab_year)) > 2:
            return 'ContrDate falls more than 2 years outside of report year'
        return None
    except:
        return None

def safe_int(val):
    try:
        if pd.isna(val):
            return None
        return int(val)
    except:
        return None

def nan_to_none(val):
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except:
        pass
    return val

xl = pd.ExcelFile(input_file)
all_frames = []

for sheet in xl.sheet_names:
    df = pd.read_excel(input_file, sheet_name=sheet, dtype={'ContributorZipcode': str})

    str_cols = df.select_dtypes(include=['object', 'str']).columns
    for col in str_cols:
        df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)

    for col in str_cols:
        df[col] = df[col].apply(strip_trailing_punctuation)

    df['ContributorCity'] = df['ContributorCity'].apply(clean_city)
    df['ContributorState'] = df['ContributorState'].apply(clean_state)
    df['report_year'] = int(sheet)
    df['ElectionYear'] = pd.to_numeric(df['ElectionYear'], errors='coerce')
    df['Election'] = df['Election'].replace(election_map)
    df['Election'] = df['Election'].apply(lambda x: x if x in ['General', 'Primary'] else None)
    df['Party'] = df['Party'].replace(party_map)
    df['Contributor Type'] = df.apply(get_contributor_type, axis=1)
    df = df.drop(columns=['ContrCP'])
    df['Transaction Type'] = df.apply(get_transaction_type, axis=1)
    df['Transaction Sub Type'] = df.apply(get_transaction_subtype, axis=1)
    df = df.drop(columns=['ContrType'])
    df['ContrDate'] = pd.to_datetime(df['ContrDate'], errors='coerce').dt.strftime('%Y-%m-%d')
    df['ContrDateDiscrepancy'] = df.apply(
        lambda row: check_date_discrepancy(row['ContrDate'], sheet), axis=1
    )
    df['ContributorZipcode'] = df['ContributorZipcode'].apply(clean_zip)

    all_frames.append(df)

combined = pd.concat(all_frames, ignore_index=True)

# Replace all NaN/NaT with None so PostgreSQL gets true NULLs, not the string 'NaN'
combined = combined.where(pd.notna(combined), other=None)

# Write to single-sheet Excel
print("Saving cleaned Excel file...")
with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    combined.to_excel(writer, sheet_name='funding_archive_2000_2018', index=False)
print("Cleaned Excel file saved.")

# Load to PostgreSQL
conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

print("Dropping and recreating funding_archive_2000_2018 table...")
cur.execute("DROP TABLE IF EXISTS funding_archive_2000_2018;")
cur.execute("""
CREATE TABLE funding_archive_2000_2018 (
    report_year INTEGER,
    cand_last VARCHAR,
    cand_suf VARCHAR,
    cand_first VARCHAR,
    cand_mid VARCHAR,
    party VARCHAR,
    office VARCHAR,
    district VARCHAR,
    contr_date VARCHAR,
    contr_amount NUMERIC,
    contr_last VARCHAR,
    contr_suf VARCHAR,
    contr_first VARCHAR,
    contr_mid VARCHAR,
    contr_mailing_address1 VARCHAR,
    contr_mailing_address2 VARCHAR,
    contributor_city VARCHAR,
    contributor_state VARCHAR,
    contributor_zipcode VARCHAR,
    contributor_country VARCHAR,
    election VARCHAR,
    election_year INTEGER,
    contributor_type VARCHAR,
    transaction_type VARCHAR,
    transaction_sub_type VARCHAR,
    contr_date_discrepancy VARCHAR
);
""")
conn.commit()

INSERT_SQL = """
INSERT INTO funding_archive_2000_2018 (
    report_year, cand_last, cand_suf, cand_first, cand_mid, party, office, district,
    contr_date, contr_amount, contr_last, contr_suf, contr_first, contr_mid,
    contr_mailing_address1, contr_mailing_address2, contributor_city, contributor_state,
    contributor_zipcode, contributor_country, election, election_year,
    contributor_type, transaction_type, transaction_sub_type, contr_date_discrepancy
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s, %s, %s
)
"""

total = 0
for _, row in combined.iterrows():
    try:
        cur.execute(INSERT_SQL, (
            safe_int(row.get('report_year')),
            nan_to_none(row.get('CandLast')), nan_to_none(row.get('CandSuf')),
            nan_to_none(row.get('CandFirst')), nan_to_none(row.get('CandMid')),
            nan_to_none(row.get('Party')), nan_to_none(row.get('Office')),
            nan_to_none(row.get('District')), nan_to_none(row.get('ContrDate')),
            nan_to_none(row.get('ContrAmount')), nan_to_none(row.get('ContrLast')),
            nan_to_none(row.get('ContrSuf')), nan_to_none(row.get('ContrFirst')),
            nan_to_none(row.get('ContrMid')), nan_to_none(row.get('ContrMailingAddress1')),
            nan_to_none(row.get('ContrMailingAddress2')), nan_to_none(row.get('ContributorCity')),
            nan_to_none(row.get('ContributorState')), nan_to_none(row.get('ContributorZipcode')),
            nan_to_none(row.get('ContributorCountry')), nan_to_none(row.get('Election')),
            safe_int(row.get('ElectionYear')), nan_to_none(row.get('Contributor Type')),
            nan_to_none(row.get('Transaction Type')), nan_to_none(row.get('Transaction Sub Type')),
            nan_to_none(row.get('ContrDateDiscrepancy'))
        ))
        total += 1
    except Exception as e:
        print(f"Error on row index {_}: {e}")
        print(row.to_dict())
        break

conn.commit()
cur.close()
conn.close()
print(f"Done. {total} rows loaded into funding_archive_2000_2018.")