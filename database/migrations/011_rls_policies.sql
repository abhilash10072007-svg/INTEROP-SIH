-- The backend uses the SERVICE ROLE key (supabase_admin), which bypasses RLS
-- entirely — so these policies only matter for any direct-from-frontend
-- Supabase calls (Auth session management, Realtime notifications channel).
-- Enable RLS everywhere as a safety net even though backend writes bypass it.

alter table profiles enable row level security;

alter table citizens enable row level security;

alter table pending_registrations enable row level security;

alter table workflows enable row level security;

alter table workflow_steps enable row level security;

alter table applications enable row level security;

alter table consent_logs enable row level security;

alter table audit_logs enable row level security;

alter table notifications enable row level security;

alter table mock_gov_uidai enable row level security;

alter table mock_gov_pan enable row level security;

alter table mock_gov_voter enable row level security;

alter table mock_gov_udyam enable row level security;

-- profiles: a user can read their own profile row
create policy "profiles_select_own" on profiles for
select using (auth.uid () = id);

-- citizens: a citizen can read their own record (used mainly for Realtime /
-- direct reads from frontend; backend itself bypasses this via service role)
create policy "citizens_select_own" on citizens for
select using (auth.uid () = profile_id);

-- notifications: citizens can select + update (mark read) their own rows,
-- since the frontend subscribes directly via supabase.channel('notifications')
create policy "notifications_select_own" on notifications for
select using (
        citizen_id in (
            select id
            from citizens
            where
                profile_id = auth.uid ()
        )
    );

create policy "notifications_update_own" on notifications for
update using (
    citizen_id in (
        select id
        from citizens
        where
            profile_id = auth.uid ()
    )
);

-- workflows / workflow_steps: public read (service catalog is unauthenticated)
create policy "workflows_public_read" on workflows for
select using (true);

create policy "workflow_steps_public_read" on workflow_steps for
select using (true);

-- applications: citizens can read their own applications directly if needed
create policy "applications_select_own" on applications for
select using (
        citizen_id in (
            select id
            from citizens
            where
                profile_id = auth.uid ()
        )
    );

-- consent_logs: citizens can read their own consent history directly
create policy "consent_logs_select_own" on consent_logs for
select using (
        citizen_id in (
            select id
            from citizens
            where
                profile_id = auth.uid ()
        )
    );

-- Everything else (pending_registrations, audit_logs, mock_gov_*) has RLS
-- enabled with NO policies defined — meaning zero access except via the
-- service-role key used by the backend. This is intentional: these tables
-- should never be readable directly from the frontend.