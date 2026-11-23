-- Tracer Route 앱(안드로이드) 오류 신고 — 2026-11-22
-- 앱은 로그인 없이 공개(publishable·anon) 키로 '넣기'만 할 수 있다. 읽기·수정·삭제는 막힘(관리자 /api만 비밀 키로 읽음).
-- 기존 표·함수는 건드리지 않는다. Supabase SQL Editor에서 이 파일만 실행하면 된다(여러 번 실행해도 안전).

create table if not exists public.app_reports (
  id           bigint generated always as identity primary key,
  app_qid      text not null check (char_length(app_qid) between 1 and 40),     -- 앱 문제 ID(문제 글 해시)
  sub          text check (char_length(sub) <= 10),                              -- 범위(예: 3.4)
  question     text not null check (char_length(question) between 1 and 1500),  -- 문제 글(앞부분)
  reason       text not null check (reason in ('answer', 'both', 'explanation', 'typo', 'other')),
  note         text check (char_length(note) <= 500),                            -- 사용자가 쓴 설명(선택)
  app_version  text check (char_length(app_version) <= 20),
  lang         text check (lang in ('ko', 'en')),
  resolved     boolean not null default false,
  at           timestamptz not null default now()
);
create index if not exists app_reports_open on public.app_reports (resolved, at desc);

alter table public.app_reports enable row level security;

-- 앱(anon): 새 신고 넣기만. 처리 여부·시각은 직접 못 정한다(아래 트리거가 덮어씀)
revoke all on public.app_reports from anon, authenticated;
grant all on public.app_reports to service_role;  -- 관리자 /api(비밀 키)가 읽고 처리하려면 필요(2026-11-23 추가: 빠져 있어 앱 신고 탭이 권한 오류)
grant usage, select on all sequences in schema public to service_role;
grant insert (app_qid, sub, question, reason, note, app_version, lang) on public.app_reports to anon;
drop policy if exists app_reports_insert on public.app_reports;
create policy app_reports_insert on public.app_reports for insert to anon with check (resolved = false);

-- 스팸 방지: 최근 1분에 30건, 하루 500건이 넘으면 거절
create or replace function public.app_reports_guard() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if (select count(*) from app_reports where at > now() - interval '1 minute') >= 30
     or (select count(*) from app_reports where at > now() - interval '1 day') >= 500 then
    raise exception 'too many reports' using errcode = 'P0001';
  end if;
  new.resolved := false;
  new.at := now();
  return new;
end $$;
revoke execute on function public.app_reports_guard() from public, anon, authenticated;
drop trigger if exists app_reports_guard on public.app_reports;
create trigger app_reports_guard before insert on public.app_reports
  for each row execute function public.app_reports_guard();
