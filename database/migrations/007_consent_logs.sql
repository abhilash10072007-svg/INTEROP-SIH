create table if not exists consent_logs (
    id uuid primary key default gen_random_uuid (),
    citizen_id uuid not null references citizens (id) on delete cascade,
    requested_by text not null, -- official/user_id or system identifier requesting access
    data_scope text not null,
    purpose text not null,
    status text not null default 'pending' check (
        status in (
            'pending',
            'approved',
            'denied'
        )
    ),
    timestamp timestamptz not null default now()
);

create index if not exists idx_consent_logs_citizen_id on consent_logs (citizen_id);

create index if not exists idx_consent_logs_status on consent_logs (status);