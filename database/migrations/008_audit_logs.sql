create table if not exists audit_logs (
    id                 uuid primary key default gen_random_uuid(),
    actor_id           uuid,               -- nullable: some actions (e.g. pre_register) have no authenticated actor yet
    action             text not null,
    target_citizen_id  uuid references citizens(id) on delete set null,
    details            jsonb not null default '{}'::jsonb,
    timestamp          timestamptz not null default now()
);

create index if not exists idx_audit_logs_actor_id on audit_logs (actor_id);

create index if not exists idx_audit_logs_target_citizen_id on audit_logs (target_citizen_id);

create index if not exists idx_audit_logs_action on audit_logs (action);

create index if not exists idx_audit_logs_timestamp on audit_logs (timestamp desc);