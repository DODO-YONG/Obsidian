create schema private;
create table public.profiles(id uuid primary key references auth.users on delete cascade, nickname text not null check (char_length(nickname) between 2 and 20), gender text not null check (gender in ('man','woman')), region text not null, bio text not null default '' check (char_length(bio)<=500));
create table public.member_status(user_id uuid primary key references auth.users on delete cascade, status text not null default 'draft' check (status in ('draft','active','suspended')), photo_verified boolean not null default false);
create table private.user_private(user_id uuid primary key references auth.users on delete cascade, birth_date date not null);
create table private.admins(user_id uuid primary key references auth.users on delete cascade);
create table public.preferences(user_id uuid primary key references auth.users on delete cascade, min_age int not null default 19, max_age int not null default 99, genders text[] not null, check (19<=min_age and min_age<=max_age and max_age<=99));
create table public.swipes(from_id uuid references auth.users on delete cascade, to_id uuid references auth.users on delete cascade, action text not null check (action in ('like','pass')), created_at timestamptz not null default now(), primary key(from_id,to_id));
create table public.matches(id uuid primary key default gen_random_uuid(), user_a uuid not null references auth.users on delete cascade, user_b uuid not null references auth.users on delete cascade, created_at timestamptz not null default now(), ended_at timestamptz, check (user_a<user_b), unique(user_a,user_b));
create table public.messages(id uuid primary key default gen_random_uuid(), match_id uuid not null references public.matches on delete cascade, sender_id uuid not null references auth.users on delete cascade, body text not null check (char_length(body) between 1 and 2000), created_at timestamptz not null default now());
create table public.blocks(blocker_id uuid references auth.users on delete cascade, blocked_id uuid references auth.users on delete cascade, created_at timestamptz not null default now(), primary key(blocker_id,blocked_id));

alter table public.profiles enable row level security; alter table public.member_status enable row level security; alter table public.preferences enable row level security;
alter table public.swipes enable row level security; alter table public.matches enable row level security; alter table public.messages enable row level security; alter table public.blocks enable row level security;
revoke all on all tables in schema public from anon;
revoke insert, update, delete on public.member_status, public.swipes, public.matches, public.messages, public.blocks from authenticated;
create policy p_sel on public.profiles for select to authenticated using (id = auth.uid());
create policy p_ins on public.profiles for insert to authenticated with check (id = auth.uid());
create policy p_upd on public.profiles for update to authenticated using (id = auth.uid()) with check (id = auth.uid());
create policy ms_sel on public.member_status for select to authenticated using (user_id = auth.uid());
create policy pr_all on public.preferences for all to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy sw_sel on public.swipes for select to authenticated using (from_id = auth.uid());
create policy m_sel on public.matches for select to authenticated using (auth.uid() in (user_a,user_b));
create policy msg_sel on public.messages for select to authenticated using (exists (select 1 from public.matches m where m.id = match_id and auth.uid() in (m.user_a,m.user_b)));
create policy b_sel on public.blocks for select to authenticated using (blocker_id = auth.uid());

create function private.on_profile() returns trigger language plpgsql security definer set search_path='' as $$ begin insert into public.member_status(user_id) values (new.id) on conflict do nothing; return new; end $$;
create trigger t_profile after insert on public.profiles for each row execute function private.on_profile();
create function private.eligible(u uuid) returns boolean language sql stable security definer set search_path='' as $$ select exists(select 1 from public.member_status where user_id=u and status='active' and photo_verified) $$;
create function private.blocked(a uuid, b uuid) returns boolean language sql stable security definer set search_path='' as $$ select exists(select 1 from public.blocks where (blocker_id=a and blocked_id=b) or (blocker_id=b and blocked_id=a)) $$;
create function private.age(u uuid) returns int language sql stable security definer set search_path='' as $$ select extract(year from age(current_date, birth_date))::int from private.user_private where user_id=u $$;

revoke execute on all functions in schema public from anon;
create function public.set_birth_date(d date) returns void language plpgsql security definer set search_path='' as $$
begin if auth.uid() is null then raise exception 'login'; end if;
 if extract(year from age(current_date,d)) < 19 then raise exception 'under 19'; end if;
 insert into private.user_private values (auth.uid(), d) on conflict (user_id) do update set birth_date=excluded.birth_date; end $$;
create function public.admin_set_status(target uuid, new_status text, verified boolean) returns void language plpgsql security definer set search_path='' as $$
begin if not exists(select 1 from private.admins where user_id=auth.uid()) then raise exception 'not admin'; end if;
 update public.member_status set status=new_status, photo_verified=verified where user_id=target; end $$;
create function public.get_candidates(lim int default 20) returns table(id uuid, nickname text, age int, gender text, region text, bio text) language plpgsql stable security definer set search_path='' as $$
declare me uuid := auth.uid(); my_age int; mp public.preferences; mg text;
begin if me is null or not private.eligible(me) then raise exception 'not eligible'; end if;
 my_age := private.age(me); select * into mp from public.preferences where user_id=me; select p.gender into mg from public.profiles p where p.id=me;
 if my_age is null or mp is null then raise exception 'incomplete'; end if;
 return query select p.id, p.nickname, private.age(p.id), p.gender, p.region, p.bio from public.profiles p join public.preferences op on op.user_id=p.id
 where p.id<>me and private.eligible(p.id) and private.age(p.id) is not null
  and p.gender = any(mp.genders) and private.age(p.id) between mp.min_age and mp.max_age
  and mg = any(op.genders) and my_age between op.min_age and op.max_age
  and not private.blocked(me,p.id)
  and not exists(select 1 from public.swipes s where s.from_id=me and s.to_id=p.id and (s.action='like' or s.created_at > now()-interval '30 days'))
  and not exists(select 1 from public.matches m where m.ended_at is null and m.user_a=least(me,p.id) and m.user_b=greatest(me,p.id))
 limit lim; end $$;
create function public.swipe(target uuid, act text) returns uuid language plpgsql security definer set search_path='' as $$
declare me uuid := auth.uid(); mid uuid;
begin if me is null or not private.eligible(me) or not private.eligible(target) or target=me or private.blocked(me,target) then raise exception 'not allowed'; end if;
 insert into public.swipes(from_id,to_id,action) values (me,target,act) on conflict (from_id,to_id) do update set action=excluded.action, created_at=now();
 if act='like' and exists(select 1 from public.swipes where from_id=target and to_id=me and action='like') then
  insert into public.matches(user_a,user_b) values (least(me,target),greatest(me,target)) on conflict (user_a,user_b) do nothing returning id into mid;
  if mid is null then select id into mid from public.matches where user_a=least(me,target) and user_b=greatest(me,target); end if;
 end if; return mid; end $$;
create function public.send_message(mid uuid, body text) returns uuid language plpgsql security definer set search_path='' as $$
declare me uuid := auth.uid(); m public.matches; nid uuid;
begin select * into m from public.matches where id=mid;
 if me is null or m.id is null or me not in (m.user_a,m.user_b) or m.ended_at is not null or private.blocked(m.user_a,m.user_b) then raise exception 'not allowed'; end if;
 insert into public.messages(match_id,sender_id,body) values (mid,me,body) returning id into nid; return nid; end $$;
create function public.block_user(target uuid) returns void language plpgsql security definer set search_path='' as $$
declare me uuid := auth.uid(); begin if me is null or target=me then raise exception 'no'; end if;
 insert into public.blocks(blocker_id,blocked_id) values (me,target) on conflict do nothing;
 update public.matches set ended_at=now() where user_a=least(me,target) and user_b=greatest(me,target) and ended_at is null; end $$;
create function public.delete_my_account() returns void language plpgsql security definer set search_path='' as $$
begin if auth.uid() is null then raise exception 'login'; end if; delete from auth.users where id=auth.uid(); end $$;
revoke execute on all functions in schema public from anon, public;
grant execute on all functions in schema public to authenticated;
