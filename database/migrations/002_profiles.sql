-- profiles.id == auth.users.id (created via supabase_admin.auth.admin.create_user
-- in /auth/callback, then inserted here with the same id)
create table if not exists profiles (
    id uuid primary key references auth.users (id) on delete cascade,
    name text not null,
    email text not null,
    role text not null default 'citizen' check (
        role in (
            'citizen',
            'official_rto',
            'official_bank',
            'admin'
        )
    ),
    created_at timestamptz not null default now()
);

create index if not exists idx_profiles_role on profiles (role);