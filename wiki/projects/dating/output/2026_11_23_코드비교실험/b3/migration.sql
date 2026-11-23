-- Schemas & default privilege lockdown
create schema if not exists private;

revoke all on schema private from public, anon, authenticated;

alter default privileges in schema public revoke all on tables from public, anon, authenticated;
alter default privileges in schema public revoke all on sequences from public, anon, authenticated;
alter default privileges in schema public revoke all on functions from public, anon, authenticated;

-- 1. public.profiles
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  nickname text not null check (char_length(nickname) between 2 and 20),
  gender text not null check (gender in ('man', 'woman')),
  region text not null,
  bio text not null default '' check (char_length(bio) <= 500)
);

-- 2. public.member_status
create table public.member_status (
  user_id uuid primary key references auth.users(id) on delete cascade,
  status text not null default 'draft' check (status in ('draft', 'active', 'suspended')),
  photo_verified boolean not null default false
);

-- Trigger: auto-create member_status on profiles insert
create function private.handle_new_profile()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.member_status (user_id)
  values (new.id)
  on conflict (user_id) do nothing;
  return new;
end;
$$;

revoke all on function private.handle_new_profile() from public, anon, authenticated;

create trigger on_profile_created
after insert on public.profiles
for each row
execute function private.handle_new_profile();

-- 3. private.user_private
create table private.user_private (
  user_id uuid primary key references auth.users(id) on delete cascade,
  birth_date date not null
);

-- 4. private.admins
create table private.admins (
  user_id uuid primary key references auth.users(id) on delete cascade
);

-- 5. public.preferences
create table public.preferences (
  user_id uuid primary key references auth.users(id) on delete cascade,
  min_age int not null default 19,
  max_age int not null default 99,
  genders text[] not null,
  check (19 <= min_age and min_age <= max_age and max_age <= 99)
);

-- 6. public.swipes
create table public.swipes (
  from_id uuid not null references auth.users(id) on delete cascade,
  to_id uuid not null references auth.users(id) on delete cascade,
  action text not null check (action in ('like', 'pass')),
  created_at timestamptz not null default now(),
  primary key (from_id, to_id),
  check (from_id <> to_id)
);

-- 7. public.matches
create table public.matches (
  id uuid primary key default gen_random_uuid(),
  user_a uuid not null references auth.users(id) on delete cascade,
  user_b uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  ended_at timestamptz,
  check (user_a < user_b),
  unique (user_a, user_b)
);

-- 8. public.messages
create table public.messages (
  id uuid primary key default gen_random_uuid(),
  match_id uuid not null references public.matches(id) on delete cascade,
  sender_id uuid not null references auth.users(id) on delete cascade,
  body text not null check (char_length(body) between 1 and 2000),
  created_at timestamptz not null default now()
);

-- 9. public.blocks
create table public.blocks (
  blocker_id uuid not null references auth.users(id) on delete cascade,
  blocked_id uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (blocker_id, blocked_id),
  check (blocker_id <> blocked_id)
);

-- Enable RLS on all tables
alter table public.profiles enable row level security;
alter table public.member_status enable row level security;
alter table private.user_private enable row level security;
alter table private.admins enable row level security;
alter table public.preferences enable row level security;
alter table public.swipes enable row level security;
alter table public.matches enable row level security;
alter table public.messages enable row level security;
alter table public.blocks enable row level security;

-- RLS Policies (strictly for authenticated)
-- profiles: select/insert/update own
create policy profiles_select_own on public.profiles
  for select to authenticated
  using (id = auth.uid());

create policy profiles_insert_own on public.profiles
  for insert to authenticated
  with check (id = auth.uid());

create policy profiles_update_own on public.profiles
  for update to authenticated
  using (id = auth.uid())
  with check (id = auth.uid());

-- member_status: select own only
create policy member_status_select_own on public.member_status
  for select to authenticated
  using (user_id = auth.uid());

-- preferences: select/insert/update own
create policy preferences_select_own on public.preferences
  for select to authenticated
  using (user_id = auth.uid());

create policy preferences_insert_own on public.preferences
  for insert to authenticated
  with check (user_id = auth.uid());

create policy preferences_update_own on public.preferences
  for update to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

-- swipes: select own sent swipes only
create policy swipes_select_own on public.swipes
  for select to authenticated
  using (from_id = auth.uid());

-- matches: select if participant
create policy matches_select_participant on public.matches
  for select to authenticated
  using (user_a = auth.uid() or user_b = auth.uid());

-- messages: select if match participant
create policy messages_select_participant on public.messages
  for select to authenticated
  using (
    exists (
      select 1 from public.matches m
      where m.id = messages.match_id
        and (m.user_a = auth.uid() or m.user_b = auth.uid())
    )
  );

-- blocks: select own blocks only
create policy blocks_select_own on public.blocks
  for select to authenticated
  using (blocker_id = auth.uid());

-- Functions (all in public schema, security definer, fixed search_path)

-- 1. set_birth_date(d date) returns void
create function public.set_birth_date(d date)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := auth.uid();
begin
  if v_uid is null then
    raise exception 'Unauthorized';
  end if;

  if d is null or extract(year from pg_catalog.age(current_date, d))::int < 19 then
    raise exception 'User must be at least 19 years old';
  end if;

  insert into private.user_private (user_id, birth_date)
  values (v_uid, d)
  on conflict (user_id) do update
    set birth_date = excluded.birth_date;
end;
$$;

-- 2. admin_set_status(target uuid, new_status text, verified boolean) returns void
create function public.admin_set_status(target uuid, new_status text, verified boolean)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := auth.uid();
begin
  if v_uid is null then
    raise exception 'Unauthorized';
  end if;

  if not exists (select 1 from private.admins a where a.user_id = v_uid) then
    raise exception 'Forbidden: admin only';
  end if;

  if target is null or new_status is null or verified is null then
    raise exception 'Invalid parameters';
  end if;

  insert into public.member_status (user_id, status, photo_verified)
  values (target, new_status, verified)
  on conflict (user_id) do update
    set status = excluded.status,
        photo_verified = excluded.photo_verified;
end;
$$;

-- 3. get_candidates(lim int default 20)
create function public.get_candidates(lim int default 20)
returns table(id uuid, nickname text, age int, gender text, region text, bio text)
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := auth.uid();
begin
  if v_uid is null then
    raise exception 'Unauthorized';
  end if;

  if not exists (
    select 1 from public.member_status ms
    where ms.user_id = v_uid
      and ms.status = 'active'
      and ms.photo_verified = true
  ) then
    raise exception 'Caller is not eligible';
  end if;

  return query
  select
    cp.id,
    cp.nickname,
    extract(year from pg_catalog.age(current_date, cup.birth_date))::int as age,
    cp.gender,
    cp.region,
    cp.bio
  from public.profiles mp
  join private.user_private mup on mup.user_id = mp.id
  join public.preferences mpref on mpref.user_id = mp.id
  join public.profiles cp on cp.id <> v_uid
  join public.member_status cms on cms.user_id = cp.id
    and cms.status = 'active'
    and cms.photo_verified = true
  join private.user_private cup on cup.user_id = cp.id
  join public.preferences cpref on cpref.user_id = cp.id
  where mp.id = v_uid
    and cp.gender = any(mpref.genders)
    and extract(year from pg_catalog.age(current_date, cup.birth_date))::int between mpref.min_age and mpref.max_age
    and mp.gender = any(cpref.genders)
    and extract(year from pg_catalog.age(current_date, mup.birth_date))::int between cpref.min_age and cpref.max_age
    and not exists (
      select 1 from public.blocks b
      where (b.blocker_id = v_uid and b.blocked_id = cp.id)
         or (b.blocker_id = cp.id and b.blocked_id = v_uid)
    )
    and not exists (
      select 1 from public.swipes s
      where s.from_id = v_uid
        and s.to_id = cp.id
        and (
          s.action = 'like'
          or (s.action = 'pass' and s.created_at >= now() - interval '30 days')
        )
    )
    and not exists (
      select 1 from public.matches m
      where m.user_a = least(v_uid, cp.id)
        and m.user_b = greatest(v_uid, cp.id)
        and m.ended_at is null
    )
  limit greatest(coalesce(lim, 20), 0);
end;
$$;

-- 4. swipe(target uuid, act text) returns uuid
create function public.swipe(target uuid, act text)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := auth.uid();
  v_match_id uuid;
begin
  if v_uid is null then
    raise exception 'Unauthorized';
  end if;

  if target is null or act is null or act not in ('like', 'pass') then
    raise exception 'Invalid swipe parameters';
  end if;

  if target = v_uid then
    raise exception 'Cannot swipe yourself';
  end if;

  if not exists (
    select 1 from public.member_status ms
    where ms.user_id = v_uid
      and ms.status = 'active'
      and ms.photo_verified = true
  ) then
    raise exception 'Caller is not eligible';
  end if;

  if not exists (
    select 1 from public.member_status ms
    where ms.user_id = target
      and ms.status = 'active'
      and ms.photo_verified = true
  ) then
    raise exception 'Target is not eligible';
  end if;

  if exists (
    select 1 from public.blocks b
    where (b.blocker_id = v_uid and b.blocked_id = target)
       or (b.blocker_id = target and b.blocked_id = v_uid)
  ) then
    raise exception 'Blocked relationship';
  end if;

  insert into public.swipes (from_id, to_id, action, created_at)
  values (v_uid, target, act, now())
  on conflict (from_id, to_id) do update
    set action = excluded.action,
        created_at = excluded.created_at;

  if act = 'like' and exists (
    select 1 from public.swipes s
    where s.from_id = target
      and s.to_id = v_uid
      and s.action = 'like'
  ) then
    insert into public.matches (user_a, user_b)
    values (least(v_uid, target), greatest(v_uid, target))
    on conflict (user_a, user_b) do update
      set user_a = excluded.user_a
    returning id into v_match_id;

    return v_match_id;
  end if;

  return null;
end;
$$;

-- 5. send_message(mid uuid, body text) returns uuid
create function public.send_message(mid uuid, body text)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := auth.uid();
  v_user_a uuid;
  v_user_b uuid;
  v_ended_at timestamptz;
  v_other uuid;
  v_msg_id uuid;
begin
  if v_uid is null then
    raise exception 'Unauthorized';
  end if;

  if mid is null or send_message.body is null or char_length(send_message.body) not between 1 and 2000 then
    raise exception 'Invalid message parameters';
  end if;

  select m.user_a, m.user_b, m.ended_at
    into v_user_a, v_user_b, v_ended_at
    from public.matches m
   where m.id = mid;

  if not found then
    raise exception 'Match not found';
  end if;

  if v_uid <> v_user_a and v_uid <> v_user_b then
    raise exception 'Not a participant of this match';
  end if;

  if v_ended_at is not null then
    raise exception 'Match has ended';
  end if;

  v_other := case when v_uid = v_user_a then v_user_b else v_user_a end;

  if exists (
    select 1 from public.blocks b
    where (b.blocker_id = v_uid and b.blocked_id = v_other)
       or (b.blocker_id = v_other and b.blocked_id = v_uid)
  ) then
    raise exception 'Blocked relationship';
  end if;

  insert into public.messages (match_id, sender_id, body)
  values (mid, v_uid, send_message.body)
  returning id into v_msg_id;

  return v_msg_id;
end;
$$;

-- 6. block_user(target uuid) returns void
create function public.block_user(target uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := auth.uid();
begin
  if v_uid is null then
    raise exception 'Unauthorized';
  end if;

  if target is null or target = v_uid then
    raise exception 'Invalid block target';
  end if;

  insert into public.blocks (blocker_id, blocked_id)
  values (v_uid, target)
  on conflict (blocker_id, blocked_id) do nothing;

  update public.matches
     set ended_at = now()
   where user_a = least(v_uid, target)
     and user_b = greatest(v_uid, target)
     and ended_at is null;
end;
$$;

-- 7. delete_my_account() returns void
create function public.delete_my_account()
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := auth.uid();
begin
  if v_uid is null then
    raise exception 'Unauthorized';
  end if;

  delete from auth.users where id = v_uid;
end;
$$;

-- Table & Function Privilege Lockdown
revoke all on all tables in schema public from public, anon, authenticated;
revoke all on all sequences in schema public from public, anon, authenticated;
revoke all on all functions in schema public from public, anon, authenticated;
revoke all on all tables in schema private from public, anon, authenticated;

-- Grant strictly required table privileges to authenticated
grant select, insert, update on public.profiles to authenticated;
grant select on public.member_status to authenticated;
grant select, insert, update on public.preferences to authenticated;
grant select on public.swipes to authenticated;
grant select on public.matches to authenticated;
grant select on public.messages to authenticated;
grant select on public.blocks to authenticated;

-- Grant function execution only to authenticated
grant execute on function public.set_birth_date(date) to authenticated;
grant execute on function public.admin_set_status(uuid, text, boolean) to authenticated;
grant execute on function public.get_candidates(int) to authenticated;
grant execute on function public.swipe(uuid, text) to authenticated;
grant execute on function public.send_message(uuid, text) to authenticated;
grant execute on function public.block_user(uuid) to authenticated;
grant execute on function public.delete_my_account() to authenticated;
