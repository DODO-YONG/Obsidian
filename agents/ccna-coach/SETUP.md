# TRACER 상시 운영 준비 (Vercel + Supabase + 구글 로그인) — 직접 할 일

> ✅ 2026-11-20 완료: https://tracer-eosin.vercel.app/ccna/ · 같은 날 구글 OAuth 앱 **게시(In production)** — 누구나 구글 계정으로 로그인 (기본 범위만 써서 심사 불필요, 개인정보 처리방침 `privacy.html`)

> 계정 만들기·키 붙여 넣기는 **본인이 직접** 한다(Claude는 키를 보거나 입력하지 않는다).
> **세 곳 모두 결제 수단(카드)을 등록하지 않는다.** 카드가 없으면 한도를 넘어도 청구되지 않고 멈추기만 한다.
> 다 하면 Claude에게 **Vercel 주소**만 알려 주면 나머지(예전 주소 연결, 깨우기 설정, 확인)를 이어서 한다.

## 1. Supabase (DB·로그인) — 약 5분
1. https://supabase.com → **Start your project** → GitHub로 가입 (요금제: **Free**).
2. **New project**: 이름 `tracer`, Region **Northeast Asia (Seoul)**, DB 비밀번호는 비밀번호 관리자에 저장.
3. 왼쪽 **SQL Editor** → 새 쿼리 → 이 폴더의 [`supabase/schema.sql`](supabase/schema.sql) 내용을 통째로 붙여 넣고 **Run** → "Success" 확인. 안드로이드 앱(Tracer Route) 오류 신고도 받으려면 [`supabase/app_reports.sql`](supabase/app_reports.sql)도 같은 방법으로 실행.
4. **Project Settings → API Keys**에서 세 값을 메모(다음 단계에서 Vercel에 붙여 넣음):
   - Project URL (`https://xxxx.supabase.co`)
   - **Publishable key** (`sb_publishable_…`, 예전 이름 anon) — 공개돼도 되는 키
   - **Secret key** (`sb_secret_…`, 예전 이름 service_role) — **절대 공개 금지**, Vercel 환경변수에만

## 2. Google 로그인 연결 — 약 7분
1. https://console.cloud.google.com → 위쪽 프로젝트 선택 → **새 프로젝트** `tracer` (결제 계정 연결 **안 함**).
2. **API 및 서비스 → OAuth 동의 화면**(Google Auth Platform) → 시작하기
   - 앱 이름 `TRACER`, 지원 이메일 본인, 대상 **외부(External)**, 연락처 이메일 본인 → 만들기
   - 범위는 기본(email·profile·openid)만. 민감한 범위가 없어 심사 없이 쓸 수 있다.
   - **대상(Audience) → 앱 게시(Publish app)** 를 눌러 "프로덕션"으로 → 아무 구글 계정이나 로그인 가능
3. **클라이언트 → 클라이언트 만들기**: 유형 **웹 애플리케이션**
   - 승인된 리디렉션 URI: `https://xxxx.supabase.co/auth/v1/callback` (1-4의 Project URL 뒤에 `/auth/v1/callback`)
   - 만들면 나오는 **클라이언트 ID**·**클라이언트 보안 비밀번호**를 복사
4. Supabase → **Authentication → Sign In / Providers → Google** → 켜고 클라이언트 ID·보안 비밀번호 붙여 넣기 → Save.

## 3. Vercel (화면 + /api) — 약 5분
1. https://vercel.com → **Sign Up** → **Hobby** → GitHub로 계속.
2. **Add New… → Project** → `DODO-YONG/Obsidian` Import
   - **Root Directory: `docs`** (Edit 눌러 선택) · Framework Preset: **Other** · Build 명령 없음
   - **Environment Variables** 에 아래를 넣는다(값은 각자 붙여 넣기):

     | 이름 | 값 |
     |---|---|
     | `GOOGLE_API_KEY` | 볼트 `.env`의 제미나이 키(무료 등급) |
     | `SUPABASE_URL` | 1-4 Project URL |
     | `SUPABASE_ANON_KEY` | 1-4 Publishable key |
     | `SUPABASE_SERVICE_ROLE_KEY` | 1-4 Secret key |
     | `TRACER_OWNER_EMAIL` | 내가 로그인할 구글 메일(이 계정이 주인=최고 관리자) |
     | `CCNA_EXAM_DATE` | (선택) `YYYY-MM-DD` — 주인 화면에만 D-day |

3. **Deploy** → 끝나면 주소(`https://xxxx.vercel.app`)가 나온다.

## 4. 로그인 주소 허용 (Supabase) — 1분
Supabase → **Authentication → URL Configuration**
- **Site URL**: `https://xxxx.vercel.app/ccna/`
- **Redirect URLs** → Add: `https://xxxx.vercel.app/ccna/**`

## 5. 확인
1. `https://xxxx.vercel.app/ccna/` → 오른쪽 위 **Google로 로그인** → 주인 메일로 로그인
2. 위쪽에 **⚙ 관리자**가 보이면 성공 → 눌러서 대시보드·사용자·활동 기록·문제은행 확인
3. Claude에게 Vercel 주소를 알려 주기 → 예전 주소(github.io/…/ccna/)가 새 주소로 넘어가게 하고, 일시정지 방지 깨우기를 켠다.

## 바꿀 수 있는 설정 (Vercel 환경변수, 선택)
| 이름 | 기본 | 뜻 |
|---|---|---|
| `TRACER_NEW_USER_STATUS` | `active` | `pending`이면 새 사용자는 관리자 승인 후 AI 사용 |
| `TRACER_GLOBAL_DAILY_AI` | `300` | 주인을 뺀 전체 사용자의 하루 제미나이 호출 한도 |
| `TRACER_BANK_MIN` | `10` | 묶음에 이 개수 이상 쌓이면 문제은행 재사용 시작 |
| `TRACER_BANK_RATIO` | `0.9` | 재사용 비율(나머지는 새로 만들어 문제은행을 키움) |
| `TRACER_REPORT_THRESHOLD` | `3` | 미해결 신고가 이만큼이면 그 문제 출제 중지 |
| `GEMINI_MODEL` | (자동) | 모델 고정 |

사용자별 하루 한도(기본 30)·권한·차단은 관리자 페이지에서 바꾼다.

## 💸 무료 범위 메모 (2026-11 확인)
- Supabase Free: DB 0.5GB, 월 활성 사용자 5만, **일주일 DB 활동이 없으면 일시정지** → `.github/workflows/tracer-keepalive.yml`이 하루 한 번 깨움.
- Vercel Hobby: 비상업·개인용만, 함수 최대 300초(여기선 60초로 제한), 한도를 넘으면 청구 없이 멈춤.
- Google OAuth: 기본 범위 로그인은 무료, 결제 계정 불필요.
- 제미나이: 기존 무료 등급 키 그대로. 문제은행이 차면 객관식은 문제당 호출 0번.
