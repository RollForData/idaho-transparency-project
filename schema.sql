-- Idaho Transparency Project
-- Database Schema

-- LEGISLATORS (anchor table, everything joins to this)
CREATE TABLE legislators (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    chamber VARCHAR(10) NOT NULL,
    district_number INTEGER NOT NULL,
    party_affiliation VARCHAR(50),
    total_terms INTEGER,
    next_election_year INTEGER,
    years_registered_idaho INTEGER,
    age INTEGER,
    race_ethnicity VARCHAR(100),
    gender VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    headshot_url VARCHAR(500),
    occupation VARCHAR(255),
    seat_designation VARCHAR(5),

);

-- DEMOGRAPHIC MIRROR
CREATE TABLE demographic_mirror (
    id SERIAL PRIMARY KEY,
    legislator_id INTEGER REFERENCES legislators(id),
    district_median_age DECIMAL(5,2),
    legislator_number_properties INTEGER,
    legislator_total_assessed_property_value DECIMAL(15,2),
    number_llcs INTEGER,
    combined_llc_property_value DECIMAL(15,2),
    district_homeownership_rate DECIMAL(5,2),
    district_median_home_value DECIMAL(15,2),
    district_racial_demographics JSONB,
    district_party_registration JSONB,
    data_year INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- FUNDING SOURCES
CREATE TABLE funding_sources (
    id SERIAL PRIMARY KEY,
    legislator_id INTEGER REFERENCES legislators(id),
    donor_name VARCHAR(255),
    donor_amount DECIMAL(12,2),
    donor_in_state BOOLEAN,
    donor_type VARCHAR(50),
    donation_industry VARCHAR(100),
    is_independent_expenditure BOOLEAN,
    ie_support_or_oppose VARCHAR(10),
    election_year INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- NOTABLE VOTES
CREATE TABLE notable_votes (
    id SERIAL PRIMARY KEY,
    legislator_id INTEGER REFERENCES legislators(id),
    bill_id VARCHAR(50),
    bill_name VARCHAR(255),
    vote_cast VARCHAR(20),
    vote_year INTEGER,
    vote_category VARCHAR(100),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- DISTRICT QUALITY OF LIFE
CREATE TABLE district_quality_of_life (
    id SERIAL PRIMARY KEY,
    legislator_id INTEGER REFERENCES legislators(id),
    metric_year INTEGER,
    per_pupil_education_spending DECIMAL(10,2),
    uninsured_rate DECIMAL(5,2),
    unemployment_rate DECIMAL(5,2),
    homeownership_rate DECIMAL(5,2),
    median_household_income DECIMAL(12,2),
    poverty_rate DECIMAL(5,2),
    total_employment INTEGER,
    average_weekly_wage DECIMAL(10,2),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ZIP CODE TO DISTRICT CROSSWALK
CREATE TABLE zip_district_crosswalk (
    id SERIAL PRIMARY KEY,
    zip_code VARCHAR(10) NOT NULL,
    district_number INTEGER NOT NULL,
    school_district_id VARCHAR(20),
    school_district_name VARCHAR(255),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);