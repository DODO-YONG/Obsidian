-- ─────────────────────────────────────────────────────────────────────────────
-- DY-003 TRACER · 실제 관리자 화면용 추가 스키마 — 2026-11-23
-- 내용: 관리자 명령 기록 표(admin_command_log) + 기간별·단원별·리포트 집계 함수
-- 사용법: 기존 표·함수는 건드리지 않고 덧붙이기만 한다.
--         Supabase SQL Editor에서 이 파일만 실행하면 된다(여러 번 실행해도 안전).
--
-- 보안·기준 원칙
-- - 새 표는 RLS를 켜고 정책을 두지 않으며, 모든 함수는 service_role만 실행 가능.
-- - 모든 날짜·시각 집계는 한국(Asia/Seoul) 달력 기준.
-- ─────────────────────────────────────────────────────────────────────────────

-- 1) 관리자 명령 기록
create table if not exists public.admin_command_log (
  id         bigint generated always as identity primary key,
  admin_id   uuid references public.profiles (id) on delete set null,
  at         timestamptz not null default now(),
  session    text,
  text       text check (char_length(text) <= 300),
  path       text check (path in ('rules', 'ai', 'manual', 'sql')),
  conf       real,
  command    text,
  descr      text,
  steps      jsonb not null default '[]'::jsonb,
  st         text check (st in ('show', 'answer', 'done', 'wait', 'cancel', 'fail')),
  msg        text check (char_length(msg) <= 500),
  ms         integer,
  sql        text check (char_length(sql) <= 2000),
  undo_key   text,
  undone_at  timestamptz
);
create index if not exists admin_command_log_at on public.admin_command_log (at desc);

alter table public.admin_command_log enable row level security;
revoke all on public.admin_command_log from public, anon, authenticated;
grant usage on schema public to service_role;
grant all on public.admin_command_log to service_role;
grant all on all sequences in schema public to service_role;

-- 2) 기간별 요약 집계: [p_from, p_to)
create or replace function public.admin_period(p_from timestamptz, p_to timestamptz)
returns json language sql stable set search_path = public as $$
  with a as (
    select
      count(distinct user_id)::int as visitors,
      count(*) filter (where action in ('grade', 'subnet'))::int as answers,
      count(*) filter (where ai)::int as ai_calls,
      count(*) filter (where action = 'grade')::int as graded,
      count(*) filter (where action = 'grade' and detail->>'verdict' = '정답')::int as correct
    from activity_log
    where at >= p_from and at < p_to
  )
  select json_build_object(
    'visitors', a.visitors,
    'answers',  a.answers,
    'ai_calls', a.ai_calls,
    'signups',  (select count(*)::int from profiles where created_at >= p_from and created_at < p_to),
    'graded',   a.graded,
    'correct',  a.correct,
    'rate',     case when a.graded > 0 then round(a.correct * 100.0 / a.graded, 1) else null end
  )
  from a;
$$;

-- 3) 최근 p_days일 단원(detail->>'sub')별 채점 정답률(낮은 순)
create or replace function public.admin_sub_stats(p_days int)
returns table (sub text, graded int, correct int, users int, rate numeric)
language sql stable set search_path = public as $$
  with g as (
    select
      detail->>'sub' as sub,
      count(*)::int as graded,
      count(*) filter (where detail->>'verdict' = '정답')::int as correct,
      count(distinct user_id)::int as users
    from activity_log
    where action = 'grade'
      and at >= now() - make_interval(days => greatest(1, coalesce(p_days, 1)))
      and nullif(detail->>'sub', '') is not null
    group by detail->>'sub'
  )
  select
    g.sub,
    g.graded,
    g.correct,
    g.users,
    round(g.correct * 100.0 / g.graded, 1) as rate
  from g
  order by rate asc, g.graded desc, g.sub asc;
$$;

-- 4-내부) 리포트용 구간 집계: [p_from, p_to)
create or replace function public._admin_report_agg(p_from timestamptz, p_to timestamptz)
returns json language sql stable set search_path = public as $$
  with logs as (
    select user_id, action, ai, detail, device, at
    from activity_log
    where at >= p_from and at < p_to
  ),
  base as (
    select
      count(*)::int as total,
      count(*) filter (where ai)::int as ai,
      count(distinct user_id)::int as active_users,
      count(*) filter (where action = 'grade')::int as graded,
      count(*) filter (where action = 'grade' and detail->>'verdict' = '정답')::int as correct
    from logs
  ),
  act as (
    select coalesce(json_object_agg(action, cnt), '{}'::json) as j
    from (
      select action, count(*)::int as cnt
      from logs
      group by action
    ) s
  ),
  dev as (
    select coalesce(json_object_agg(dev, cnt), '{}'::json) as j
    from (
      select coalesce(nullif(device, ''), '알 수 없음') as dev, count(*)::int as cnt
      from logs
      group by 1
    ) s
  ),
  hr as (
    select json_agg(coalesce(h.cnt, 0) order by gs.hr) as j
    from generate_series(0, 23) as gs(hr)
    left join (
      select extract(hour from at at time zone 'Asia/Seoul')::int as hr,
             count(*)::int as cnt
      from logs
      group by 1
    ) h on h.hr = gs.hr
  )
  select json_build_object(
    'total',        base.total,
    'ai',           base.ai,
    'active_users', base.active_users,
    'signups',      (select count(*)::int from profiles where created_at >= p_from and created_at < p_to),
    'graded',       base.graded,
    'correct',      base.correct,
    'rate',         case when base.graded > 0 then round(base.correct * 100.0 / base.graded, 1) else null end,
    'by_action',    act.j,
    'by_device',    dev.j,
    'by_hour',      hr.j
  )
  from base, act, dev, hr;
$$;

-- 4) 관리자 리포트: 한국 달력 기준 오늘 포함 n일(1~365) + 직전 동기간 비교
create or replace function public.admin_report(p_days int)
returns json language plpgsql stable set search_path = public as $$
declare
  v_n            int;
  v_now          timestamptz;
  v_today        date;
  v_from         timestamptz;
  v_pfrom        timestamptz;
  v_prev_partial boolean;
  v_top_users    json;
  v_daily        json;
begin
  v_n     := least(365, greatest(1, coalesce(p_days, 1)));
  v_now   := now();
  v_today := (v_now at time zone 'Asia/Seoul')::date;
  v_from  := ((v_today - (v_n - 1))::timestamp at time zone 'Asia/Seoul');
  v_pfrom := ((v_today - (2 * v_n - 1))::timestamp at time zone 'Asia/Seoul');

  select coalesce(v_pfrom < min(at), true)
  into v_prev_partial
  from activity_log;

  select coalesce(
    json_agg(
      json_build_object('name', t.name, 'email', t.email, 'n', t.n)
      order by t.n desc, t.id asc
    ),
    '[]'::json
  )
  into v_top_users
  from (
    select p.id, p.name, p.email, count(*)::int as n
    from activity_log a
    join profiles p on p.id = a.user_id
    where a.at >= v_from and a.at < v_now
      and a.action <> 'admin'
    group by p.id, p.name, p.email
    order by n desc, p.id asc
    limit 5
  ) t;

  select json_agg(
    json_build_object(
      'day',   to_char(d.day, 'YYYY-MM-DD'),
      'total', coalesce(a.total, 0),
      'users', coalesce(a.users, 0)
    )
    order by d.day asc
  )
  into v_daily
  from (
    select (v_today - (v_n - 1) + g.i) as day
    from generate_series(0, v_n - 1) as g(i)
  ) d
  left join (
    select
      (at at time zone 'Asia/Seoul')::date as day,
      count(*)::int as total,
      count(distinct user_id)::int as users
    from activity_log
    where at >= v_from and at < v_now
    group by 1
  ) a on a.day = d.day;

  return json_build_object(
    'days',         v_n,
    'cur',          public._admin_report_agg(v_from, v_now),
    'prev',         public._admin_report_agg(v_pfrom, v_from),
    'prev_partial', v_prev_partial,
    'top_users',    v_top_users,
    'daily',        v_daily
  );
end $$;

-- ── 함수 실행 권한: service_role만 ───────────────────────────────────────────
do $$
declare f text;
begin
  foreach f in array array[
    'admin_period(timestamptz,timestamptz)',
    'admin_sub_stats(int)',
    '_admin_report_agg(timestamptz,timestamptz)',
    'admin_report(int)'
  ] loop
    execute format('revoke execute on function public.%s from public, anon, authenticated', f);
    execute format('grant execute on function public.%s to service_role', f);
  end loop;
end $$;
