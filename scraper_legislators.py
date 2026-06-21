import requests
from bs4 import BeautifulSoup
import psycopg2
import os
from dotenv import load_dotenv
import re
from datetime import datetime

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

URLS = {
    'House': 'https://legislature.idaho.gov/house/membership/',
    'Senate': 'https://legislature.idaho.gov/senate/membership/'
}

def parse_term_number(text):
    match = re.search(r'(\d+)', text)
    return int(match.group(1)) if match else None

def parse_district_number(text):
    match = re.search(r'(\d+)', text)
    return int(match.group(1)) if match else None

def scrape_members(url, chamber):
    print(f"Fetching {chamber} page...")
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    email_to_bio = {}
    for table in soup.find_all('table'):
        table_text = table.get_text(strip=True)
        email_match = re.search(r'[\w\.-]+@(?:house|senate)\.idaho\.gov', table_text)
        if email_match:
            email = email_match.group(0).lower()
            email_to_bio[email] = table_text

    members = []
    seen_names = set()

    for strong in soup.find_all('strong'):
        next_text = strong.next_sibling
        if not next_text:
            continue

        next_str = str(next_text).strip()
        if not re.match(r'^\([RD]\)', next_str):
            continue

        name_text = strong.get_text(strip=True).replace('\xa0', ' ').strip()
        if not name_text or name_text in seen_names:
            continue
        seen_names.add(name_text)

        member = {}
        member['full_name'] = name_text
        member['chamber'] = chamber
        member['party_affiliation'] = 'Republican' if '(R)' in next_str else 'Democrat'

        data_p = strong.find_parent('p')
        if not data_p:
            continue

        bio_text = None
        email_tag = data_p.find('a', href=re.compile(r'mailto:'))
        if email_tag:
            email = email_tag.get_text(strip=True).lower()
            raw_bio = email_to_bio.get(email, '')
            if raw_bio:
                bio_text = re.sub(re.escape(email), '', raw_bio, count=1, flags=re.IGNORECASE).strip()
        member['bio_text'] = bio_text if bio_text else None

        raw_html = str(data_p)
        raw_html_clean = re.sub(r'<sup>[^<]+</sup>', '', raw_html)
        data_p_clean = BeautifulSoup(raw_html_clean, 'html.parser')

        full_text = data_p_clean.get_text(separator='\n', strip=True)
        lines = [l.strip() for l in full_text.split('\n') if l.strip()]

        district_line = next((l for l in lines if l.startswith('District')), None)
        member['district_number'] = parse_district_number(district_line) if district_line else None

        term_line = next((l for l in lines if re.search(r'\d+\s*term', l, re.IGNORECASE)), None)
        member['total_terms'] = parse_term_number(term_line) if term_line else None

        seat_line = next((l for l in lines if 'Seat' in l), None)
        if seat_line:
            seat_match = re.search(r'Seat\s([AB])', seat_line)
            member['seat_designation'] = seat_match.group(1) if seat_match else None
        else:
            member['seat_designation'] = None

        skip_labels = ['home', 'statehouse', 'fax', 'committees', 'subscribe', 'view', 'session only']
        occupation = None
        found_phone = False
        for line in lines:
            line_lower = line.lower()
            if re.search(r'\(\d{3}\)', line) or any(label in line_lower for label in ['home', 'statehouse', 'fax']):
                found_phone = True
            elif found_phone:
                if not any(label in line_lower for label in skip_labels):
                    if not re.search(r'\d{3}-\d{4}', line) and len(line) < 150:
                        occupation = line
                        break
        member['occupation'] = occupation

        data_col = data_p.find_parent('div', class_=re.compile('vc_column_container'))
        if data_col:
            prev_col = data_col.find_previous_sibling('div')
            if prev_col:
                img = prev_col.find('img', src=re.compile(r'/directory/'))
                member['headshot_url'] = 'https://legislature.idaho.gov' + img.get('src', '') if img else None
            else:
                member['headshot_url'] = None
        else:
            member['headshot_url'] = None

        current_year = datetime.now().year
        if current_year % 2 == 0:
            member['next_election_year'] = current_year
        else:
            member['next_election_year'] = current_year + 1

        members.append(member)

    return members

def insert_members(members):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    processed = 0
    for m in members:
        cur.execute("""
            INSERT INTO legislators (
                full_name, chamber, district_number, party_affiliation,
                total_terms, next_election_year, headshot_url,
                occupation, seat_designation, bio_text, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (full_name) DO UPDATE SET
                chamber = EXCLUDED.chamber,
                district_number = EXCLUDED.district_number,
                party_affiliation = EXCLUDED.party_affiliation,
                total_terms = EXCLUDED.total_terms,
                next_election_year = EXCLUDED.next_election_year,
                headshot_url = EXCLUDED.headshot_url,
                occupation = EXCLUDED.occupation,
                seat_designation = EXCLUDED.seat_designation,
                bio_text = EXCLUDED.bio_text,
                updated_at = NOW()
        """, (
            m.get('full_name'),
            m.get('chamber'),
            m.get('district_number'),
            m.get('party_affiliation'),
            m.get('total_terms'),
            m.get('next_election_year'),
            m.get('headshot_url'),
            m.get('occupation'),
            m.get('seat_designation'),
            m.get('bio_text')
        ))
        processed += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"Successfully processed {processed} legislators (existing members updated, new members inserted)")

if __name__ == '__main__':
    all_members = []
    for chamber, url in URLS.items():
        members = scrape_members(url, chamber)
        print(f"Found {len(members)} {chamber} members")
        all_members.extend(members)

    print(f"Total legislators found: {len(all_members)}")
    insert_members(all_members)
    print("Done!")