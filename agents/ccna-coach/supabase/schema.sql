-- ─────────────────────────────────────────────────────────────────────────────
-- DY-003 TRACER · Supabase 스키마
-- 사용법: Supabase 대시보드 → SQL Editor → 이 파일 내용을 통째로 붙여 넣고 Run. (여러 번 실행해도 안전)
--
-- 보안 원칙
-- - 브라우저는 DB에 직접 접근하지 않는다. 로그인(Supabase Auth)만 브라우저가 하고,
--   모든 읽기·쓰기는 Vercel /api 함수가 비밀 키(service_role)로 한다.
-- - 그래서 모든 표에 RLS를 켜고 anon·authenticated 정책은 하나도 만들지 않는다(= 직접 접근 전부 거부).
-- - 정답·해설은 이 DB에만 있고, 채점 요청 때 /api가 필요한 만큼만 화면에 보낸다.
-- ─────────────────────────────────────────────────────────────────────────────

-- 사용자 (Supabase Auth의 auth.users 와 1:1). 권한도 여기 함께 둔다.
create table if not exists public.profiles (
  id            uuid primary key references auth.users (id) on delete cascade,
  email         text,
  name          text,
  role          text not null default 'user'   check (role in ('owner', 'admin', 'user')),
  status        text not null default 'active' check (status in ('active', 'pending', 'blocked')),
  can_practice  boolean not null default true,   -- AI 문제(객관식·주관식) 받기
  can_explain   boolean not null default true,   -- 내 문제 해설
  daily_limit   integer not null default 30 check (daily_limit >= 0),  -- 하루 제미나이 호출 한도(owner는 무시)
  note          text,                              -- 관리자 메모
  created_at    timestamptz not null default now(),
  last_seen     timestamptz
);

-- 활동 기록: 누가·언제·무엇을·어떤 기기로. IP는 저장하지 않는다.
create table if not exists public.activity_log (
  id       bigint generated always as identity primary key,
  user_id  uuid references public.profiles (id) on delete cascade,
  action   text not null,          -- visit · question · grade · explain · subnet · report · admin
  detail   jsonb not null default '{}'::jsonb,
  ai       boolean not null default false,   -- 제미나이를 실제로 불렀는가
  counted  boolean not null default false,   -- 전체 하루 한도에 들어가는가(ai 이고 owner 아님)
  device   text,
  at       timestamptz not null default now()
);
create index if not exists activity_user_at on public.activity_log (user_id, at desc);
create index if not exists activity_at on public.activity_log (at desc);

-- 문제 저장소. 묶음 = (sub, difficulty, qtype)
create table if not exists public.questions (
  id            uuid primary key default gen_random_uuid(),
  sub           text not null,
  difficulty    text not null check (difficulty in ('쉬움', '보통', '어려움')),
  qtype         text not null check (qtype in ('mcq', 'short')),
  question      text not null,
  choices       jsonb not null default '[]'::jsonb,   -- 객관식 보기 4개
  answer        text not null,                        -- 'A'~'D' 또는 주관식 모범 답안
  explanation   text,
  option_notes  jsonb not null default '[]'::jsonb,   -- 보기 A~D 각각 맞는/틀린 이유
  key_concept   text,
  cli_example   text,
  tip           text,
  model         text,
  norm_hash     text not null unique,                 -- 중복 문제 방지
  status        text not null default 'active' check (status in ('active', 'flagged', 'hidden')),
  served        integer not null default 0,
  graded        integer not null default 0,
  correct       integer not null default 0,
  reports       integer not null default 0,
  created_by    uuid references public.profiles (id) on delete set null,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);
create index if not exists questions_bucket on public.questions (sub, difficulty, qtype, status);

-- 누가 어떤 문제를 받았는지(같은 사람에게 반복 출제 방지 + 받은 문제만 채점 가능)
create table if not exists public.question_seen (
  user_id      uuid not null references public.profiles (id) on delete cascade,
  question_id  uuid not null references public.questions (id) on delete cascade,
  served_at    timestamptz not null default now(),
  graded_at    timestamptz,
  primary key (user_id, question_id)
);

-- 문제 신고
create table if not exists public.question_reports (
  id           bigint generated always as identity primary key,
  question_id  uuid not null references public.questions (id) on delete cascade,
  user_id      uuid references public.profiles (id) on delete cascade,
  reason       text,
  resolved     boolean not null default false,
  at           timestamptz not null default now(),
  unique (question_id, user_id)
);

-- 풀이 기록(진도 계산용)
create table if not exists public.attempts (
  id           bigint generated always as identity primary key,
  user_id      uuid not null references public.profiles (id) on delete cascade,
  question_id  uuid references public.questions (id) on delete set null,
  mode         text not null default 'practice',  -- practice · custom · retry(틀린 문제 다시 풀기, 진도 통계 제외)
  domain_id    text,
  sub          text,
  qtype        text,             -- mcq · short · subnet · custom
  difficulty   text,
  verdict      text,             -- 정답 · 부분 정답 · 오답
  question     text,
  user_answer  text,
  at           timestamptz not null default now()
);
create index if not exists attempts_user_at on public.attempts (user_id, at desc);

-- 게임 진행(XP·레벨·배지·퀘스트). 화면의 상태 객체를 그대로 저장.
create table if not exists public.progress (
  user_id     uuid primary key references public.profiles (id) on delete cascade,
  data        jsonb not null default '{}'::jsonb,
  updated_at  timestamptz not null default now()
);

-- ── RLS: 켜고 정책은 만들지 않는다(브라우저 직접 접근 차단) ──────────────────
alter table public.profiles          enable row level security;
alter table public.activity_log      enable row level security;
alter table public.questions         enable row level security;
alter table public.question_seen     enable row level security;
alter table public.question_reports  enable row level security;
alter table public.attempts          enable row level security;
alter table public.progress          enable row level security;

-- ── 함수(/api가 rpc로 부른다) ────────────────────────────────────────────────

-- 묶음 안의 출제 가능한 문제 수
create or replace function public.bucket_size(p_sub text, p_diff text, p_qtype text)
returns integer language sql stable set search_path = public as $$
  select count(*)::int from questions
  where sub = p_sub and difficulty = p_diff and qtype = p_qtype and status = 'active';
$$;

-- 이 사용자가 아직 안 받은 문제 하나를 무작위로
create or replace function public.pick_question(p_user uuid, p_sub text, p_diff text, p_qtype text)
returns setof public.questions language sql volatile set search_path = public as $$
  select q.* from questions q
  where q.sub = p_sub and q.difficulty = p_diff and q.qtype = p_qtype and q.status = 'active'
    and not exists (select 1 from question_seen s where s.user_id = p_user and s.question_id = q.id)
  order by random()
  limit 1;
$$;

-- 새로 만들 때 "이것과 겹치지 말 것"으로 넘길 최근 문제
create or replace function public.recent_in_bucket(p_sub text, p_diff text, p_qtype text, p_n int)
returns table (question text) language sql stable set search_path = public as $$
  select left(q.question, 120) from questions q
  where q.sub = p_sub and q.difficulty = p_diff and q.qtype = p_qtype
  order by q.created_at desc
  limit p_n;
$$;

-- 출제 1회 기록
create or replace function public.mark_served(p_user uuid, p_qid uuid)
returns void language sql volatile set search_path = public as $$
  insert into question_seen (user_id, question_id) values (p_user, p_qid)
  on conflict (user_id, question_id) do nothing;
  update questions set served = served + 1 where id = p_qid;
$$;

-- 채점 1회 기록. 이미 채점한 문제면 false(통계 중복 방지)
create or replace function public.mark_graded(p_user uuid, p_qid uuid, p_ok boolean)
returns boolean language plpgsql volatile set search_path = public as $$
declare n int;
begin
  update question_seen set graded_at = now()
  where user_id = p_user and question_id = p_qid and graded_at is null;
  get diagnostics n = row_count;
  if n = 0 then return false; end if;
  update questions set graded = graded + 1, correct = correct + (case when p_ok then 1 else 0 end)
  where id = p_qid;
  return true;
end $$;

-- 신고. 미해결 신고가 p_threshold 이상이면 출제 중지(flagged). 미해결 신고 수를 돌려준다
create or replace function public.report_question(p_qid uuid, p_user uuid, p_reason text, p_threshold int)
returns integer language plpgsql volatile set search_path = public as $$
declare n int;
begin
  insert into question_reports (question_id, user_id, reason) values (p_qid, p_user, left(p_reason, 500))
  on conflict (question_id, user_id) do update set reason = excluded.reason, resolved = false, at = now();
  select count(*) into n from question_reports where question_id = p_qid and not resolved;
  update questions set reports = n,
         status = case when n >= p_threshold and status = 'active' then 'flagged' else status end
  where id = p_qid;
  return n;
end $$;

-- 관리자: 사용자 목록 + 오늘(한국 시간) 사용량
create or replace function public.admin_users()
returns table (id uuid, email text, name text, role text, status text, can_practice boolean, can_explain boolean,
               daily_limit int, note text, created_at timestamptz, last_seen timestamptz,
               today_ai int, today_actions int, total_attempts int)
language sql stable set search_path = public as $$
  select p.id, p.email, p.name, p.role, p.status, p.can_practice, p.can_explain, p.daily_limit, p.note,
         p.created_at, p.last_seen,
         (select count(*)::int from activity_log a where a.user_id = p.id and a.ai
            and a.at >= (date_trunc('day', now() at time zone 'Asia/Seoul') at time zone 'Asia/Seoul')),
         (select count(*)::int from activity_log a where a.user_id = p.id
            and a.at >= (date_trunc('day', now() at time zone 'Asia/Seoul') at time zone 'Asia/Seoul')),
         (select count(*)::int from attempts t where t.user_id = p.id)
  from profiles p
  order by p.last_seen desc nulls last;
$$;

-- 관리자: 최근 p_days일(한국 날짜) 일별 접속자·제미나이 호출·저장소 출제·새 문제
create or replace function public.admin_daily(p_days int)
returns table (day date, visitors int, ai_calls int, bank_serves int, new_questions int, answers int)
language sql stable set search_path = public as $$
  with days as (
    select generate_series((now() at time zone 'Asia/Seoul')::date - (p_days - 1),
                           (now() at time zone 'Asia/Seoul')::date, interval '1 day')::date as day
  ), a as (
    select (at at time zone 'Asia/Seoul')::date as day, user_id, action, ai, detail from activity_log
    where at >= now() - make_interval(days => p_days + 1)
  )
  select d.day,
         (select count(distinct user_id)::int from a where a.day = d.day),
         (select count(*)::int from a where a.day = d.day and a.ai),
         (select count(*)::int from a where a.day = d.day and a.action = 'question' and a.detail->>'source' = 'bank'),
         (select count(*)::int from a where a.day = d.day and a.action = 'question' and a.detail->>'source' = 'new'),
         (select count(*)::int from a where a.day = d.day and a.action in ('grade', 'subnet'))
  from days d order by d.day;
$$;

-- 관리자: 묶음별 문제 수
create or replace function public.bank_buckets()
returns table (sub text, difficulty text, qtype text, active int, flagged int, hidden int)
language sql stable set search_path = public as $$
  select sub, difficulty, qtype,
         count(*) filter (where status = 'active')::int,
         count(*) filter (where status = 'flagged')::int,
         count(*) filter (where status = 'hidden')::int
  from questions group by sub, difficulty, qtype order by sub, difficulty, qtype;
$$;

-- ── 권한: /api(service_role)만. 2026년 이후 새 프로젝트는 명시적 grant가 필요 ──────
grant usage on schema public to service_role;
grant all on all tables in schema public to service_role;
grant all on all sequences in schema public to service_role;
revoke all on all tables in schema public from anon, authenticated;

do $$
declare f text;
begin
  foreach f in array array[
    'bucket_size(text,text,text)', 'pick_question(uuid,text,text,text)', 'recent_in_bucket(text,text,text,int)',
    'mark_served(uuid,uuid)', 'mark_graded(uuid,uuid,boolean)', 'report_question(uuid,uuid,text,int)',
    'admin_users()', 'admin_daily(int)', 'bank_buckets()'
  ] loop
    execute format('revoke execute on function public.%s from public, anon, authenticated', f);
    execute format('grant execute on function public.%s to service_role', f);
  end loop;
end $$;
