import pandas as pd
import re

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

writer = pd.ExcelWriter(output_file, engine='openpyxl')
xl = pd.ExcelFile(input_file)

for sheet in xl.sheet_names:
    df = pd.read_excel(input_file, sheet_name=sheet, dtype={'ContributorZipcode': str})

    # Fix Ann Vegors party from UNI to REF before party map runs
    mask = (
        (df['CandLast'].str.strip().str.lower() == 'vegors') &
        (df['CandFirst'].str.strip().str.lower() == 'ann') &
        (df['Party'] == 'UNI')
    )
    df.loc[mask, 'Party'] = 'REF'

    # Global trim of all string columns
    str_cols = df.select_dtypes(include=['object', 'str']).columns
    for col in str_cols:
        df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)

    # Election year and type
    df['ElectionYear'] = df['ElectionYear'].fillna(int(sheet))
    df['Election'] = df['Election'].replace(election_map)
    df['Election'] = df['Election'].fillna('Unknown')

    # Party standardization
    df['Party'] = df['Party'].replace(party_map)

    # Contributor Type
    df['Contributor Type'] = df.apply(get_contributor_type, axis=1)
    df = df.drop(columns=['ContrCP'])

    # Transaction Type and Sub Type
    df['Transaction Type'] = df.apply(get_transaction_type, axis=1)
    df['Transaction Sub Type'] = df.apply(get_transaction_subtype, axis=1)
    df = df.drop(columns=['ContrType'])

    # Standardize date format to YYYY-MM-DD
    df['ContrDate'] = pd.to_datetime(df['ContrDate'], errors='coerce').dt.strftime('%Y-%m-%d')

    # Clean zip codes to 5 digits, zero pad 4 digit zips, null out invalid entries
    df['ContributorZipcode'] = df['ContributorZipcode'].apply(clean_zip)

    df.to_excel(writer, sheet_name=sheet, index=False)

writer.close()
print("Done. Cleaned file saved.")