---
type: topic
tags: [fair-work, 경쟁분석, 벤치마킹, 지도UX]
project: fair-work
date: 2026-11-26
작성: gemini
검토상태: 미확인
---

# 🔍 경쟁 사이트 분석: ESL Whitelist Korea (`eslwhitelistkorea.com`)

상위: [[fair-work]]

- 대상: `https://eslwhitelistkorea.com/app/map` (2026-11-26 읽기 전용 탐색)
- 목적: **Midnight Run Korea**의 지도·검색·리뷰 UX 설계 참고 및 차별화 포인트 도출 (추후 Claude의 별도 확인 결과와 교차 비교 예정)

---

## 1. 사이트 구조 및 현황
- **지도 엔진**: NAVER Maps 기반, 우측 상단 3개 모드 전환 (`Reviews` / `Academy profiles` / `Job openings`).
- **데이터 규모**: `Reviews` 디렉터리 기준 **128개 학원 / 139개 리뷰** (초기 데이터 상당수가 `Source: TokyoJon Green List` / `TokyoJon Black List` 출처 링크를 단 이관 리뷰 + 일부 자체 리뷰). 채용공고(`/app/openings`)는 3건 모두 만료(`Expired`).
- **검색·필터 (`Reviews` 모드)**:
  - 좌측 패널(`Review directory`, 모바일은 하단 시트)에 검색창(`Search names, aliases, or addresses`), 필터(`All / Whitelist / Blacklist`, `Recruiters only`), 정렬(`A–Z`, `Z–A`, `Newest`, `Oldest`, `Most reviews`, `Fewest reviews`), `Add a place`.
  - 목록 클릭 시 지도가 해당 학원으로 이동하고 패널이 상세 화면으로 전환.
- **핀 디자인**: 마스코트 'Dubu(두부)' 표정 아이콘(웃음=Whitelist, 울음=Blacklist, `???`=혼합, 무표정=리뷰 0건) + 겹치는 구역은 검은색 원형 숫자 클러스터.
- **상세 패널 필드**: 영문·한글 학원명 병기, 전체 주소 + **Kakao Maps 외부 링크**, Whitelist(👍)/Blacklist(👎) 수, 개별 리뷰 카드(작성일 퍼머링크, 본문, 외부 출처 링크, 조회수, `Helpful` 버튼, `Report review`), 하단 리뷰 작성 CTA. (5점 별점·세부 항목 점수·태그·사진 없음)
- **로그인 정책**: 리뷰 전문·지도·디렉터리 대부분 **비로그인 전체 공개**. 리뷰 작성·장소 추가·Helpful·신고·이력서·강사 마켓(`/app/teachers`)만 로그인 필요(Google OAuth + 이메일/비밀번호). 학원 클레임은 비즈니스 이메일 도메인 또는 명함 수동 검수.
- **수익 모델**: 현재 무료 운영 (`Academy profiles and job posts are free`).

---

## 2. 가져오면 좋은 UX 5가지 (채택 후보)
1. **지도 + 좌측 검색·정렬 패널 결합 (모바일은 하단 시트)** ⭐
   - 사용자가 지적한 "이름 검색 + 지도 매칭" 불편을 가장 직관적으로 해결. 목록 클릭 → 지도 이동 → 상세 확인이 한 화면에서 완결됨.
2. **학원 상세에 `Kakao Maps` 외부 링크 1줄 추가**
   - 원어민 교사가 주변 지하철역·거리뷰(로드뷰)를 바로 확인 가능. 구현 비용 최소, 실사용 만족도 최상.
3. **지도 핀 클러스터링 (숫자 원형 배지)**
   - 대치동·분당 등 밀집 지역에서 줌 아웃 시 가독성·렌더링 성능 확보.
4. **리뷰 카드의 `Helpful` 버튼 + 외부 출처 투명 표기**
   - Tokyo Jon 등 외부 참고 데이터는 `Source: TokyoJon Black/Green List` 링크를 명확히 표시하고, 자체 리뷰엔 `Helpful` 카운트로 유용한 후기 부각.
5. **신뢰 원칙 명시 (FAQ/안내)**
   - *"AI가 리뷰를 재작성하지 않음 · 개인정보 미판매 · 플랫폼 판정이 아님"*을 투명하게 공개.

---

## 3. 따라 하면 안 되는 점 & Midnight Run Korea의 우위 4가지
1. **학원 DB 규모 격차**: 상대는 수동 등록 **128곳**뿐이라 대부분 학원이 검색 안 됨 → 우리는 **전국 20,196곳 나이스 DB + 영어 별칭 2,341곳 + 국민연금 894곳** 보유.
2. **리뷰 구조화 수준**: 상대는 이진 분류(👍/👎) + 장문 텍스트뿐이라 핵심 조건 비교가 어려움 → 우리는 **5대 핵심 체크리스트**(월급·퇴직금·4대보험·계약준수·LOR) + 별점 2종 제공.
3. **법적 안전성**: 상대는 **비로그인 전체 공개 + 우는/웃는 핀 + Blacklist 직접 라벨**이라 한국 명예훼손·업무방해 위험이 큼 → 우리는 **같은 색 중립 핀 + 승인 교사 전용 열람 + 학원 반론 창구**로 지속 가능성 확보.
4. **기능 집중도**: 상대는 구인·이력서·강사 마켓까지 벌려 만료 공고(`Expired`)·잠긴 테이블(`Profile details hidden`) 등 빈 화면 노출 → 우리는 **계약 전 학원 사전 검증** 하나에 집중.

---

## 4. Claude 교차 비교 시 확인할 포인트
- 모바일·데스크톱 지도 패널 전환 시 실제 조작감 및 반응 속도
- `Reviews` 외에 `Job openings` 비교 테이블의 시장 평균 대비 표시(▲/▼)를 우리 체크리스트 요약에 응용할 여지가 있는지
- 법적 관점에서 `Source: TokyoJon ...` 출처 표기 방식의 적정성
