-- Simulated external government databases, keyed by aadhaar_number so
-- digilocker_mock.py can join across them.

create table if not exists mock_gov_uidai (
    aadhaar_number text primary key,
    name text not null,
    dob date not null,
    address text not null
);

create table if not exists mock_gov_pan (
    aadhaar_number text primary key references mock_gov_uidai (aadhaar_number) on delete cascade,
    pan_number text not null unique,
    name text not null,
    dob date not null,
    address text
);

create table if not exists mock_gov_voter (
    aadhaar_number text primary key references mock_gov_uidai (aadhaar_number) on delete cascade,
    voter_id text not null unique,
    name text not null,
    dob date not null,
    address text
);

create table if not exists mock_gov_udyam (
    aadhaar_number text primary key references mock_gov_uidai (aadhaar_number) on delete cascade,
    udyam_number text not null unique,
    name text not null,
    dob date,
    address text
);