# 과제: 소개팅 앱 1단계 — DB + 권한(RLS) + 핵심 함수

결과물은 **`migration.sql` 파일 하나**. Supabase(Postgres) 위에서 돈다고 가정한다. 시험 환경은 PGlite(Postgres 17, WASM)이고, 아래 "환경"은 시험 장치가 미리 만들어 둔다. **여기 적힌 이름·인자·반환형을 정확히 지킨다**(자동 채점).

## 환경 (시험 장치가 이미 만들어 둠 — migration.sql에서 만들지 말 것)
- 역할: `anon`, `authenticated` (Supabase와 같음)
- `auth.users(id uuid primary key)` 테이블
- `auth.uid()` 함수: 현재 요청한 사용자 id (`request.jwt.claim.sub` 설정값), 로그인 안 했으면 null
- Supabase 기본값처럼 `public` 스키마의 테이블·시퀀스·함수에는 `anon`·`authenticated`에게 **모든 권한이 기본으로 부여**된다. 그래서 RLS·권한 회수가 유일한 방어선이다.
- `migration.sql`은 슈퍼유저로 한 번 실행된다. 사용자는 `set role authenticated` + `request.jwt.claim.sub = <id>` 상태로 SQL을 실행한다.

## 테이블
| 이름 | 칼럼 | 비고 |
|---|---|---|
| `public.profiles` | `id uuid pk → auth.users on delete cascade`, `nickname text not null` (2~20자), `gender text not null` ('man','woman'), `region text not null`, `bio text not null default ''` (500자 이하) | 사용자가 직접 insert/update(자기 것만) |
| `public.member_status` | `user_id uuid pk → auth.users on delete cascade`, `status text not null default 'draft'` ('draft','active','suspended'), `photo_verified boolean not null default false` | **profiles insert 때 자동 생성**(트리거). 사용자는 자기 것 select만. 바꾸는 건 운영자 함수로만 |
| `private.user_private` | `user_id uuid pk → auth.users on delete cascade`, `birth_date date not null` | 사용자는 직접 접근 불가(스키마 권한 없음) |
| `private.admins` | `user_id uuid pk → auth.users on delete cascade` | 운영자 목록. 시험 장치가 슈퍼유저로 넣는다 |
| `public.preferences` | `user_id uuid pk → auth.users on delete cascade`, `min_age int not null default 19`, `max_age int not null default 99`, `genders text[] not null` | 자기 것만 select/insert/update. 19 ≤ min ≤ max ≤ 99 |
| `public.swipes` | `from_id uuid`, `to_id uuid` (둘 다 → auth.users on delete cascade), `action text` ('like','pass'), `created_at timestamptz default now()`, pk(from_id,to_id) | 자기가 보낸 것만 select. 직접 insert/update/delete 불가(`swipe()`로만) |
| `public.matches` | `id uuid pk default gen_random_uuid()`, `user_a uuid`, `user_b uuid` (→ auth.users on delete cascade, `user_a < user_b`, unique(user_a,user_b)), `created_at`, `ended_at timestamptz` | 당사자만 select. 직접 쓰기 불가 |
| `public.messages` | `id uuid pk`, `match_id uuid → matches on delete cascade`, `sender_id uuid → auth.users on delete cascade`, `body text` (1~2000자), `created_at` | 매칭 당사자만 select. 직접 쓰기 불가(`send_message()`로만) |
| `public.blocks` | `blocker_id`, `blocked_id` (→ auth.users on delete cascade), pk(둘), `created_at` | 자기가 한 차단만 select. 직접 쓰기 불가(`block_user()`로만) |

## 함수 (모두 `public` 스키마, `authenticated`가 호출)
"자격 있음" = `member_status.status = 'active'` 그리고 `photo_verified = true`. 나이 = `birth_date` 기준 만 나이.

| 함수 | 동작 |
|---|---|
| `set_birth_date(d date) returns void` | 내 생년월일 저장(있으면 갱신). **만 19세 미만이면 오류** |
| `admin_set_status(target uuid, new_status text, verified boolean) returns void` | `private.admins`에 있는 사람만. 아니면 오류 |
| `get_candidates(lim int default 20) returns table(id uuid, nickname text, age int, gender text, region text, bio text)` | 나에게 보여 줄 상대. 내가 자격 없으면 오류. 조건: 상대도 자격 있음, 나 아님, **서로의** 선호(성별·나이 범위) 만족, 어느 쪽이든 차단 없음, 내가 like한 사람 제외, 내가 **30일 안에** pass한 사람 제외, 이미 매칭(종료 안 된)된 사람 제외. 생년월일 없는 사람 제외 |
| `swipe(target uuid, act text) returns uuid` | like/pass 기록(같은 상대에게 다시 하면 덮어씀). 내가 자격 없거나, 상대가 자격 없거나, 차단 관계거나, 자기 자신이면 오류. like이고 상대도 나를 like했으면 매칭을 **하나만** 만들고 그 id 반환, 아니면 null |
| `send_message(mid uuid, body text) returns uuid` | 그 매칭의 당사자이고, 매칭이 종료 안 됐고, 차단 관계가 아니면 저장 후 id 반환. 아니면 오류 |
| `block_user(target uuid) returns void` | 차단 기록 + 둘 사이 매칭을 종료(`ended_at = now()`) |
| `delete_my_account() returns void` | 내 `auth.users` 행을 지운다 → 내 데이터 전부 연쇄 삭제 |

## 보안 조건
- `security definer` 함수는 `set search_path = ''`(또는 고정 경로)로 만들고, 안에서 `auth.uid()`로 권한을 직접 검사한다.
- 로그인 안 한 사용자(`anon`)는 어떤 테이블도 못 읽고 어떤 함수도 못 쓴다.
- 사용자가 자기 `member_status`를 바꾸거나, 남의 profiles·preferences·생년월일을 읽을 방법이 없어야 한다.
