create table if not exists public.rounds (
    id uuid primary key,
    name text not null,
    is_active boolean not null default false,
    created_at timestamptz not null default now()
);

create table if not exists public.current_books (
    id uuid primary key,
    round_id uuid not null references public.rounds(id) on delete cascade,
    title text not null,
    author text,
    cover_url text
);

create table if not exists public.round_books (
    id uuid primary key,
    round_id uuid not null references public.rounds(id) on delete cascade,
    title text not null,
    author text,
    cover_url text,
    display_order integer not null
);

create table if not exists public.votes (
    id uuid primary key,
    submitted_at timestamptz not null default now(),
    round_id uuid not null references public.rounds(id) on delete cascade,
    rank_1 text not null,
    rank_2 text not null,
    rank_3 text not null,
    rating integer not null check (rating between 1 and 5)
);

create index if not exists votes_round_id_idx on public.votes(round_id);
create index if not exists round_books_round_id_idx on public.round_books(round_id);

alter table public.rounds enable row level security;
alter table public.current_books enable row level security;
alter table public.round_books enable row level security;
alter table public.votes enable row level security;

-- Public users may read the active/current poll data.
drop policy if exists "Public read rounds" on public.rounds;
create policy "Public read rounds"
on public.rounds for select to anon using (true);

drop policy if exists "Public read current books" on public.current_books;
create policy "Public read current books"
on public.current_books for select to anon using (true);

drop policy if exists "Public read round books" on public.round_books;
create policy "Public read round books"
on public.round_books for select to anon using (true);

-- Public users may submit votes, but cannot read raw ballot rows.
-- Results are read server-side using the Supabase secret key and shown only as aggregates.
drop policy if exists "Public read votes" on public.votes;

drop policy if exists "Public insert votes" on public.votes;
create policy "Public insert votes"
on public.votes for insert to anon with check (true);

-- Deliberately NO anon insert/update/delete policies on rounds/current_books/round_books.
-- Admin operations use the Supabase secret key server-side, which bypasses RLS.
