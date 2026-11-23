-- ============================================================================
-- 소개팅 앱 1단계 — DB + 권한(RLS) + 핵심 함수
-- ============================================================================

-- 1. 스키마 및 기본 권한 정비
create schema private;
revoke all on schema private from public, anon, authenticated;
revoke create on schema public from public, anon, authenticated;

-- 2. 테이블 정의

-- 2-1. 공개 프로필 (본인만 조회/생성/수정)
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  nickname text not null check (char_length(nickname) between 2 and 20),
  gender text not null check (gender in ('man', 'woman')),
  region text not null,
  bio text not null default '' check (char_length(bio) <= 500)
);

-- 2-2. 회원 상태 (프로필 생성 시 트리거로 자동 생성, 본인 조회만 가능, 변경은 운영자 함수만)
create table public.member_status (
  user_id uuid primary key references auth.users(id) on delete cascade,
  status text not null default 'draft' check (status in ('draft', 'active', 'suspended')),
  photo_verified boolean not null default false
);

-- 2-3. 비공개 개인정보 (직접 접근 불가)
create table private.user_private (
  user_id uuid primary key references auth.users(id) on delete cascade,
  birth_date date not null
);

-- 2-4. 운영자 목록 (슈퍼유저가 관리, 직접 접근 불가)
create table private.admins (
  user_id uuid primary key references auth.users(id) on delete cascade
);

-- 2-5. 선호 조건 (본인만 조회/생성/수정)
create table public.preferences (
  user_id uuid primary key references auth.users(id) on delete cascade,
  min_age int not null default 19,
  max_age int not null default 99,
  genders text[] not null,
  constraint preferences_age_range_check check (
    min_age >= 19 and max_age <= 99 and min_age <= max_age
  ),
  constraint preferences_genders_check check (
    genders <@ array['man', 'woman']::text[]
    and pg_catalog.array_position(genders, null) is null
  )
);

-- 2-6. 스와이프 (본인이 보낸 것만 조회, 쓰기는 swipe() 함수로만)
create table public.swipes (
  from_id uuid not null references auth.users(id) on delete cascade,
  to_id uuid not null references auth.users(id) on delete cascade,
  action text not null check (action in ('like', 'pass')),
  created_at timestamptz not null default now(),
  primary key (from_id, to_id),
  constraint swipes_no_self_check check (from_id <> to_id)
);

-- 2-7. 매칭 (당사자만 조회, 직접 쓰기 불가)
create table public.matches (
  id uuid primary key default gen_random_uuid(),
  user_a uuid not null references auth.users(id) on delete cascade,
  user_b uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  ended_at timestamptz,
  constraint matches_user_order_check check (user_a < user_b),
  constraint matches_pair_unique unique (user_a, user_b)
);

-- 2-8. 메시지 (매칭 당사자만 조회, 쓰기는 send_message() 함수로만)
create table public.messages (
  id uuid primary key default gen_random_uuid(),
  match_id uuid not null references public.matches(id) on delete cascade,
  sender_id uuid not null references auth.users(id) on delete cascade,
  body text not null check (char_length(body) between 1 and 2000),
  created_at timestamptz not null default now()
);

-- 2-9. 차단 (본인이 한 차단만 조회, 쓰기는 block_user() 함수로만)
create table public.blocks (
  blocker_id uuid not null references auth.users(id) on delete cascade,
  blocked_id uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (blocker_id, blocked_id),
  constraint blocks_no_self_check check (blocker_id <> blocked_id)
);

-- 3. 인덱스
create index idx_swipes_to_from on public.swipes (to_id, from_id);
create index idx_matches_user_b on public.matches (user_b);
create index idx_messages_match_created on public.messages (match_id, created_at);
create index idx_blocks_blocked on public.blocks (blocked_id, blocker_id);

-- 4. profiles insert 시 member_status 자동 생성 트리거
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

create trigger trg_profiles_create_member_status
  after insert on public.profiles
  for each row
  execute function private.handle_new_profile();

-- 5. 테이블 권한 회수 및 최소 권한 부여
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

-- 6. RLS 활성화 및 정책 설정
alter table public.profiles enable row level security;
alter table public.member_status enable row level security;
alter table public.preferences enable row level security;
alter table public.swipes enable row level security;
alter table public.matches enable row level security;
alter table public.messages enable row level security;
alter table public.blocks enable row level security;
alter table private.user_private enable row level security;
alter table private.admins enable row level security;

-- profiles: 본인만 조회/생성/수정
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

-- member_status: 본인만 조회
create policy member_status_select_own on public.member_status
  for select to authenticated
  using (user_id = auth.uid());

-- preferences: 본인만 조회/생성/수정
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

-- swipes: 본인이 보낸 것만 조회
create policy swipes_select_own on public.swipes
  for select to authenticated
  using (from_id = auth.uid());

-- matches: 당사자만 조회
create policy matches_select_participant on public.matches
  for select to authenticated
  using (user_a = auth.uid() or user_b = auth.uid());

-- messages: 매칭 당사자만 조회
create policy messages_select_participant on public.messages
  for select to authenticated
  using (
    exists (
      select 1
      from public.matches m
      where m.id = match_id
        and (m.user_a = auth.uid() or m.user_b = auth.uid())
    )
  );

-- blocks: 본인이 한 차단만 조회
create policy blocks_select_own on public.blocks
  for select to authenticated
  using (blocker_id = auth.uid());

-- 7. 핵심 함수 (모두 public 스키마, security definer, search_path 고정)

-- 7-1. set_birth_date(d date) returns void
create function public.set_birth_date(d date)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid;
  v_age int;
begin
  v_uid := auth.uid();
  if v_uid is null then
    raise exception 'not authenticated' using errcode = '42501';
  end if;

  if d is null or not pg_catalog.isfinite(d) then
    raise exception 'valid birth_date is required' using errcode = '22023';
  end if;

  v_age := extract(year from pg_catalog.age(current_date, d))::int;
  if v_age < 19 then
    raise exception 'must be at least 19 years old' using errcode = '22023';
  end if;

  insert into private.user_private (user_id, birth_date)
  values (v_uid, d)
  on conflict (user_id) do update
    set birth_date = excluded.birth_date;
end;
$$;

revoke all on function public.set_birth_date(date) from public, anon, authenticated;
grant execute on function public.set_birth_date(date) to authenticated;

-- 7-2. admin_set_status(target uuid, new_status text, verified boolean) returns void
create function public.admin_set_status(target uuid, new_status text, verified boolean)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid;
begin
  v_uid := auth.uid();
  if v_uid is null then
    raise exception 'not authenticated' using errcode = '42501';
  end if;

  if not exists (select 1 from private.admins a where a.user_id = v_uid) then
    raise exception 'admin privilege required' using errcode = '42501';
  end if;

  if target is null then
    raise exception 'target is required' using errcode = '22004';
  end if;

  if new_status is null or new_status not in ('draft', 'active', 'suspended') then
    raise exception 'invalid status' using errcode = '22023';
  end if;

  if verified is null then
    raise exception 'verified is required' using errcode = '22004';
  end if;

  insert into public.member_status (user_id, status, photo_verified)
  values (target, new_status, verified)
  on conflict (user_id) do update
    set status = excluded.status,
        photo_verified = excluded.photo_verified;
end;
$$;

revoke all on function public.admin_set_status(uuid, text, boolean) from public, anon, authenticated;
grant execute on function public.admin_set_status(uuid, text, boolean) to authenticated;

-- 7-3. get_candidates(lim int default 20)
create function public.get_candidates(lim int default 20)
returns table(
  id uuid,
  nickname text,
  age int,
  gender text,
  region text,
  bio text
)
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  v_uid uuid;
begin
  v_uid := auth.uid();
  if v_uid is null then
    raise exception 'not authenticated' using errcode = '42501';
  end if;

  if not exists (
    select 1
    from public.member_status ms
    where ms.user_id = v_uid
      and ms.status = 'active'
      and ms.photo_verified = true
  ) then
    raise exception 'caller is not eligible' using errcode = '42501';
  end if;

  if lim is not null and lim < 0 then
    raise exception 'limit must not be negative' using errcode = '2201W';
  end if;

  return query
  with me as (
    select
      p.id as uid,
      p.gender,
      pref.min_age,
      pref.max_age,
      pref.genders,
      extract(year from pg_catalog.age(current_date, up.birth_date))::int as age
    from public.profiles p
    join public.preferences pref on pref.user_id = p.id
    join private.user_private up on up.user_id = p.id
    where p.id = v_uid
  )
  select
    cp.id,
    cp.nickname,
    extract(year from pg_catalog.age(current_date, cup.birth_date))::int as age,
    cp.gender,
    cp.region,
    cp.bio
  from me
  join public.profiles cp on cp.id <> me.uid
  join public.member_status cms
    on cms.user_id = cp.id
   and cms.status = 'active'
   and cms.photo_verified = true
  join public.preferences cpref on cpref.user_id = cp.id
  join private.user_private cup on cup.user_id = cp.id
  where
    -- 서로의 성별 선호 만족
    cp.gender = any(me.genders)
    and me.gender = any(cpref.genders)
    -- 서로의 나이 범위 만족
    and extract(year from pg_catalog.age(current_date, cup.birth_date))::int between me.min_age and me.max_age
    and me.age between cpref.min_age and cpref.max_age
    -- 어느 쪽이든 차단 없음
    and not exists (
      select 1
      from public.blocks b
      where (b.blocker_id = me.uid and b.blocked_id = cp.id)
         or (b.blocker_id = cp.id and b.blocked_id = me.uid)
    )
    -- 내가 like한 사람 및 30일 안에 pass한 사람 제외
    and not exists (
      select 1
      from public.swipes s
      where s.from_id = me.uid
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
      where m.user_a = least(me.uid, cp.id)
        and m.user_b = greatest(me.uid, cp.id)
        and m.ended_at is null
    )
  order by cp.id
  limit coalesce(lim, 20);
end;
$$;

revoke all on function public.get_candidates(int) from public, anon, authenticated;
grant execute on function public.get_candidates(int) to authenticated;

-- 7-4. swipe(target uuid, act text) returns uuid
create function public.swipe(target uuid, act text)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid;
  v_user_a uuid;
  v_user_b uuid;
  v_match_id uuid;
begin
  v_uid := auth.uid();
  if v_uid is null then
    raise exception 'not authenticated' using errcode = '42501';
  end if;

  if target is null then
    raise exception 'target is required' using errcode = '22004';
  end if;

  if target = v_uid then
    raise exception 'cannot swipe yourself' using errcode = '22023';
  end if;

  if act is null or act not in ('like', 'pass') then
    raise exception 'invalid swipe action' using errcode = '22023';
  end if;

  -- 본인 자격 확인
  if not exists (
    select 1
    from public.member_status ms
    where ms.user_id = v_uid
      and ms.status = 'active'
      and ms.photo_verified = true
  ) then
    raise exception 'caller is not eligible' using errcode = '42501';
  end if;

  -- 상대 자격 확인
  if not exists (
    select 1
    from public.member_status ms
    where ms.user_id = target
      and ms.status = 'active'
      and ms.photo_verified = true
  ) then
    raise exception 'target is not eligible' using errcode = '22023';
  end if;

  -- 차단 관계 확인 (양방향)
  if exists (
    select 1
    from public.blocks b
    where (b.blocker_id = v_uid and b.blocked_id = target)
       or (b.blocker_id = target and b.blocked_id = v_uid)
  ) then
    raise exception 'blocked relationship' using errcode = '42501';
  end if;

  v_user_a := least(v_uid, target);
  v_user_b := greatest(v_uid, target);

  -- 동시 상호 like 시 중복 매칭·경쟁 상태 방지
  perform pg_catalog.pg_advisory_xact_lock(
    pg_catalog.hashtextextended(v_user_a::text || ':' || v_user_b::text, 0)
  );

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
    insert into public.matches (user_a, user_b)
    values (v_user_a, v_user_b)
    on conflict (user_a, user_b) do update
      set ended_at = null
    returning id into v_match_id;

    return v_match_id;
  end if;

  return null;
end;
$$;

revoke all on function public.swipe(uuid, text) from public, anon, authenticated;
grant execute on function public.swipe(uuid, text) to authenticated;

-- 7-5. send_message(mid uuid, body text) returns uuid
create function public.send_message(mid uuid, body text)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid;
  v_user_a uuid;
  v_user_b uuid;
  v_ended_at timestamptz;
  v_other uuid;
  v_msg_id uuid;
begin
  v_uid := auth.uid();
  if v_uid is null then
    raise exception 'not authenticated' using errcode = '42501';
  end if;

  if mid is null then
    raise exception 'match_id is required' using errcode = '22004';
  end if;

  if send_message.body is null
     or char_length(send_message.body) < 1
     or char_length(send_message.body) > 2000 then
    raise exception 'message body must be 1 to 2000 characters' using errcode = '22023';
  end if;

  select m.user_a, m.user_b, m.ended_at
  into v_user_a, v_user_b, v_ended_at
  from public.matches m
  where m.id = mid;

  if not found then
    raise exception 'match not found' using errcode = '42501';
  end if;

  if v_user_a <> v_uid and v_user_b <> v_uid then
    raise exception 'not a participant of this match' using errcode = '42501';
  end if;

  if v_ended_at is not null then
    raise exception 'match has ended' using errcode = '22023';
  end if;

  v_other := case when v_user_a = v_uid then v_user_b else v_user_a end;

  if exists (
    select 1
    from public.blocks b
    where (b.blocker_id = v_uid and b.blocked_id = v_other)
       or (b.blocker_id = v_other and b.blocked_id = v_uid)
  ) then
    raise exception 'blocked relationship' using errcode = '42501';
  end if;

  insert into public.messages (match_id, sender_id, body)
  values (mid, v_uid, send_message.body)
  returning id into v_msg_id;

  return v_msg_id;
end;
$$;

revoke all on function public.send_message(uuid, text) from public, anon, authenticated;
grant execute on function public.send_message(uuid, text) to authenticated;

-- 7-6. block_user(target uuid) returns void
create function public.block_user(target uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid;
begin
  v_uid := auth.uid();
  if v_uid is null then
    raise exception 'not authenticated' using errcode = '42501';
  end if;

  if target is null then
    raise exception 'target is required' using errcode = '22004';
  end if;

  if target = v_uid then
    raise exception 'cannot block yourself' using errcode = '22023';
  end if;

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

revoke all on function public.block_user(uuid) from public, anon, authenticated;
grant execute on function public.block_user(uuid) to authenticated;

-- 7-7. delete_my_account() returns void
create function public.delete_my_account()
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid;
begin
  v_uid := auth.uid();
  if v_uid is null then
    raise exception 'not authenticated' using errcode = '42501';
  end if;

  delete from auth.users where id = v_uid;
end;
$$;

revoke all on function public.delete_my_account() from public, anon, authenticated;
grant execute on function public.delete_my_account() to authenticated;
