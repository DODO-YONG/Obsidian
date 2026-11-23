-- 관리자 명령창(웹 TRACER 관리자 화면 전용) — 2026-11-23
-- 사용자 '삭제 예정' 표시(delete_at). 실제로 지우지 않고 표시만 한다. 그 사용자가 다시 접속하면 표시가 자동으로 풀린다.
-- 기존 표·함수는 그대로 두고 덧붙이기만 한다. Supabase SQL Editor에서 이 파일만 실행하면 된다(여러 번 실행해도 안전).

alter table public.profiles add column if not exists delete_at timestamptz;  -- 삭제 예정으로 표시한 시각(null = 아님)

-- admin_users()에 delete_at을 더한다(돌려주는 칸이 바뀌므로 지우고 다시 만든다)
drop function if exists public.admin_users();
create function public.admin_users()
returns table (id uuid, email text, name text, role text, status text, can_practice boolean, can_explain boolean,
               daily_limit int, note text, created_at timestamptz, last_seen timestamptz, delete_at timestamptz,
               today_ai int, today_actions int, total_attempts int)
language sql stable set search_path = public as $$
  select p.id, p.email, p.name, p.role, p.status, p.can_practice, p.can_explain, p.daily_limit, p.note,
         p.created_at, p.last_seen, p.delete_at,
         (select count(*)::int from activity_log a where a.user_id = p.id and a.ai
            and a.at >= (date_trunc('day', now() at time zone 'Asia/Seoul') at time zone 'Asia/Seoul')),
         (select count(*)::int from activity_log a where a.user_id = p.id
            and a.at >= (date_trunc('day', now() at time zone 'Asia/Seoul') at time zone 'Asia/Seoul')),
         (select count(*)::int from attempts t where t.user_id = p.id)
  from profiles p
  order by p.last_seen desc nulls last;
$$;
revoke execute on function public.admin_users() from public, anon, authenticated;
grant execute on function public.admin_users() to service_role;
