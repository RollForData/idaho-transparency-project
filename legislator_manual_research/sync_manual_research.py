import csv
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

CSV_FILE = 'legislator_manual_research/legislator_manual_research.csv'

def parse_boolean(value):
    if not value:
        return None
    value = value.strip().lower()
    if value == 'yes':
        return True
    elif value == 'no':
        return False
    return None

def parse_int(value):
    if not value or not value.strip():
        return None
    try:
        return int(value.strip())
    except ValueError:
        return None

def clean_text(value):
    if not value:
        return None
    cleaned = value.strip()
    return cleaned if cleaned else None

def load_research_data():
    rows = []
    with open(CSV_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                'legislator_id': parse_int(row.get('id')),
                'birth_year': parse_int(row.get('birth_year')),
                'birth_year_source': clean_text(row.get('birth_year_source')),
                'birthplace': clean_text(row.get('birthplace')),
                'birthplace_source': clean_text(row.get('birthplace_source')),
                'gender': clean_text(row.get('gender')),
                'faith_referenced_in_platform': parse_boolean(row.get('faith_ref_in_platform')),
                'denomination': clean_text(row.get('denomination')),
                'religion_source': clean_text(row.get('religion_source')),
                'wikipedia_url': clean_text(row.get('wikipedia_url')),
            })
    return rows

def sync_to_database(rows):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("DELETE FROM legislator_manual_research;")

    inserted = 0
    skipped = 0
    for r in rows:
        if not r['legislator_id']:
            skipped += 1
            continue

        cur.execute("""
            INSERT INTO legislator_manual_research (
                legislator_id, birth_year, birth_year_source,
                birthplace, birthplace_source, gender,
                faith_referenced_in_platform, denomination,
                religion_source, wikipedia_url, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            r['legislator_id'],
            r['birth_year'],
            r['birth_year_source'],
            r['birthplace'],
            r['birthplace_source'],
            r['gender'],
            r['faith_referenced_in_platform'],
            r['denomination'],
            r['religion_source'],
            r['wikipedia_url']
        ))
        inserted += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"Synced {inserted} rows into legislator_manual_research")
    if skipped:
        print(f"Skipped {skipped} rows with no legislator_id")

if __name__ == '__main__':
    rows = load_research_data()
    print(f"Loaded {len(rows)} rows from {CSV_FILE}")
    sync_to_database(rows)
    print("Done!")