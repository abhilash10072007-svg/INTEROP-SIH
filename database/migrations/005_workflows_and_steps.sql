create table if not exists workflows (
    id uuid primary key default gen_random_uuid (),
    service_name text not null,
    description text,
    created_at timestamptz not null default now()
);

create table if not exists workflow_steps (
    id uuid primary key default gen_random_uuid (),
    workflow_id uuid not null references workflows (id) on delete cascade,
    step_order integer not null,
    step_name text not null,
    step_type text not null, -- e.g. 'form', 'document_upload', 'risk_assessment', 'review'
    auto_or_manual text not null check (
        auto_or_manual in ('auto', 'manual')
    ),
    unique (workflow_id, step_order)
);

create index if not exists idx_workflow_steps_workflow_id on workflow_steps (workflow_id);