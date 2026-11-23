# migration.sql 코드 검토 (Claude)

대상: `b_final/migration.sql` / 기준: `SPEC.md` / 읽은 것: SPEC.md, harness/, b_final/ 만.
줄 번호는 **수정 전 원본** 기준. 재현 스크립트: `b_final/attack.js` (`node attack.js`).

## 총평
- 권한 구조는 탄탄하다. 모든 표 `revoke all` 후 최소 grant, 모든 RLS 정책 `to authenticated`, 모든 함수 `security definer` + `set search_path = ''` + 안에서 `auth.uid()` 검사, anon·PUBLIC 실행 권한 회수, 트리거 함수는 `private`에 숨김.
- 직접 공격해 본 결과(남의 profiles/preferences/생년월일 읽기, member_status 직접 변경, 트리거 함수 직접 호출, anon 호출, id 바꿔치기) 모두 막힘. **심각도 높음 문제는 못 찾았다.**
- 주된 약점은 **동시성**(같은 두 사람 사이 함수들이 직렬화되지 않음).

## 문제 목록

### [중간] 1. 동시에 서로 like 하면 매칭이 안 생긴다
- 근거: `swipe()` 430–442줄. 자기 like를 넣고 같은 트랜잭션에서 상대 like가 있는지 본다. READ COMMITTED에서 A·B가 동시에 실행하면 서로 상대의 **미커밋** like를 못 봐서 둘 다 `null` 반환 → 서로 like인데 매칭 없음(이후 영구히. 다시 like 하면 생기지만 사용자는 모름).
- 재현: PGlite는 연결이 하나라 직접 재현 불가. Postgres 격리 수준 동작으로 확실(두 psql 세션에서 `begin; select swipe(..)` 를 교차 실행하면 재현).
- 고치는 법: 두 사람 쌍 단위로 `pg_advisory_xact_lock(hashtextextended(least||greatest, 0))` 을 잡고 검사·기록. 두 번째 트랜잭션은 첫 번째 커밋 후 새 스냅샷으로 상대 like를 본다.

### [중간] 2. 차단과 동시에 매칭·메시지가 끼어들 수 있다
- 근거: `block_user()` 542–550줄, `send_message()` 490–518줄, `swipe()` 421–449줄. 
  - 차단 트랜잭션이 matches 를 update 한 뒤, 동시에 진행되던 swipe 가 매칭을 새로 insert 하면 **차단된 두 사람 사이에 종료 안 된 매칭**이 남는다(get_candidates 에서 "매칭됨"으로 계속 보임).
  - send_message 가 ended_at·blocks 를 검사한 직후 차단이 커밋되면 **차단 뒤에 메시지가 저장**된다(괴롭힘 차단 기능의 구멍).
- 고치는 법: 1번과 같은 쌍 잠금을 block_user·send_message 에도 걸고, send_message 는 잠금 후 ended_at 을 다시 읽는다.

### [낮음] 3. 함수 오류 메시지로 남의 상태를 알 수 있음(정보 노출)
- 근거: `swipe()` 418·427줄. 임의 uuid 에 swipe 하면 `target not eligible`(없거나 비활성)과 그 외를 구분 → 회원 활성 여부 탐지. 나를 차단한 사람에게 swipe 하면 `blocked relationship` → **상대가 나를 차단했는지** 알 수 있다. `send_message()` 의 `match not found` / `not a participant` 도 같은 종류.
- 재현: `attack.js` 의 "oracle" 두 줄.
- 고치는 법: 상대 관련 실패는 하나의 일반 메시지(`cannot swipe this user`)로 통일.

### [낮음] 4. admin_set_status 가 프로필 없는 사용자의 member_status 를 새로 만든다
- 근거: 274–278줄 upsert. 명세상 member_status 는 profiles insert 트리거로만 생긴다. 운영자가 프로필·생년월일 없는 사용자를 active 로 만들면 그 사용자가 `swipe()` 로 like·매칭까지 가능.
- 재현: `attack.js` "admin activates profileless user Z" → "profileless Z swipes A" 성공.
- 고치는 법: upsert 대신 `update ... ; if not found then raise exception 'no profile'`. (운영자 실수가 전제라 낮음)

### [낮음] 5. 생년월일 미입력자도 swipe·매칭 가능 / 생년월일 무제한 변경
- 근거: `swipe()` 는 caller·target 의 생년월일 존재를 보지 않는다(get_candidates 만 봄). `set_birth_date()` 는 인증(photo_verified) 후에도 언제든·몇 번이든 바꿀 수 있고 `0001-01-01` 같은 값도 받는다.
- 명세 범위 안이지만 운영에선 나이 확인 우회가 된다. 고치는 법: 자격 판정에 생년월일 존재 포함, 생년월일 변경은 운영자만 또는 1회, 하한(예: 1900년) 검사.

### [낮음] 6. 정지(suspended)된 사용자가 기존 매칭에서 계속 메시지 전송 가능
- 근거: `send_message()` 는 자격을 보지 않는다. 명세 조건에도 없어서 명세 위반은 아님. 운영상 정지 = 대화 중단이 기대되면 status 검사를 넣거나 정지 시 매칭 종료.

### [낮음] 7. Supabase 배포 때 확인할 점 (추정)
- `delete_my_account()` 568줄이 `auth.users` 를 직접 지운다. 함수 소유자(마이그레이션 실행 역할 `postgres`)에게 `auth.users` DELETE 권한이 있어야 한다(현재 Supabase 에선 대체로 있음, 추정). Supabase 권장은 Auth Admin API 이고, Storage 파일 등 DB 밖 데이터는 연쇄 삭제되지 않는다.
- 나이 계산 `current_date` 는 세션 시간대(Supabase 기본 UTC) 기준 → 한국 시각 00~09시에 만 19세 생일인 사람은 하루 늦게 통과.
- 이후 `public` 에 새 함수·표를 만들면 기본 권한으로 anon 에게 다시 열린다 → 새 객체마다 revoke 를 잊지 말 것(또는 `alter default privileges ... revoke`).

### [낮음] 8. 성능
- RLS 정책이 `auth.uid()` 를 행마다 부른다(130–187줄). Supabase 권장대로 `(select auth.uid())` 로 감싸면 한 번만 계산.
- `messages.sender_id` 에 인덱스가 없어 계정 삭제 연쇄 시 messages 전체 스캔.
- `idx_member_status_eligible`(86줄)은 pk 와 같은 칼럼이라 효과가 거의 없다.
- `get_candidates` 는 매 호출 전체 프로필을 훑고 행마다 `age()` 계산, `lim` 상한이 없어 큰 값으로 한 번에 긁어 갈 수 있다(상한 예: 100). 규모가 커지면 생년월일 범위 조건(`birth_date between ...`)으로 바꾸는 게 좋다.
- 정렬이 `order by cp.id` 고정이라 늘 같은 상대부터 보인다(기능적 참고).

### [낮음] 9. 매칭 상대의 프로필(닉네임)을 볼 방법이 없음
- profiles 는 자기 것만 select. 명세대로지만 매칭 후 대화 화면에서 상대 이름을 못 띄운다 → 다음 단계에서 "매칭 당사자 profiles select" 정책이나 함수 필요.

## 고친 것
1. `swipe()` — 검사 전에 두 사람 쌍 advisory 잠금(`pg_advisory_xact_lock(hashtextextended(least||greatest,0))`) 추가 → 동시 like 시 매칭 누락 해결(문제 1).
2. `block_user()` — 같은 쌍 잠금 추가 → 차단과 동시에 생긴 매칭이 종료 안 된 채 남는 문제 해결(문제 2).
3. `send_message()` — 참여자 확인 뒤 같은 쌍 잠금 + `ended_at` 재조회 → 차단 직후 메시지 끼어들기 해결(문제 2).
- 확인: `node selftest.js` → ALL 8 TESTS PASSED. 낮음 항목(3~9)은 명세 해석·운영 판단이 필요해 고치지 않았다.
