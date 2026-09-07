create table if not exists notifications (
    id uuid primary key default gen_random_uuid (),
    citizen_id uuid not null references citizens (id) on delete cascade,
    message text not null,
    read_status boolean not null default false,
    created_at timestamptz not null default now()
);

create index if not exists idx_notifications_citizen_id on notifications (citizen_id);

create index if not exists idx_notifications_read_status on notifications (read_status);