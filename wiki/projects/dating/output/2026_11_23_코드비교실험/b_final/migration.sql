-- 소개팅 앱 1단계: DB 스키마, RLS, 권한 회수, 핵심 함수

-- 1. private 스키마
create schema if not exists private;
revoke all on schema private from public, anon, authenticated;

-- 2. 테이블 생성

-- public.profiles
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  nickname text not null check (pg_catalog.char_length(nickname) between 2 and 20),
  gender text not null check (gender in ('man', 'woman')),
  region text not null,
  bio text not null default '' check (pg_catalog.char_length(bio) <= 500)
);

-- public.member_status
create table public.member_status (
  user_id uuid primary key references auth.users(id) on delete cascade,
  status text not null default 'draft' check (status in ('draft', 'active', 'suspended')),
  photo_verified boolean not null default false
);

-- private.user_private
create table private.user_private (
  user_id uuid primary key references auth.users(id) on delete cascade,
  birth_date date not null
);

-- private.admins
create table private.admins (
  user_id uuid primary key references auth.users(id) on delete cascade
);

-- public.preferences
create table public.preferences (
  user_id uuid primary key references auth.users(id) on delete cascade,
  min_age int not null default 19,
  max_age int not null default 99,
  genders text[] not null,
  check (min_age >= 19 and min_age <= max_age and max_age <= 99),
  check (genders <@ array['man', 'woman']::text[])
);

-- public.swipes
create table public.swipes (
  from_id uuid not null references auth.users(id) on delete cascade,
  to_id uuid not null references auth.users(id) on delete cascade,
  action text not null check (action in ('like', 'pass')),
  created_at timestamptz not null default pg_catalog.now(),
  primary key (from_id, to_id),
  check (from_id <> to_id)
);

-- public.matches
create table public.matches (
  id uuid primary key default pg_catalog.gen_random_uuid(),
  user_a uuid not null references auth.users(id) on delete cascade,
  user_b uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default pg_catalog.now(),
  ended_at timestamptz,
  check (user_a < user_b),
  unique (user_a, user_b)
);

-- public.messages
create table public.messages (
  id uuid primary key default pg_catalog.gen_random_uuid(),
  match_id uuid not null references public.matches(id) on delete cascade,
  sender_id uuid not null references auth.users(id) on delete cascade,
  body text not null check (pg_catalog.char_length(body) between 1 and 2000),
  created_at timestamptz not null default pg_catalog.now()
);

-- public.blocks
create table public.blocks (
  blocker_id uuid not null references auth.users(id) on delete cascade,
  blocked_id uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default pg_catalog.now(),
  primary key (blocker_id, blocked_id),
  check (blocker_id <> blocked_id)
);

-- 3. 인덱스
create index idx_member_status_eligible
  on public.member_status (user_id)
  where status = 'active' and photo_verified = true;

create index idx_swipes_to_from on public.swipes (to_id, from_id);
create index idx_matches_user_b on public.matches (user_b);
create index idx_messages_match_created on public.messages (match_id, created_at);
create index idx_blocks_blocked_id on public.blocks (blocked_id);

-- 4. profiles insert 시 member_status 자동 생성 트리거
create or replace function private.handle_new_profile()
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

create trigger trg_profiles_create_member_status
  after insert on public.profiles
  for each row
  execute function private.handle_new_profile();

-- 5. RLS 활성화 및 정책

alter table public.profiles enable row level security;
alter table public.member_status enable row level security;
alter table public.preferences enable row level security;
alter table public.swipes enable row level security;
alter table public.matches enable row level security;
alter table public.messages enable row level security;
alter table public.blocks enable row level security;
alter table private.user_private enable row level security;
alter table private.admins enable row level security;

-- public.profiles: 자기 것만 select / insert / update
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

-- public.member_status: 자기 것만 select
create policy member_status_select_own on public.member_status
  for select to authenticated
  using (user_id = auth.uid());

-- public.preferences: 자기 것만 select / insert / update
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

-- public.swipes: 자기가 보낸 것만 select
create policy swipes_select_own on public.swipes
  for select to authenticated
  using (from_id = auth.uid());

-- public.matches: 당사자만 select
create policy matches_select_participant on public.matches
  for select to authenticated
  using (user_a = auth.uid() or user_b = auth.uid());

-- public.messages: 매칭 당사자만 select
create policy messages_select_participant on public.messages
  for select to authenticated
  using (
    exists (
      select 1
      from public.matches m
      where m.id = messages.match_id
        and (m.user_a = auth.uid() or m.user_b = auth.uid())
    )
  );

-- public.blocks: 자기가 한 차단만 select
create policy blocks_select_own on public.blocks
  for select to authenticated
  using (blocker_id = auth.uid());

-- 6. 테이블 권한 회수 및 최소 권한 부여

revoke all on table public.profiles from public, anon, authenticated;
revoke all on table public.member_status from public, anon, authenticated;
revoke all on table public.preferences from public, anon, authenticated;
revoke all on table public.swipes from public, anon, authenticated;
revoke all on table public.matches from public, anon, authenticated;
revoke all on table public.messages from public, anon, authenticated;
revoke all on table public.blocks from public, anon, authenticated;
revoke all on table private.user_private from public, anon, authenticated;
revoke all on table private.admins from public, anon, authenticated;

grant select, insert, update on table public.profiles to authenticated;
grant select on table public.member_status to authenticated;
grant select, insert, update on table public.preferences to authenticated;
grant select on table public.swipes to authenticated;
grant select on table public.matches to authenticated;
grant select on table public.messages to authenticated;
grant select on table public.blocks to authenticated;

-- 7. 핵심 함수 (모두 public 스키마, security definer, set search_path = '')

-- 7-1. set_birth_date(d date) returns void
create or replace function public.set_birth_date(d date)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := auth.uid();
  v_age int;
begin
  if v_uid is null then
    raise exception 'not authenticated';
  end if;

  if d is null then
    raise exception 'birth_date is required';
  end if;

  v_age := extract(year from pg_catalog.age(current_date, d))::int;
  if v_age < 19 then
    raise exception 'must be at least 19 years old';
  end if;

  insert into private.user_private (user_id, birth_date)
  values (v_uid, d)
  on conflict (user_id) do update
    set birth_date = excluded.birth_date;
end;
$$;

-- 7-2. admin_set_status(target uuid, new_status text, verified boolean) returns void
create or replace function public.admin_set_status(target uuid, new_status text, verified boolean)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := auth.uid();
begin
  if v_uid is null then
    raise exception 'not authenticated';
  end if;

  if not exists (
    select 1 from private.admins a where a.user_id = v_uid
  ) then
    raise exception 'forbidden: admin only';
  end if;

  if target is null then
    raise exception 'target is required';
  end if;

  if new_status is null or new_status not in ('draft', 'active', 'suspended') then
    raise exception 'invalid status';
  end if;

  if verified is null then
    raise exception 'verified is required';
  end if;

  insert into public.member_status (user_id, status, photo_verified)
  values (target, new_status, verified)
  on conflict (user_id) do update
    set status = excluded.status,
        photo_verified = excluded.photo_verified;
end;
$$;

-- 7-3. get_candidates(lim int default 20) returns table(...)
create or replace function public.get_candidates(lim int default 20)
returns table(
  id uuid,
  nickname text,
  age int,
  gender text,
  region text,
  bio text
)
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := auth.uid();
  v_lim int;
begin
  if v_uid is null then
    raise exception 'not authenticated';
  end if;

  if not exists (
    select 1
    from public.member_status ms
    where ms.user_id = v_uid
      and ms.status = 'active'
      and ms.photo_verified = true
  ) then
    raise exception 'not eligible';
  end if;

  v_lim := greatest(coalesce(lim, 20), 0);

  return query
  select
    cp.id,
    cp.nickname,
    extract(year from pg_catalog.age(current_date, cpriv.birth_date))::int as age,
    cp.gender,
    cp.region,
    cp.bio
  from public.profiles mp
  join public.preferences mpref on mpref.user_id = mp.id
  join private.user_private mpriv on mpriv.user_id = mp.id
  join public.profiles cp on cp.id <> mp.id
  join public.member_status cms on cms.user_id = cp.id
  join public.preferences cpref on cpref.user_id = cp.id
  join private.user_private cpriv on cpriv.user_id = cp.id
  where mp.id = v_uid
    and cms.status = 'active'
    and cms.photo_verified = true
    -- 서로의 선호 (성별·나이 범위) 만족
    and cp.gender = any(mpref.genders)
    and extract(year from pg_catalog.age(current_date, cpriv.birth_date))::int
        between mpref.min_age and mpref.max_age
    and mp.gender = any(cpref.genders)
    and extract(year from pg_catalog.age(current_date, mpriv.birth_date))::int
        between cpref.min_age and cpref.max_age
    -- 어느 쪽이든 차단 없음
    and not exists (
      select 1
      from public.blocks b
      where (b.blocker_id = v_uid and b.blocked_id = cp.id)
         or (b.blocker_id = cp.id and b.blocked_id = v_uid)
    )
    -- 내가 like한 사람 제외, 내가 30일 안에 pass한 사람 제외
    and not exists (
      select 1
      from public.swipes s
      where s.from_id = v_uid
        and s.to_id = cp.id
        and (
          s.action = 'like'
          or (s.action = 'pass' and s.created_at > pg_catalog.now() - interval '30 days')
        )
    )
    -- 이미 매칭(종료 안 된)된 사람 제외
    and not exists (
      select 1
      from public.matches m
      where m.ended_at is null
        and m.user_a = least(v_uid, cp.id)
        and m.user_b = greatest(v_uid, cp.id)
    )
  order by cp.id
  limit v_lim;
end;
$$;

-- 7-4. swipe(target uuid, act text) returns uuid
create or replace function public.swipe(target uuid, act text)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := auth.uid();
  v_a uuid;
  v_b uuid;
  v_match_id uuid;
begin
  if v_uid is null then
    raise exception 'not authenticated';
  end if;

  if target is null then
    raise exception 'target is required';
  end if;

  if target = v_uid then
    raise exception 'cannot swipe self';
  end if;

  if act is null or act not in ('like', 'pass') then
    raise exception 'invalid action';
  end if;

  -- 동시성: 같은 두 사람 사이의 swipe/block_user/send_message 를 직렬화한다.
  -- (없으면 A·B가 동시에 like 할 때 서로의 미커밋 like를 못 봐서 매칭이 안 생긴다)
  perform pg_catalog.pg_advisory_xact_lock(
    pg_catalog.hashtextextended(least(v_uid, target)::text || greatest(v_uid, target)::text, 0)
  );

  if not exists (
    select 1
    from public.member_status ms
    where ms.user_id = v_uid
      and ms.status = 'active'
      and ms.photo_verified = true
  ) then
    raise exception 'caller not eligible';
  end if;

  if not exists (
    select 1
    from public.member_status ms
    where ms.user_id = target
      and ms.status = 'active'
      and ms.photo_verified = true
  ) then
    raise exception 'target not eligible';
  end if;

  if exists (
    select 1
    from public.blocks b
    where (b.blocker_id = v_uid and b.blocked_id = target)
       or (b.blocker_id = target and b.blocked_id = v_uid)
  ) then
    raise exception 'blocked relationship';
  end if;

  insert into public.swipes (from_id, to_id, action, created_at)
  values (v_uid, target, act, pg_catalog.now())
  on conflict (from_id, to_id) do update
    set action = excluded.action,
        created_at = pg_catalog.now();

  if act = 'like' and exists (
    select 1
    from public.swipes s
    where s.from_id = target
      and s.to_id = v_uid
      and s.action = 'like'
  ) then
    v_a := least(v_uid, target);
    v_b := greatest(v_uid, target);

    insert into public.matches (user_a, user_b)
    values (v_a, v_b)
    on conflict (user_a, user_b) do nothing
    returning id into v_match_id;

    if v_match_id is null then
      select m.id into v_match_id
      from public.matches m
      where m.user_a = v_a and m.user_b = v_b;
    end if;

    return v_match_id;
  end if;

  return null;
end;
$$;

-- 7-5. send_message(mid uuid, body text) returns uuid
create or replace function public.send_message(mid uuid, body text)
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
  v_msg_id uuid;
begin
  if v_uid is null then
    raise exception 'not authenticated';
  end if;

  if mid is null then
    raise exception 'match_id is required';
  end if;

  if body is null or pg_catalog.char_length(body) < 1 or pg_catalog.char_length(body) > 2000 then
    raise exception 'invalid message body';
  end if;

  select m.user_a, m.user_b, m.ended_at
    into v_user_a, v_user_b, v_ended_at
  from public.matches m
  where m.id = mid;

  if not found then
    raise exception 'match not found';
  end if;

  if v_user_a <> v_uid and v_user_b <> v_uid then
    raise exception 'not a participant of this match';
  end if;

  -- 동시성: block_user 와 직렬화한 뒤 종료 여부를 다시 읽는다(차단 직후 메시지가 끼어드는 것 방지)
  perform pg_catalog.pg_advisory_xact_lock(
    pg_catalog.hashtextextended(v_user_a::text || v_user_b::text, 0)
  );

  select m.ended_at into v_ended_at
  from public.matches m
  where m.id = mid;

  if v_ended_at is not null then
    raise exception 'match has ended';
  end if;

  if exists (
    select 1
    from public.blocks b
    where (b.blocker_id = v_user_a and b.blocked_id = v_user_b)
       or (b.blocker_id = v_user_b and b.blocked_id = v_user_a)
  ) then
    raise exception 'blocked relationship';
  end if;

  insert into public.messages (match_id, sender_id, body)
  values (mid, v_uid, body)
  returning id into v_msg_id;

  return v_msg_id;
end;
$$;

-- 7-6. block_user(target uuid) returns void
create or replace function public.block_user(target uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := auth.uid();
begin
  if v_uid is null then
    raise exception 'not authenticated';
  end if;

  if target is null or target = v_uid then
    raise exception 'invalid target';
  end if;

  -- 동시성: swipe/send_message 와 직렬화(차단과 동시에 만들어진 매칭·메시지가 남지 않게)
  perform pg_catalog.pg_advisory_xact_lock(
    pg_catalog.hashtextextended(least(v_uid, target)::text || greatest(v_uid, target)::text, 0)
  );

  insert into public.blocks (blocker_id, blocked_id)
  values (v_uid, target)
  on conflict (blocker_id, blocked_id) do nothing;

  update public.matches
  set ended_at = pg_catalog.now()
  where user_a = least(v_uid, target)
    and user_b = greatest(v_uid, target)
    and ended_at is null;
end;
$$;

-- 7-7. delete_my_account() returns void
create or replace function public.delete_my_account()
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := auth.uid();
begin
  if v_uid is null then
    raise exception 'not authenticated';
  end if;

  delete from auth.users where id = v_uid;
end;
$$;

-- 8. 함수 권한 회수 및 authenticated에만 부여

revoke all on function public.set_birth_date(date) from public, anon, authenticated;
revoke all on function public.admin_set_status(uuid, text, boolean) from public, anon, authenticated;
revoke all on function public.get_candidates(int) from public, anon, authenticated;
revoke all on function public.swipe(uuid, text) from public, anon, authenticated;
revoke all on function public.send_message(uuid, text) from public, anon, authenticated;
revoke all on function public.block_user(uuid) from public, anon, authenticated;
revoke all on function public.delete_my_account() from public, anon, authenticated;

grant execute on function public.set_birth_date(date) to authenticated;
grant execute on function public.admin_set_status(uuid, text, boolean) to authenticated;
grant execute on function public.get_candidates(int) to authenticated;
grant execute on function public.swipe(uuid, text) to authenticated;
grant execute on function public.send_message(uuid, text) to authenticated;
grant execute on function public.block_user(uuid) to authenticated;
grant execute on function public.delete_my_account() to authenticated;
