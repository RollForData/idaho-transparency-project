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

        # Get raw HTML of paragraph to handle superscript term numbers
        raw_html = str(data_p)

        # Fix superscript term number: "2<sup>nd</sup> term" becomes "2nd term"
        raw_html_clean = re.sub(r'<sup>[^<]+</sup>', '', raw_html)
        data_p_clean = BeautifulSoup(raw_html_clean, 'html.parser')

        full_text = data_p_clean.get_text(separator='\n', strip=True)
        lines = [l.strip() for l in full_text.split('\n') if l.strip()]

        # Extract district number
        district_line = next((l for l in lines if l.startswith('District')), None)
        member['district_number'] = parse_district_number(district_line) if district_line else None

        # Extract term number
        term_line = next((l for l in lines if re.search(r'\d+\s*term', l, re.IGNORECASE)), None)
        member['total_terms'] = parse_term_number(term_line) if term_line else None

        # Extract seat designation
        seat_line = next((l for l in lines if 'Seat' in l), None)
        if seat_line:
            seat_match = re.search(r'Seat\s([AB])', seat_line)
            member['seat_designation'] = seat_match.group(1) if seat_match else None
        else:
            member['seat_designation'] = None

        # Extract occupation
        # Skip known non-occupation labels
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

        # Find headshot image in the sibling column
        # Navigate up to find the column container, then look at previous sibling column
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

        member['gender'] = None
        member['age'] = None
        member['race_ethnicity'] = None
        member['years_registered_idaho'] = None
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

    inserted = 0
    for m in members:
        cur.execute("""
            INSERT INTO legislators (
                full_name, chamber, district_number, party_affiliation,
                total_terms, next_election_year, years_registered_idaho,
                age, race_ethnicity, gender, headshot_url, occupation,
                seat_designation
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            m.get('full_name'),
            m.get('chamber'),
            m.get('district_number'),
            m.get('party_affiliation'),
            m.get('total_terms'),
            m.get('next_election_year'),
            m.get('years_registered_idaho'),
            m.get('age'),
            m.get('race_ethnicity'),
            m.get('gender'),
            m.get('headshot_url'),
            m.get('occupation'),
            m.get('seat_designation')
        ))
        inserted += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"Successfully inserted {inserted} legislators into the database")

if __name__ == '__main__':
    all_members = []
    for chamber, url in URLS.items():
        members = scrape_members(url, chamber)
        print(f"Found {len(members)} {chamber} members")
        all_members.extend(members)

    print(f"Total legislators found: {len(all_members)}")
    insert_members(all_members)
    print("Done!")