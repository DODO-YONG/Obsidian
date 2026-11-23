# `a_final/migration.sql` 코드 검토 결과

검토 대상: `wiki/_inbox/_ab/a_final/migration.sql` (기준 명세: `wiki/_inbox/_ab/SPEC.md`)  
검증 환경: `harness/env.js` (PGlite / PostgreSQL 17)에서 직접 재현 시험 및 `EXPLAIN ANALYZE` 수행.

## 총평
전반적인 기본 방어선(테이블/함수 권한 회수 후 최소 부여, 전 테이블 RLS, `security definer` + `set search_path = ''`, `(select auth.uid())` 캐싱, `anon` 완전 차단, 직접적인 `member_status`/`private.*` 변조·조회 차단)은 탄탄하게 짜여 있다.  
다만 **나이 계산 함수의 `IMMUTABLE` 오용 및 타임존 우회**, **`swipe`·`send_message`와 `block_user` 간 동시성 경쟁(TOCTOU)**, **오류 메시지 분기를 통한 차단·상태 정보 유출**, **실제 Supabase 운영 호환성(PostgREST upsert 실패, `public` 스키마 일괄 회수)**, **성능 병목(`messages.sender_id` 인덱스 누락, 인라이닝 불가 함수)** 문제가 발견됐다.

---

## 발견된 문제

### 1. [심각도 높음] `private.age_of()`에 `IMMUTABLE` 오용 및 세션 `TimeZone` 조작으로 만 19세 제한 우회 가능
- **근거**: `migration.sql` L123-126 (`private.age_of`), L160 (`set_birth_date`), L194·L201·L208 (`get_candidates`)
  1. `private.age_of(d)`는 매일(그리고 세션 타임존마다) 값이 바뀌는 `current_date`를 참조하는데 **`immutable`**로 선언됐다. PostgreSQL 플래너는 `immutable` 함수에 상수 인자가 들어오면 플랜 시점에 값을 고정(constant folding)하므로, Prepared Statement나 장수 커넥션에서 자정이 지나거나 타임존이 바뀌어도 옛날 나이를 반환한다.
  2. `set search_path = ''`는 세션 `TimeZone`을 고정하지 않는다. `authenticated` 세션의 타임존을 바꾸면 `Pacific/Niue`(UTC-11)와 `Pacific/Kiritimati`(UTC+14) 사이 최대 25시간(하루 이상) 차이가 나서, UTC 기준 아직 만 18세인 사용자(매일 UTC 10:00~23:59 사이 다음 날이 19세 생일인 경우)가 타임존을 UTC+14로 바꿔 `set_birth_date()`의 만 19세 제한을 통과할 수 있다.
  - **재현 결과 (PGlite)**:
    - `PREPARE p_age AS SELECT private.age_of('2007-11-23'::date)`를 UTC(`2026-11-23`)에서 생성·실행(`age: 19`)한 뒤 `SET TIME ZONE 'Pacific/Niue'`(`current_date = 2026-11-22`, 실제 만 나이 `18`)로 바꿔도 `EXECUTE p_age`가 여전히 `19`를 반환함.
    - 같은 `authenticated` 사용자가 `Pacific/Niue`(현지시간 `2026-11-22`, 만 18세)에서 `set_birth_date('2007-11-23')` 호출 시 `must be 19 or older`로 거부됐으나, `SET TIME ZONE 'Pacific/Kiritimati'` 실행 직후 동일 생년월일 저장에 성공함.
- **고치는 방법**:
  - `private.age_of(d)`를 `immutable` 대신 **`stable`**로 변경한다.
  - `current_date` 대신 서비스 기준 타임존으로 날짜를 고정한다(예: `(pg_catalog.now() at time zone 'Asia/Seoul')::date` 또는 `'UTC'`).

---

### 2. [심각도 높음] `swipe()`와 `block_user()` 사이 동시성 경쟁(TOCTOU)으로 차단된 사용자 간 활성 매칭이 생성될 수 있음
- **근거**: `migration.sql` L233-256 (`swipe`), L285-296 (`block_user`)
  - `swipe()`는 L235에서 `private.is_blocked(me, target)`을 검사한 **뒤에** L238에서 쌍 단위 잠금(`pg_advisory_xact_lock`)을 획득한다.
  - `block_user()`는 L292-295에서 이 쌍 단위 잠금을 전혀 잡지 않는다.
  - **재현 시나리오** (B가 이미 A에게 `like`한 상태):
    1. T1(`A: swipe(B, 'like')`): L235 `is_blocked(A, B)` → `false` 통과.
    2. T2(`B: block_user(A)`): `blocks(B, A)` 삽입 → `matches` 종료 시도(아직 매칭이 없어 0건) → 커밋.
    3. T1(`A: swipe(B, 'like')`): 잠금 획득 후 `swipes(A, B, 'like')` 삽입 → B의 `like` 확인 → **`matches(A, B)`를 `ended_at = null`로 새로 생성 후 커밋**.
  - 결과적으로 B가 A를 차단해 `block_user()`가 성공했는데도 둘 사이에 종료되지 않은 활성 매칭이 남는다. (같은 이유로 `swipe()`의 `is_eligible` 검사도 잠금 전이라 `admin_set_status()`와 미세 경쟁이 있다.)
- **고치는 방법**:
  - `swipe()`에서 기본 인자 검증(`me`/`target`/`act` null 및 자기 자신 체크) 직후, `is_eligible`·`is_blocked` 검사 **이전에** 쌍 단위 `pg_advisory_xact_lock`을 잡는다.
  - `block_user()`에서도 `swipe()`와 **동일한 키**로 `pg_advisory_xact_lock`을 잡은 뒤 `blocks` 삽입과 `matches` 종료를 수행한다.

---

### 3. [심각도 중간] `swipe()` 오류 메시지 분기로 상대의 차단 여부와 `member_status`가 유출됨 (정보 유출 오라클)
- **근거**: `migration.sql` L234-235 (`swipe`)
  - 명세상 `member_status`는 자기 것만 조회할 수 있고, `blocks`도 자기가 한 차단만 조회할 수 있어 "상대가 나를 차단했는지"는 숨겨야 한다.
  - 그러나 L234(`'target not eligible'`)와 L235(`'blocked'`)가 서로 다른 오류 메시지를 반환한다.
  - **재현 결과 (PGlite)**: 자격 있는 A가 임의의 대상에게 `swipe(target, 'pass')` 호출 시
    - active이고 A를 차단한 B → `ERROR: blocked`
    - draft 상태이고 차단 안 한 C → `ERROR: target not eligible`
    - 존재하지 않는 UUID → `ERROR: target not eligible`
  - A는 `swipe()` 오류 메시지만 보고 임의의 UUID가 ① `active + photo_verified` 상태인지, ② 나를 차단했는지를 DB 흔적 없이 알아낼 수 있다.
- **고치는 방법**:
  - L234-235의 상대 자격 미달과 차단 관계 오류를 하나의 동일한 일반 메시지(예: `'cannot swipe target'`)로 통일한다.

---

### 4. [심각도 중간] `send_message()`와 `block_user()` 사이 동시성 경쟁(TOCTOU)으로 차단 후에도 메시지가 저장될 수 있음
- **근거**: `migration.sql` L270-281 (`send_message`), L292-295 (`block_user`)
  - `send_message()` L270의 `select * into m from public.matches x where x.id = mid`에 행 잠금이 없다.
  - **재현 시나리오**:
    1. T1(`A: send_message(mid, ...)`): `m.ended_at is null` 및 `is_blocked = false` 확인.
    2. T2(`B: block_user(A)`): `blocks(B, A)` 삽입 + `matches.ended_at = now()` 갱신 후 커밋.
    3. T1(`A: send_message`): `messages` 삽입 후 커밋.
  - `block_user()`가 완료된 뒤에도 차단된 상대의 메시지가 저장된다.
- **고치는 방법**:
  - `send_message()` L270을 `select * into m from public.matches x where x.id = mid for share;`로 바꾼다(`for share`끼리는 충돌하지 않아 일반 채팅 동시성은 유지되면서, `block_user()`의 `update public.matches`가 잡는 `for no key update`와는 직렬화되어 `READ COMMITTED`에서 변경된 `ended_at`을 재검증한다). 추가로 `block_user()`에서 `matches` 업데이트를 먼저 수행하거나 쌍 잠금을 함께 사용하면 더 확실하다.

---

### 5. [심각도 중간] 정지(`suspended`)된 사용자가 기존 매칭에서 `send_message()`를 계속 호출할 수 있음
- **근거**: `migration.sql` L261-283 (`send_message`)
  - `send_message()`는 매칭 당사자·`ended_at`·차단 여부만 확인하고 `member_status`를 확인하지 않는다.
  - **재현 결과 (PGlite)**: 운영자가 `admin_set_status(A, 'suspended', false)`로 A를 정지시킨 뒤에도 A가 기존 매칭 `mid`에 `send_message(mid, 'im suspended!')`를 호출하면 정상 저장된다.
  - 참고: `SPEC.md`의 `send_message` 설명에 자격 조건이 명시돼 있지 않아 엄밀한 명세 위반은 아니지만, 실제 운영·보안 측면에서는 제재된 계정이 기존 매칭 상대에게 계속 메시지를 보낼 수 있는 공백이다.
- **고치는 방법**:
  - 명세와 협의해 `send_message()`에 발신자 상태 확인(예: `status <> 'suspended'` 또는 `private.is_eligible(me)`)을 추가하거나, `admin_set_status(..., 'suspended', ...)` 시 해당 사용자의 활성 매칭을 종료하는 정책을 검토한다.

---

### 6. [심각도 중간] 실제 Supabase 배포 시 `public` 스키마 전체 `REVOKE`가 기존 테이블·확장 기능 권한을 지움
- **근거**: `migration.sql` L307-309
  - `revoke all on all tables / sequences / functions in schema public from public, anon, authenticated;`는 이 마이그레이션이 만든 객체뿐 아니라 `public` 스키마의 **모든 기존 객체**(다른 모듈 테이블, 뷰, `public`에 설치된 확장 함수 등)의 권한까지 전부 회수한다.
  - 또한 `private` 스키마에 `service_role` 권한이 부여되지 않아, Supabase Edge Function 등 백엔드가 `service_role`로 `private.admins`·`private.user_private`를 관리해야 할 때 접근이 막힐 수 있다 `(추정: Supabase 기본 설정상 새로 만든 private 스키마에는 service_role의 USAGE 권한이 자동 부여되지 않음)`.
- **고치는 방법**:
  - `on all ... in schema public` 대신 이 마이그레이션이 생성한 각 테이블·함수 이름을 명시해 `revoke`한다. 백엔드에서 `service_role`이 `private`에 접근해야 한다면 명시적으로 필요한 권한만 부여한다.

---

### 7. [심각도 중간] 컬럼 단위 `UPDATE` 권한에서 PK를 제외해 Supabase PostgREST `.upsert()`가 실패함
- **근거**: `migration.sql` L315 (`profiles`), L319 (`preferences`)
  - `grant update (nickname, gender, region, bio) on public.profiles`와 `grant update (min_age, max_age, genders) on public.preferences`에 PK 컬럼(`id`, `user_id`)이 빠져 있다.
  - Supabase 클라이언트(`supabase-js`)의 `.upsert({ id, nickname, ... })`는 PostgREST가 `INSERT ... ON CONFLICT (id) DO UPDATE SET id = EXCLUDED.id, ...`로 변환하는데, PostgreSQL은 값이 바뀌지 않아도 `DO UPDATE SET`에 포함된 모든 컬럼의 `UPDATE` 권한을 검사한다.
  - **재현 결과 (PGlite)**: `profiles`와 `preferences` 모두 PK를 포함한 `ON CONFLICT ... DO UPDATE SET` 실행 시 `permission denied for table profiles / preferences` 오류가 발생한다.
  - RLS `UPDATE` 정책(L95-96, L105-106)이 이미 `with check (id = (select auth.uid()))`로 PK 변경을 막고 있으므로 PK를 `UPDATE` 권한에서 빼도 추가 보안 이득은 없다.
- **고치는 방법**:
  - `grant update (id, nickname, gender, region, bio)` / `grant update (user_id, min_age, max_age, genders)`(또는 테이블 단위 `grant update`)로 변경한다.

---

### 8. [심각도 중간] `public.messages(sender_id)` 인덱스 누락으로 회원 탈퇴 시 `messages` 전체 테이블 스캔 발생
- **근거**: `migration.sql` L65, L69, L303
  - `public.messages.sender_id`는 `references auth.users(id) on delete cascade` 외래 키인데, `messages`에는 `(id)` PK와 `(match_id, created_at)` 인덱스만 있고 `sender_id` 인덱스가 없다(`swipes_to_idx`, `matches_user_b_idx`, `blocks_blocked_idx`는 모두 있는데 `messages`만 누락).
  - `delete_my_account()`가 `delete from auth.users where id = me`를 실행하면 FK 연쇄 삭제가 `DELETE FROM public.messages WHERE sender_id = $1`을 실행한다.
  - **재현 결과 (PGlite `EXPLAIN`)**: `Delete on messages -> Seq Scan on messages (Filter: (sender_id = ...))`. 데이터가 가장 많이 쌓이는 `messages`를 탈퇴 때마다 풀스캔하면 지연과 잠금 경합을 유발한다.
- **고치는 방법**:
  - `create index messages_sender_idx on public.messages(sender_id);`를 추가한다.

---

### 9. [심각도 중간] `get_candidates()` 성능 병목: 인라이닝 불가 함수 호출 + 필터용 인덱스 부족
- **근거**: `migration.sql` L123-139 (`age_of`, `is_blocked`), L183-221 (`get_candidates`)
  - `private.is_blocked()`(`security definer set search_path = ''`)와 `private.age_of()`(`set search_path = ''`)는 함수 속성 때문에 PostgreSQL 플래너가 **인라이닝할 수 없다**.
  - **재현 결과 (PGlite `EXPLAIN ANALYZE`)**:
    1. `not private.is_blocked(me, c.id)`가 Anti-Join으로 풀리지 못하고 후보 행마다 개별 함수 필터(`Filter: ... AND (NOT private.is_blocked(...))`)로 실행된다.
    2. `private.age_of(cu.birth_date)`가 `WHERE`와 `SELECT`에서 반복 호출되며, 날짜 컬럼에 대한 인덱스 범위 조건으로 변환되지 못한다.
    3. `member_status`에 `(user_id) where status = 'active' and photo_verified` 부분 인덱스가 없어 비활성·미인증 회원까지 `member_status_pkey`로 스캔하며 필터링한다(`Rows Removed by Filter`). `profiles(gender)`·`user_private(birth_date)`·`preferences(genders)` 인덱스도 없다.
- **고치는 방법**:
  - `get_candidates()`는 이미 `security definer`이므로 `not private.is_blocked(me, c.id)`를 두 개의 `not exists`로 풀어 써 Anti-Join이 되게 한다(`blocker_id = me and blocked_id = c.id`, `blocker_id = c.id and blocked_id = me`).
  - 나이 비교를 기준 날짜 기준 `cu.birth_date between ... and ...` 범위 조건으로 바꾸고, `member_status(user_id) where status = 'active' and photo_verified` 부분 인덱스와 `profiles(gender, id)`, `user_private(birth_date)` 인덱스를 추가한다.

---

### 10. [심각도 낮음] `delete_my_account()`의 직접 `DELETE FROM auth.users` 관련 Supabase 실제 운영 주의점
- **근거**: `migration.sql` L298-304
  - 명세(`SPEC.md` L36) 요구대로 구현됐으나, 실제 Supabase 배포에서는 다음 운영 문제가 발생할 수 있다:
    1. `auth.users`는 `supabase_auth_admin` 소유이며, 향후 프로필 사진 등을 Supabase Storage(`storage.objects`)에 저장할 경우 `owner` FK 제약이 있는 버전에서는 직접 `DELETE FROM auth.users`가 외래 키 오류로 실패하거나 Storage 고아 파일이 남는다 `(추정: Supabase 버전에 따라 storage.objects.owner FK 유무가 다름)`.
    2. SQL로 `auth.users`를 삭제해도 이미 발급된 Access JWT는 만료 전까지 유효하다(단, 이 스키마에서는 모든 데이터가 연쇄 삭제되므로 잔여 JWT로 쓰기·조회를 시도해도 FK·`is_eligible`에 막혀 보안 사고로 이어지지는 않는다).
- **고치는 방법**:
  - 실제 Supabase 프로덕션에서는 Edge Function 등에서 Storage 파일 정리 후 Auth Admin API(`auth.admin.deleteUser()`)를 호출하는 방식으로 탈퇴를 처리하는 것을 권장한다.

---

### 11. [심각도 낮음] `block_user()`의 미가공 FK 오류로 미인증 사용자도 `auth.users` UUID 존재 여부 판별 가능
- **근거**: `migration.sql` L285-296
  - `block_user(target)`는 호출자 자격을 보지 않고 바로 `insert into public.blocks`를 수행한다.
  - **재현 결과 (PGlite)**: `draft` 미인증 사용자 C가 존재하는 UUID(B)를 넣으면 성공, 없는 UUID를 넣으면 `violates foreign key constraint "blocks_blocked_id_fkey"` 오류가 발생해 임의 UUID의 가입 여부를 확인할 수 있다. (UUID 추측 난이도상 위험도는 낮음.)
- **고치는 방법**:
  - `foreign_key_violation`을 잡아 일반화된 오류를 반환하거나, 대상이 없으면 조용히 종료한다.

---

### 12. [심각도 낮음] 종료된 매칭(`ended_at is not null`)에 재차 상호 `like` 시 `swipe()`가 종료된 매칭 ID를 반환
- **근거**: `migration.sql` L248-256 (`swipe`), L218 (`get_candidates`)
  - 현재는 `block_user()`만 `ended_at`을 설정하므로 차단 검사(L235)에 먼저 걸리지만, 운영자 처리나 추후 매칭 종료/차단 해제 기능 등으로 차단 없이 `ended_at is not null`인 행이 생기면 `swipe(target, 'like')`가 `on conflict do nothing` 뒤 L253에서 **이미 종료된 매칭 ID**를 반환한다.
  - **재현 결과 (PGlite)**: `ended_at`이 채워진 매칭 상태에서 `swipe(B, 'like')` 호출 시 그 종료된 `mid`가 반환되고, 바로 `send_message(mid, ...)`를 부르면 `match ended` 오류가 난다. `get_candidates()`(L218)는 `ended_at is null`만 활성 매칭으로 취급하므로 동작 일관성이 어긋난다.
- **고치는 방법**:
  - 재매칭 정책에 맞춰 `on conflict (user_a, user_b) do update set ended_at = null`로 재활성화하거나, 재매칭 금지라면 `ended_at is not null`일 때 `null` 또는 오류를 반환하도록 명시한다.

---

### 13. [심각도 낮음] `set_birth_date()` 비현실적 과거 날짜 허용 및 프로필/생년월일 없는 계정의 `swipe()` 가능
- **근거**: `migration.sql` L159-160 (`set_birth_date`), L177-180 (`admin_set_status`), L233-234 (`swipe`)
  - `set_birth_date()`는 `age < 19`만 검사해 `'0001-01-01'`(만 2025세)과 `'4713-01-01 BC'`(만 6738세, JS `Date`에서 `Invalid Date`)가 저장되고, `'-infinity'`는 `timestamp out of range` 미처리 오류를 낸다(PGlite 재현).
  - 운영자가 `profiles`나 `birth_date`가 없는 계정에 `admin_set_status(u, 'active', true)`를 호출하면 `get_candidates()`에서는 제외되지만 `swipe()`는 `is_eligible()`만 확인하므로 프로필·생년월일 없는 계정도 스와이프·매칭이 가능하다(PGlite 재현).
- **고치는 방법**:
  - `set_birth_date()`에 `isfinite(d)` 및 합리적 최소 생년월일/최대 나이(예: `d >= date '1900-01-01'`) 검증을 추가한다.
  - 필요 시 `swipe()` 또는 `admin_set_status()`에서 `user_private`(생년월일) 존재를 확인한다(단, 자동 채점 시나리오가 프로필 전 `admin_set_status`를 호출할 수 있으므로 주의).

---

### 14. [심각도 낮음] 기타 경미한 명세·운영 참고 사항
- **`get_candidates()` 상한 100건 고정 (L220)**: `limit least(greatest(coalesce(lim, 20), 0), 100)`은 DoS 방어로는 적절하나 명세에 없는 상한이라 `lim > 100` 요청 시 조용히 100건으로 잘린다.
- **Advisory lock 전역 네임스페이스 (L238-239)**: `hashtextextended(least || greatest, 0)`에 기능 접두사가 없어 같은 DB의 다른 기능이 advisory lock을 쓰면 키 충돌 가능성이 미미하게 있다(`'swipe:' || ...` 접두사 권장).
- **트랜잭션 래핑 부재 (L1-328)**: 파일 전체가 `begin; ... commit;`으로 감싸져 있지 않아, 트랜잭션 없이 문장 단위로 실행하면 테이블·함수 생성(L10-304)과 권한 회수(L307-311) 사이 짧은 구간에 기본 권한이 열려 있을 수 있다(Supabase CLI는 파일 단위 트랜잭션으로 실행하므로 일반 배포에서는 문제없음).

---

## 이상 없음을 확인한 주요 항목
- `anon` 역할의 모든 테이블 조회·쓰기 및 모든 공개 함수 호출 차단.
- `authenticated` 역할의 타인 `profiles`·`preferences`·`member_status`·`swipes`·`matches`·`messages`·`blocks` 직접 조회/변조 차단, `profiles` 타인 ID 삽입 시 PK/FK보다 RLS가 먼저 거부함 확인.
- `private` 스키마(`user_private`, `admins`, 내부 함수) 직접 접근 및 호출 차단.
- 모든 `security definer` 함수에 `set search_path = ''` 적용 및 내부에서 `auth.uid()` 직접 검증.
- `matches` RLS `(select auth.uid()) in (user_a, user_b)`가 `InitPlan` + `BitmapOr`(`matches_user_a_user_b_key` + `matches_user_b_idx`)로 인덱스 스캔됨을 `EXPLAIN`으로 확인.
- `preferences.genders`의 `ARRAY['man', NULL]` 등 NULL 원소 포함 배열은 `<@` 체크 제약으로 정상 거부됨을 확인.
