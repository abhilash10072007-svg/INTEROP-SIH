create table if not exists citizens (
    id                   uuid primary key default gen_random_uuid(),
    profile_id           uuid not null references profiles(id) on delete cascade,
    name                 text not null,
    mobile               text not null unique,
    email                text not null,
    dob                  date not null,
    address              text not null,
    aadhaar_number       text not null unique,
    documents            jsonb not null default '[]'::jsonb,
    verification_status  text not null default 'verified'
                         check (verification_status in ('verified', 'pending', 'flagged', 'fraud_flag')),
    linked_pan           text,
    linked_voter_id      text,
    linked_udyam         text,
    linked_license       text,
    created_at           timestamptz not null default now(),
    updated_at           timestamptz not null default now()
);

create index if not exists idx_citizens_profile_id on citizens (profile_id);

create index if not exists idx_citizens_mobile on citizens (mobile);

create index if not exists idx_citizens_aadhaar on citizens (aadhaar_number);