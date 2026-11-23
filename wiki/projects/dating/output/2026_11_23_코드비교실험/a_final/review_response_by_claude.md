# 검토 응답 (Claude)

| # | 심각도 | 판단 | 조치 |
|---|---|---|---|
| 1 | 높음 | 진짜(`current_date` 쓰는데 immutable, 세션 TimeZone으로 하루 앞당기기 가능) | **고침**: `private.today()`(Asia/Seoul 고정, stable) 추가, `age_of`도 stable. Kiritimati에서 19세 하루 전 생일 → 거부 확인 |
| 2 | 높음 | 진짜(잠금이 검사 뒤에 있고 block_user는 잠금 없음) | **고침**: `private.lock_pair()`를 swipe에서 자격·차단 검사 **전**에, block_user에서도 같은 키로 잡음 |
| 3 | 중간 | 진짜(차단 여부·상대 상태가 오류 문구로 구분됨) | **고침**: 상대 자격 미달·차단을 `cannot swipe target` 하나로 통일 |
| 4 | 중간 | 진짜(검사~insert 사이 block_user 끼어들 수 있음) | **고침**: send_message가 쌍 잠금 후 매칭을 `for share`로 다시 읽고 검사 |
| 5 | 중간 | 명세 밖 정책 | **안 고침**: SPEC이 send_message 조건(당사자·미종료·비차단)을 명시적으로 나열함. 자격 조건 추가는 명세 변경이라 자동 채점과 어긋날 수 있음 → 정책 결정 사항 |
| 6 | 중간 | 일부 진짜(public 전체 회수는 다른 객체까지 건드림) | **고침**: 이 파일이 만든 테이블·함수만 이름으로 회수. service_role 부여는 명세에 없어 안 넣음 |
| 7 | 중간 | 진짜(PostgREST upsert가 PK 칼럼 UPDATE 권한을 요구) | **고침**: update 칼럼 권한에 `id`/`user_id` 추가. RLS with check가 PK 변경을 막는 것 확인 |
| 8 | 중간 | 진짜(FK 연쇄 삭제 시 풀스캔) | **고침**: `messages_sender_idx` 추가 |
| 9 | 중간 | 진짜(성능) | **고침**: 차단 검사를 `not exists` 2개로 풀고, 상대 나이 조건을 생년월일 범위로 변환, `member_status` 자격 부분 인덱스 추가 |
| 10 | 낮음 | 운영 참고 | 안 고침: 명세가 `auth.users` 직접 삭제를 요구 |
| 11 | 낮음 | 진짜지만 UUID 추측 난이도상 영향 미미 | 안 고침(낮음) |
| 12 | 낮음 | 현재는 도달 불가(종료는 차단으로만 생기고 차단이면 swipe 거부) | 안 고침(낮음) |
| 13 | 낮음 | 입력 품질 문제 | 안 고침(낮음) |
| 14 | 낮음 | 참고 사항 | 안 고침(낮음). 단 잠금 키에는 #2를 고치면서 `dating_pair:` 접두사를 붙임 |

확인: `a_final/selftest.js` 29개 전부 통과. 별도로 타임존 우회 거부, upsert 성공, PK 변경 RLS 거부, `private.lock_pair` 사용자 실행 불가도 확인함.
