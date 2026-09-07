create table if not exists pending_registrations (
    id uuid primary key default gen_random_uuid (),
    full_name text not null,
    mobile text not null,
    email text not null,
    dob date not null,
    aadhaar_number text not null,
    created_at timestamptz not null default now()
);

create index if not exists idx_pending_reg_mobile on pending_registrations (mobile);