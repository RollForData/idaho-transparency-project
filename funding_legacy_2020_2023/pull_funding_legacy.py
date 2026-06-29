import requests
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

API_URL = 'https://canvass.sos.idaho.gov/eng/finances/get_activity.json'

PAYLOAD = {
    "activity_types": {"donate": 1, "spend": 0, "file": 0},
    "amounts": [1, 1000000],
    "campaigns": [],
    "ch": ["summary"],
    "ch_data": [],
    "committee_types": [],
    "contest_years": [2019, 2026],
    "dates": ["2020-01-01T07:00:00.000Z", "2027-01-01T07:00:00.000Z"],
    "districts": [],
    "donate_types": [],
    "donors": [],
    "get_link_to_result": 0,
    "limit": 1000,
    "offices": [],
    "order": "date desc",
    "page": 1,
    "parties": [],
    "report_types": [],
    "reports": [],
    "spend_codes": [],
    "spend_types": [],
    "stages": [],
    "treasurers": [],
    "vendors": []
}

CREATE_TABLE_SQL = """
DROP TABLE IF EXISTS funding_legacy_2020_2023;
CREATE TABLE funding_legacy_2020_2023 (
    id VARCHAR,
    date TIMESTAMP,
    amount NUMERIC,
    donate_type VARCHAR,
    donate_count VARCHAR,
    elec_year VARCHAR,
    elec_stage VARCHAR,
    from_pk_id VARCHAR,
    from_display_name VARCHAR,
    from_entity_type VARCHAR,
    from_address VARCHAR,
    from_city VARCHAR,
    from_state VARCHAR,
    from_zip VARCHAR,
    from_is_dupe VARCHAR,
    to_pk_id VARCHAR,
    to_display_name VARCHAR,
    to_entity_type VARCHAR,
    to_address VARCHAR,
    to_city VARCHAR,
    to_state VARCHAR,
    to_zip VARCHAR,
    to_office_id VARCHAR,
    to_office_name VARCHAR,
    to_district_name VARCHAR,
    to_party_code VARCHAR,
    to_treasurer_id VARCHAR,
    to_treasurer_name VARCHAR,
    to_reg_district VARCHAR,
    to_status VARCHAR,
    report_id VARCHAR,
    report_code VARCHAR,
    report_name VARCHAR,
    report_status VARCHAR,
    report_submit_date TIMESTAMP,
    report_due_date TIMESTAMP,
    report2_id VARCHAR,
    report2_code VARCHAR,
    report2_name VARCHAR,
    report2_status VARCHAR,
    report2_submit_date TIMESTAMP,
    report2_due_date TIMESTAMP
);
"""

INSERT_SQL = """
INSERT INTO funding_legacy_2020_2023 (
    id, date, amount, donate_type, donate_count, elec_year, elec_stage,
    from_pk_id, from_display_name, from_entity_type, from_address, from_city,
    from_state, from_zip, from_is_dupe, to_pk_id, to_display_name, to_entity_type,
    to_address, to_city, to_state, to_zip, to_office_id, to_office_name,
    to_district_name, to_party_code, to_treasurer_id, to_treasurer_name,
    to_reg_district, to_status, report_id, report_code, report_name, report_status,
    report_submit_date, report_due_date, report2_id, report2_code, report2_name,
    report2_status, report2_submit_date, report2_due_date
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s
)
"""

def safe(record, key):
    val = record.get(key)
    if val == '' or val == ' ':
        return None
    return val

def fetch_page(page):
    payload = {**PAYLOAD, 'page': page}
    response = requests.post(API_URL, json=payload)
    response.raise_for_status()
    return response.json().get('output', [])

def run():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    print("Creating table...")
    cur.execute(CREATE_TABLE_SQL)
    conn.commit()

    page = 1
    total_inserted = 0

    while True:
        print(f"Fetching page {page}...")
        records = fetch_page(page)

        if not records:
            print("No more records. Done.")
            break

        for r in records:
            cur.execute(INSERT_SQL, (
                safe(r, 'id'), safe(r, 'date'), safe(r, 'amount'),
                safe(r, 'donate_type'), safe(r, 'donate_count'),
                safe(r, 'elec_year'), safe(r, 'elec_stage'),
                safe(r, 'from_pk_id'), safe(r, 'from_display_name'),
                safe(r, 'from_entity_type'), safe(r, 'from_address'),
                safe(r, 'from_city'), safe(r, 'from_state'), safe(r, 'from_zip'),
                safe(r, 'from_is_dupe'), safe(r, 'to_pk_id'),
                safe(r, 'to_display_name'), safe(r, 'to_entity_type'),
                safe(r, 'to_address'), safe(r, 'to_city'), safe(r, 'to_state'),
                safe(r, 'to_zip'), safe(r, 'to_office_id'), safe(r, 'to_office_name'),
                safe(r, 'to_district_name'), safe(r, 'to_party_code'),
                safe(r, 'to_treasurer_id'), safe(r, 'to_treasurer_name'),
                safe(r, 'to_reg_district'), safe(r, 'to_status'),
                safe(r, 'report_id'), safe(r, 'report_code'), safe(r, 'report_name'),
                safe(r, 'report_status'), safe(r, 'report_submit_date'),
                safe(r, 'report_due_date'), safe(r, 'report2_id'),
                safe(r, 'report2_code'), safe(r, 'report2_name'),
                safe(r, 'report2_status'), safe(r, 'report2_submit_date'),
                safe(r, 'report2_due_date')
            ))

        conn.commit()
        total_inserted += len(records)
        print(f"Page {page} done. Total inserted so far: {total_inserted}")

        if len(records) < 1000:
            print("Last page reached.")
            break

        page += 1

    cur.close()
    conn.close()
    print(f"Complete. Total records inserted: {total_inserted}")

if __name__ == '__main__':
    run()