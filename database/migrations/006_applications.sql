create table if not exists applications (
    id             uuid primary key default gen_random_uuid(),
    citizen_id     uuid not null references citizens(id) on delete cascade,
    workflow_id    uuid not null references workflows(id),
    current_step   integer not null default 1,
    status         text not null default 'in_progress'
                  check (status in (
                      'in_progress', 'pending_review', 'completed',
                      'rejected', 'info_requested', 'withdrawn'
                  )),
    data_json      jsonb not null default '{}'::jsonb,
    step_history   jsonb not null default '[]'::jsonb,
    sla_deadline   timestamptz,
    created_at     timestamptz not null default now(),
    updated_at     timestamptz not null default now()
);

create index if not exists idx_applications_citizen_id on applications (citizen_id);

create index if not exists idx_applications_workflow_id on applications (workflow_id);

create index if not exists idx_applications_status on applications (status);