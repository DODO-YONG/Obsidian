# 🤖 나만의 에이전트 만들기

수업에서 만드는 AI 에이전트 프로젝트 모음. 코드는 `agents/`, 설계·학습 메모는 Obsidian 위키(`wiki/`)에 있다.

## 🗺️ 프로젝트 지도

```mermaid
flowchart LR
  W["📚 Obsidian 위키<br/>설계·학습 메모"]
  T["🧩 _template<br/>새 프로젝트 틀"]
  W -.-> T

  subgraph SA["🛡️ security-agent · 웹사이트 보안 점검"]
    direction TB
    SA1["🔑 권한 확인<br/>authorize_target"] --> SA2["🔍 비침습 점검<br/>헤더·쿠키·TLS·본문"]
    SA2 --> SA3["📝 리포트<br/>위험도·고치는 법"]
  end
  W --> SA

  classDef plan fill:#fff4d6,stroke:#d9a400,color:#5a4500
  classDef dev fill:#dbeafe,stroke:#2563eb,color:#1e3a8a
  classDef done fill:#dcfce7,stroke:#16a34a,color:#14532d
  classDef base fill:#f3f4f6,stroke:#9ca3af,color:#374151
  class W,T base
  style SA fill:#dbeafe,stroke:#2563eb,color:#1e3a8a
```

<sub>색: 🟨 기획 · 🟦 개발중 · 🟩 완료</sub>

## 📋 프로젝트 목록

| 프로젝트 | 한 줄 설명 | 상태 | 코드 | 메모 |
|---|---|---|---|---|
| 🛡️ security-agent | URL을 주면 공격 없이 응답만 읽어 보안 약점을 찾고, 위험도와 고치는 법을 리포트로 써 줌 | 🟦 개발중 | [agents/security-agent](agents/security-agent) | [위키](wiki/projects/security-agent/security-agent.md) · [소개 페이지](https://dodo-yong.github.io/security-agent/) |

## 📁 폴더 구조

```
agents/<이름>/          에이전트 코드 (프로젝트 하나 = 폴더 하나)
wiki/projects/<이름>/   설계·학습 메모 (Obsidian)
raw/                    원본 자료 (읽기 전용)
```

## 🔒 비밀 정보 다루는 법

- **API 키·토큰** → 각 폴더의 `.env`에만 저장. git에 자동으로 안 올라간다. 형식은 `.env.example`로 공유.
- **올리기 싫은 문서·메모** → 아무 곳에나 `private/` 폴더를 만들어 넣거나, 파일명을 `이름.private.md`처럼 짓는다.
- **안전장치** → 커밋 직전 검사(`.githooks/pre-commit`)가 키 모양 문자열이나 `.env` 파일을 발견하면 커밋을 막는다.
- 이 저장소를 새로 clone했다면 한 번 실행: `git config core.hooksPath .githooks`

## ⚙️ 동기화

Obsidian Git 플러그인이 편집이 5분 멈추면 자동으로 커밋·푸시한다(Obsidian이 켜져 있을 때).
