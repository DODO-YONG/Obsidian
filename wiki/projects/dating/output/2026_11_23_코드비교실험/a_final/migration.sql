-- 소개팅 앱 1단계: 테이블 + RLS + 핵심 함수
-- 전제: anon/authenticated 역할, auth.users, auth.uid()는 이미 있음.


-- ───────────────────────── 스키마 ─────────────────────────
create schema if not exists private;
revoke all on schema private from public, anon, authenticated;

-- ───────────────────────── 테이블 ─────────────────────────
create table public.profiles (
  id       uuid primary key references auth.users(id) on delete cascade,
  nickname text not null check (char_length(nickname) between 2 and 20),
  gender   text not null check (gender in ('man','woman')),
  region   text not null,
  bio      text not null default '' check (char_length(bio) <= 500)
);

create table public.member_status (
  user_id        uuid primary key references auth.users(id) on delete cascade,
  status         text not null default 'draft' check (status in ('draft','active','suspended')),
  photo_verified boolean not null default false
);

create table private.user_private (
  user_id    uuid primary key references auth.users(id) on delete cascade,
  birth_date date not null
);

create table private.admins (
  user_id uuid primary key references auth.users(id) on delete cascade
);

create index member_status_eligible_idx on public.member_status(user_id)
  where status = 'active' and photo_verified;

create table public.preferences (
  user_id uuid primary key references auth.users(id) on delete cascade,
  min_age int not null default 19,
  max_age int not null default 99,
  genders text[] not null check (genders <@ array['man','woman']::text[]),
  check (19 <= min_age and min_age <= max_age and max_age <= 99)
);

create table public.swipes (
  from_id    uuid not null references auth.users(id) on delete cascade,
  to_id      uuid not null references auth.users(id) on delete cascade,
  action     text not null check (action in ('like','pass')),
  created_at timestamptz not null default now(),
  primary key (from_id, to_id),
  check (from_id <> to_id)
);
create index swipes_to_idx on public.swipes(to_id);

create table public.matches (
  id         uuid primary key default gen_random_uuid(),
  user_a     uuid not null references auth.users(id) on delete cascade,
  user_b     uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  ended_at   timestamptz,
  check (user_a < user_b),
  unique (user_a, user_b)
);
create index matches_user_b_idx on public.matches(user_b);

create table public.messages (
  id         uuid primary key default gen_random_uuid(),
  match_id   uuid not null references public.matches(id) on delete cascade,
  sender_id  uuid not null references auth.users(id) on delete cascade,
  body       text not null check (char_length(body) between 1 and 2000),
  created_at timestamptz not null default now()
);
create index messages_match_idx on public.messages(match_id, created_at);
create index messages_sender_idx on public.messages(sender_id);

create table public.blocks (
  blocker_id uuid not null references auth.users(id) on delete cascade,
  blocked_id uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (blocker_id, blocked_id),
  check (blocker_id <> blocked_id)
);
create index blocks_blocked_idx on public.blocks(blocked_id);

-- ───────────────────────── RLS ─────────────────────────
alter table public.profiles      enable row level security;
alter table public.member_status enable row level security;
alter table public.preferences   enable row level security;
alter table public.swipes        enable row level security;
alter table public.matches       enable row level security;
alter table public.messages      enable row level security;
alter table public.blocks        enable row level security;
alter table private.user_private enable row level security;
alter table private.admins       enable row level security;

create policy profiles_select_own on public.profiles for select to authenticated
  using (id = (select auth.uid()));
create policy profiles_insert_own on public.profiles for insert to authenticated
  with check (id = (select auth.uid()));
create policy profiles_update_own on public.profiles for update to authenticated
  using (id = (select auth.uid())) with check (id = (select auth.uid()));

create policy member_status_select_own on public.member_status for select to authenticated
  using (user_id = (select auth.uid()));

create policy preferences_select_own on public.preferences for select to authenticated
  using (user_id = (select auth.uid()));
create policy preferences_insert_own on public.preferences for insert to authenticated
  with check (user_id = (select auth.uid()));
create policy preferences_update_own on public.preferences for update to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));

create policy swipes_select_own on public.swipes for select to authenticated
  using (from_id = (select auth.uid()));

create policy matches_select_party on public.matches for select to authenticated
  using ((select auth.uid()) in (user_a, user_b));

create policy messages_select_party on public.messages for select to authenticated
  using (exists (select 1 from public.matches m
                 where m.id = messages.match_id
                   and (select auth.uid()) in (m.user_a, m.user_b)));

create policy blocks_select_own on public.blocks for select to authenticated
  using (blocker_id = (select auth.uid()));

-- ───────────────────────── 내부 도우미(private, 사용자 호출 불가) ─────────────────────────
-- 기준 날짜는 세션 TimeZone과 무관하게 서비스 기준(Asia/Seoul)으로 고정. 매일 바뀌므로 stable.
create function private.today() returns date
language sql stable set search_path = '' as $$
  select (pg_catalog.now() at time zone 'Asia/Seoul')::date
$$;

create function private.age_of(d date) returns int
language sql stable set search_path = '' as $$
  select extract(year from pg_catalog.age(private.today()::timestamp, d::timestamp))::int
$$;

-- 쌍 단위 잠금(swipe·block_user·send_message가 같은 키로 직렬화)
create function private.lock_pair(a uuid, b uuid) returns void
language sql volatile set search_path = '' as $$
  select pg_catalog.pg_advisory_xact_lock(
    pg_catalog.hashtextextended('dating_pair:' || least(a, b)::text || ':' || greatest(a, b)::text, 0))
$$;

create function private.is_eligible(u uuid) returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.member_status s
                 where s.user_id = u and s.status = 'active' and s.photo_verified)
$$;

create function private.is_blocked(a uuid, b uuid) returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.blocks k
                 where (k.blocker_id = a and k.blocked_id = b)
                    or (k.blocker_id = b and k.blocked_id = a))
$$;

-- profiles insert → member_status 자동 생성
create function private.on_profile_insert() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  insert into public.member_status(user_id) values (new.id)
  on conflict (user_id) do nothing;
  return new;
end $$;

create trigger profiles_create_status after insert on public.profiles
  for each row execute function private.on_profile_insert();

-- ───────────────────────── 공개 함수 ─────────────────────────
create function public.set_birth_date(d date) returns void
language plpgsql security definer set search_path = '' as $$
declare me uuid := auth.uid();
begin
  if me is null then raise exception 'not authenticated' using errcode = '42501'; end if;
  if d is null then raise exception 'birth date required'; end if;
  if private.age_of(d) < 19 then raise exception 'must be 19 or older'; end if;
  insert into private.user_private(user_id, birth_date) values (me, d)
  on conflict (user_id) do update set birth_date = excluded.birth_date;
end $$;

create function public.admin_set_status(target uuid, new_status text, verified boolean) returns void
language plpgsql security definer set search_path = '' as $$
declare me uuid := auth.uid();
begin
  if me is null or not exists (select 1 from private.admins a where a.user_id = me) then
    raise exception 'admin only' using errcode = '42501';
  end if;
  if target is null then raise exception 'target required'; end if;
  if new_status is null or new_status not in ('draft','active','suspended') then
    raise exception 'invalid status';
  end if;
  if verified is null then raise exception 'verified required'; end if;
  insert into public.member_status(user_id, status, photo_verified)
  values (target, new_status, verified)
  on conflict (user_id) do update
    set status = excluded.status, photo_verified = excluded.photo_verified;
end $$;

create function public.get_candidates(lim int default 20)
returns table(id uuid, nickname text, age int, gender text, region text, bio text)
language plpgsql stable security definer set search_path = '' as $$
#variable_conflict use_column
declare me uuid := auth.uid();
begin
  if me is null then raise exception 'not authenticated' using errcode = '42501'; end if;
  if not private.is_eligible(me) then raise exception 'not eligible'; end if;

  return query
  with mine as (
    select p.gender as g, private.age_of(u.birth_date) as a,
           f.min_age, f.max_age, f.genders,
           -- 내 나이 범위를 상대 생년월일 범위로 변환(인덱스 가능한 범위 조건)
           (private.today() - pg_catalog.make_interval(years => f.min_age))::date as born_before_eq,
           (private.today() - pg_catalog.make_interval(years => f.max_age + 1))::date as born_after
    from public.profiles p
    join private.user_private u on u.user_id = p.id
    join public.preferences f on f.user_id = p.id
    where p.id = me
  )
  select c.id, c.nickname, private.age_of(cu.birth_date), c.gender, c.region, c.bio
  from mine
  join public.profiles c on c.id <> me
  join public.member_status cs on cs.user_id = c.id and cs.status = 'active' and cs.photo_verified
  join private.user_private cu on cu.user_id = c.id
  join public.preferences cf on cf.user_id = c.id
  where c.gender = any (mine.genders)
    and cu.birth_date <= mine.born_before_eq
    and cu.birth_date >  mine.born_after
    and mine.g = any (cf.genders)
    and mine.a between cf.min_age and cf.max_age
    and not exists (select 1 from public.blocks k where k.blocker_id = me and k.blocked_id = c.id)
    and not exists (select 1 from public.blocks k where k.blocker_id = c.id and k.blocked_id = me)
    and not exists (select 1 from public.swipes s
                    where s.from_id = me and s.to_id = c.id
                      and (s.action = 'like'
                           or (s.action = 'pass' and s.created_at > now() - interval '30 days')))
    and not exists (select 1 from public.matches m
                    where m.user_a = least(me, c.id) and m.user_b = greatest(me, c.id)
                      and m.ended_at is null)
  order by c.id
  limit least(greatest(coalesce(lim, 20), 0), 100);
end $$;

create function public.swipe(target uuid, act text) returns uuid
language plpgsql security definer set search_path = '' as $$
declare
  me  uuid := auth.uid();
  mid uuid;
begin
  if me is null then raise exception 'not authenticated' using errcode = '42501'; end if;
  if target is null then raise exception 'target required'; end if;
  if act is null or act not in ('like','pass') then raise exception 'invalid action'; end if;
  if target = me then raise exception 'cannot swipe yourself'; end if;

  -- 검사 전에 쌍 단위 잠금(동시 like·block_user와 직렬화, TOCTOU 방지)
  perform private.lock_pair(me, target);

  if not private.is_eligible(me) then raise exception 'not eligible'; end if;
  -- 상대 자격·차단 여부를 구분해 알려 주지 않도록 같은 메시지
  if not private.is_eligible(target) or private.is_blocked(me, target) then
    raise exception 'cannot swipe target';
  end if;

  insert into public.swipes(from_id, to_id, action, created_at)
  values (me, target, act, now())
  on conflict (from_id, to_id) do update
    set action = excluded.action, created_at = excluded.created_at;

  if act = 'like' and exists (select 1 from public.swipes s
                              where s.from_id = target and s.to_id = me and s.action = 'like') then
    insert into public.matches(user_a, user_b)
    values (least(me, target), greatest(me, target))
    on conflict (user_a, user_b) do nothing
    returning id into mid;
    if mid is null then
      select m.id into mid from public.matches m
      where m.user_a = least(me, target) and m.user_b = greatest(me, target);
    end if;
    return mid;
  end if;
  return null;
end $$;

create function public.send_message(mid uuid, body text) returns uuid
language plpgsql security definer set search_path = '' as $$
declare
  me    uuid := auth.uid();
  m     public.matches%rowtype;
  other uuid;
  new_id uuid;
begin
  if me is null then raise exception 'not authenticated' using errcode = '42501'; end if;
  select * into m from public.matches x where x.id = mid;
  if not found or me not in (m.user_a, m.user_b) then
    raise exception 'not a party of this match' using errcode = '42501';
  end if;
  -- block_user와 직렬화한 뒤 최신 상태로 다시 읽고 검사
  perform private.lock_pair(m.user_a, m.user_b);
  select * into m from public.matches x where x.id = mid for share;
  if not found then raise exception 'not a party of this match' using errcode = '42501'; end if;
  if m.ended_at is not null then raise exception 'match ended'; end if;
  other := case when m.user_a = me then m.user_b else m.user_a end;
  if private.is_blocked(me, other) then raise exception 'blocked'; end if;
  if body is null or char_length(body) not between 1 and 2000 then
    raise exception 'body must be 1-2000 chars';
  end if;
  insert into public.messages(match_id, sender_id, body)
  values (mid, me, body) returning id into new_id;
  return new_id;
end $$;

create function public.block_user(target uuid) returns void
language plpgsql security definer set search_path = '' as $$
declare me uuid := auth.uid();
begin
  if me is null then raise exception 'not authenticated' using errcode = '42501'; end if;
  if target is null then raise exception 'target required'; end if;
  if target = me then raise exception 'cannot block yourself'; end if;
  perform private.lock_pair(me, target);
  insert into public.blocks(blocker_id, blocked_id) values (me, target)
  on conflict (blocker_id, blocked_id) do nothing;
  update public.matches set ended_at = now()
  where user_a = least(me, target) and user_b = greatest(me, target) and ended_at is null;
end $$;

create function public.delete_my_account() returns void
language plpgsql security definer set search_path = '' as $$
declare me uuid := auth.uid();
begin
  if me is null then raise exception 'not authenticated' using errcode = '42501'; end if;
  delete from auth.users where id = me;
end $$;

-- ───────────────────────── 권한 (기본 부여 회수 후 최소 부여) ─────────────────────────
-- public 스키마의 다른 객체는 건드리지 않도록 이 파일이 만든 객체만 이름으로 회수
revoke all on public.profiles, public.member_status, public.preferences, public.swipes,
              public.matches, public.messages, public.blocks
  from public, anon, authenticated;
revoke all on function public.set_birth_date(date), public.admin_set_status(uuid, text, boolean),
              public.get_candidates(int), public.swipe(uuid, text), public.send_message(uuid, text),
              public.block_user(uuid), public.delete_my_account()
  from public, anon, authenticated;
revoke all on all tables    in schema private from public, anon, authenticated;
revoke all on all functions in schema private from public, anon, authenticated;

grant select                                                  on public.profiles to authenticated;
grant insert (id, nickname, gender, region, bio)              on public.profiles to authenticated;
grant update (id, nickname, gender, region, bio)              on public.profiles to authenticated;
grant select                                                  on public.member_status to authenticated;
grant select                                                  on public.preferences to authenticated;
grant insert (user_id, min_age, max_age, genders)             on public.preferences to authenticated;
grant update (user_id, min_age, max_age, genders)             on public.preferences to authenticated;
grant select on public.swipes, public.matches, public.messages, public.blocks to authenticated;

grant execute on function public.set_birth_date(date)                      to authenticated;
grant execute on function public.admin_set_status(uuid, text, boolean)     to authenticated;
grant execute on function public.get_candidates(int)                       to authenticated;
grant execute on function public.swipe(uuid, text)                         to authenticated;
grant execute on function public.send_message(uuid, text)                  to authenticated;
grant execute on function public.block_user(uuid)                          to authenticated;
grant execute on function public.delete_my_account()                       to authenticated;
