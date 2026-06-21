import csv
import re
import time
import psycopg2
import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from ddgs import DDGS

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

HEADERS = {'User-Agent': 'IdahoTransparencyProject/1.0 (civic research; github.com/RollForData)'}

def get_legislators_from_db():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT id, full_name, chamber FROM legislators ORDER BY chamber, full_name")
    results = cur.fetchall()
    cur.close()
    conn.close()
    return results

def clean_name(name):
    name = re.sub(r'["\u201c\u201d][^""\u201c\u201d]*["\u201c\u201d]', '', name)
    name = re.sub(r'\b[A-Z]\.\s*', '', name)
    name = ' '.join(name.split())
    return name.strip()

def extract_birth_year(text):
    patterns = [
        r'\(born\s+\w+\s+\d+,\s+(\d{4})\)',
        r'[Bb]orn\s+\w+\s+\d+,\s+(\d{4})',
        r'[Bb]orn\s*:?\s*\w+\s+\d+,\s+(\d{4})',
        r'\(born\s+(\d{4})\)',
        r'[Bb]orn\s+(\d{4})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            year_match = re.search(r'\b(19[3-9]\d|20[0-2]\d)\b', match.group(0))
            if year_match:
                return year_match.group(1)
    return None

def extract_birthplace(text):
    us_states = [
        'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado',
        'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho',
        'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana',
        'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota',
        'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada',
        'New Hampshire', 'New Jersey', 'New Mexico', 'New York',
        'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon',
        'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota',
        'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington',
        'West Virginia', 'Wisconsin', 'Wyoming'
    ]

    # Look specifically for location after "in" following birth date
    # Pattern: "born Month Day, Year, in City, State" or "born in City, State"
    patterns = [
        r'[Bb]orn\s+\w+\s+\d+,\s+\d{4},?\s+in\s+([^,\(\)\n]+,\s*[A-Z][a-z]+)',
        r'[Bb]orn\s+\w+\s+\d+,\s+\d{4},?\s+in\s+([^,\(\)\n]+)',
        r'[Bb]orn\s+in\s+([^,\(\)\n]+,\s*[A-Z][a-z]+)',
        r'[Bb]orn\s+in\s+([^,\(\)\n]+)',
        r'[Bb]irthplace\s*:?\s*([^\n]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            location = match.group(1).strip()
            # Skip if it looks like a date
            if re.match(r'^(January|February|March|April|May|June|July|August|September|October|November|December)', location):
                continue
            # Check for US state
            for state in us_states:
                if state.lower() in location.lower():
                    return state
            # Return raw location if reasonable length
            if 3 < len(location) < 60:
                return location

    return None

def extract_gender(text):
    gender_match = re.search(r'[Gg]ender\s*:?\s*(Male|Female|male|female)', text)
    if gender_match:
        return gender_match.group(1).capitalize()
    sample = text[:3000]
    he_count = len(re.findall(r'\bhe\b|\bhis\b|\bhim\b', sample, re.IGNORECASE))
    she_count = len(re.findall(r'\bshe\b|\bher\b|\bhers\b', sample, re.IGNORECASE))
    if he_count > she_count and he_count > 2:
        return 'Male'
    elif she_count > he_count and she_count > 2:
        return 'Female'
    return None

def extract_religion(text):
    patterns = [
        r'[Rr]eligion\s*:?\s*([^\n]{3,80}?)(?:\n|Personal|Political|Education|Profession|Contact)',
        r'[Rr]eligion\s*:?\s*([^\n]{3,80})',
        r'[Rr]eligious\s+[Vv]iews?\s*:?\s*([^\n]{3,80})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            religion = match.group(1).strip()
            if 2 < len(religion) < 80:
                return religion
    return None

def extract_official_website(soup):
    # Check infobox for website field
    website_labels = soup.find_all('th', string=re.compile(r'[Ww]ebsite'))
    for label in website_labels:
        td = label.find_next_sibling('td')
        if td:
            link = td.find('a')
            if link and link.get('href'):
                href = link.get('href')
                if href.startswith('http'):
                    return href

    # Check external links section
    ext_links_header = soup.find('span', id='External_links')
    if ext_links_header:
        ul = ext_links_header.find_next('ul')
        if ul:
            for li in ul.find_all('li'):
                text = li.get_text().lower()
                if 'official' in text or 'website' in text or 'campaign' in text:
                    link = li.find('a')
                    if link and link.get('href', '').startswith('http'):
                        return link.get('href')

    return None

def search_and_analyze(leg_id, full_name, chamber):
    result = {
        'id': leg_id,
        'full_name': full_name,
        'chamber': chamber,
        'has_page': False,
        'wikipedia_url': '',
        'official_website': '',
        'birth_year': '',
        'birthplace': '',
        'gender': '',
        'religion': '',
        'notes': ''
    }

    clean = clean_name(full_name)

    try:
        query = f"{clean} Idaho politician wikipedia"
        search_results = DDGS().text(query, max_results=5)

        wiki_url = None
        snippet_text = ''

        for r in search_results:
            url = r.get('href', '')
            if 'en.wikipedia.org/wiki/' in url:
                wiki_url = url
                snippet_text = r.get('body', '')
                break

        if not wiki_url:
            result['notes'] = 'No Wikipedia page found'
            return result

        result['wikipedia_url'] = wiki_url

        # Try birth year from snippet first
        birth_year = extract_birth_year(snippet_text)
        if birth_year:
            result['birth_year'] = birth_year

        # Fetch full Wikipedia page
        time.sleep(1)
        response = requests.get(wiki_url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            result['notes'] = f'Page fetch failed: {response.status_code}'
            return result

        soup = BeautifulSoup(response.content, 'html.parser')
        full_text = soup.get_text()

        # Verify correct person
        last_name = clean.lower().split()[-1]
        if last_name not in full_text.lower()[:2000]:
            result['notes'] = 'Page found but may be wrong person'
            return result

        result['has_page'] = True

        # Extract all fields
        if not result['birth_year']:
            birth_year = extract_birth_year(full_text)
            if birth_year:
                result['birth_year'] = birth_year

        birthplace = extract_birthplace(full_text)
        if birthplace:
            result['birthplace'] = birthplace

        gender = extract_gender(full_text)
        if gender:
            result['gender'] = gender

        religion = extract_religion(full_text)
        if religion:
            result['religion'] = religion

        official_website = extract_official_website(soup)
        if official_website:
            result['official_website'] = official_website

        found_fields = [f for f in ['birth_year', 'birthplace', 'gender', 'religion', 'official_website'] if result[f]]
        result['notes'] = f"Found: {', '.join(found_fields)}" if found_fields else 'Page found but no target data extracted'

    except Exception as e:
        result['notes'] = f'Error: {str(e)}'

    return result

def main():
    print("Getting legislators from database...")
    legislators = get_legislators_from_db()
    print(f"Found {len(legislators)} legislators")
    print("Searching Wikipedia via DuckDuckGo...")
    print("This will take several minutes due to rate limiting\n")

    results = []

    for i, (leg_id, full_name, chamber) in enumerate(legislators):
        print(f"{i+1}/105: {full_name}")
        result = search_and_analyze(leg_id, full_name, chamber)
        results.append(result)
        time.sleep(2)

    total = len(results)
    has_page = sum(1 for r in results if r['has_page'])
    has_birth_year = sum(1 for r in results if r['birth_year'])
    has_birthplace = sum(1 for r in results if r['birthplace'])
    has_gender = sum(1 for r in results if r['gender'])
    has_religion = sum(1 for r in results if r['religion'])
    has_website = sum(1 for r in results if r['official_website'])

    print(f"\n{'='*50}")
    print(f"WIKIPEDIA COVERAGE ANALYSIS - UPDATED")
    print(f"{'='*50}")
    print(f"Total legislators: {total}")
    print(f"Has Wikipedia page: {has_page} ({round(has_page/total*100)}%)")
    print(f"Birth year found: {has_birth_year} ({round(has_birth_year/total*100)}%)")
    print(f"Birthplace found: {has_birthplace} ({round(has_birthplace/total*100)}%)")
    print(f"Gender found: {has_gender} ({round(has_gender/total*100)}%)")
    print(f"Religion found: {has_religion} ({round(has_religion/total*100)}%)")
    print(f"Official website found: {has_website} ({round(has_website/total*100)}%)")
    print(f"{'='*50}")

    output_file = 'analysis_wikipedia_duckduckgo.csv'
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'id', 'full_name', 'chamber', 'has_page', 'wikipedia_url',
            'official_website', 'birth_year', 'birthplace', 'gender',
            'religion', 'notes'
        ])
        writer.writeheader()
        writer.writerows(results)

    print(f"\nResults saved to analysis_wikipedia_duckduckgo.csv")

if __name__ == '__main__':
    main()