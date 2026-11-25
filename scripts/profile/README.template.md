<!-- 이 파일은 DODO-YONG/DODO-YONG 프로필 README의 원본입니다. 고칠 때는 볼트의 scripts/profile/README.template.md 를 고치고
     python3 scripts/profile-readme.py 로 올립니다. 아래 journal 칸은 매일 밤 자동으로 채워집니다. -->
# Hi, I'm MJ 👋

**Aspiring Network & Security Engineer** · building AI-assisted tools with Claude Code

I'm building a career in network and security engineering, with the goal of working in KY or IN.
I learn by building: in the past weeks I designed, shipped, and operated several small AI agents and web apps on my own, with security and zero running cost as ground rules.

[🌐 Workshop site](https://dodo-yong.github.io/Obsidian/) · [📓 Work journal (daily & weekly)](https://dodo-yong.github.io/Obsidian/journal/?lang=en) · [🧠 TRACER (live)](https://tracer-eosin.vercel.app/ccna/) · [📁 Main repository](https://github.com/DODO-YONG/Obsidian)

---

## 🎓 Education & Training
| Program | Status |
|---|---|
| AWS training program | In progress (2026) |

## 📜 Certifications
| Certification | Status |
|---|---|
| Google Cybersecurity Professional Certificate | ✅ Completed |
| Cisco CCNA 200-301 | 📚 In progress |

## 🛠️ Projects

| Project | What it does | Built with |
|---|---|---|
| 🧠 **[TRACER](https://tracer-eosin.vercel.app/ccna/)** — CCNA practice site | Public CCNA 200-301 practice site with Google sign-in. Serves questions from a 1,808-question bank with full explanations (including why each wrong choice is wrong), saves progress per account, and adds XP, titles, and quests. Includes an admin console (user roles, daily AI limits, activity log, flagged questions) and a natural-language admin command bar. | JavaScript · Vercel serverless · Supabase (Postgres, Auth) · Gemini (free tier) · Playwright tests on GitHub Actions |
| 📱 **Tracer Route** — Android app | Offline version of TRACER for Android with the question bank built in, English/Korean UI, anonymous error reports, and a privacy policy. Release build ready; Google Play closed testing next. | Capacitor · Android · Supabase |
| 🛡️ **[SENTINEL](https://github.com/DODO-YONG/security-agent)** — web security checker | Non-intrusive website security agent: checks authorization first, then reads only responses (headers, cookies, TLS, page content) and writes a report with risk levels and fixes. No attacks. | Python · Claude Agent SDK |
| 🎤 **MIRROR** — interview coach | Practice coach for AWS Leadership Principles interviews. Asks about the weakest principles first, digs in with follow-up questions, and scores answers on STAR structure, numbers, and principle fit. | Python · Claude Agent SDK |
| 💗 **[Heartline](https://dodo-yong.github.io/Obsidian/heartline/)** — conversational web app | Web app where users design a chat persona (personality, tone, relationship) and talk in a messenger-style UI, with an English-practice mode and built-in safety rules. Planned, built, tested, and presented in one day. | JavaScript · Python · Gemini |
| 🎧 **[SHADOW](https://dodo-yong.github.io/Obsidian/shadow/)** — English shadowing coach | Downloads audio from a video link, splits it into sentences, and records you while you hold Space. Compares your intonation curve and the words recognized against the original. Runs fully on the local machine. | Python · Whisper (local) · yt-dlp |
| 🧹 **SWEEPER** — laptop cleanup helper | Scans Downloads/Desktop without AI, then proposes cleanup; nothing moves until approved in the terminal, and deletions go to the Trash only. | Python · Claude Agent SDK |
| 🐛 **[worm-arena](https://github.com/DODO-YONG/worm-arena)** | Browser worm game with single-player and same-network multiplayer. | Python · HTML/JavaScript |

**Study logs:** [CCNA study log](https://github.com/DODO-YONG/ccna-study-log) (Packet Tracer labs) · [TryHackMe write-ups](https://github.com/DODO-YONG/tryhackme-writeups) (no flags or answers)

## 🧰 Skills
- **Networking:** routing, switching, subnetting · Cisco Packet Tracer · Wireshark
- **Security:** non-intrusive web checks (headers, cookies, TLS) · secret scanning with pre-commit hooks · least-privilege database rules · privacy policies
- **Development:** Python · JavaScript · HTML/CSS · SQL (PostgreSQL) · Linux shell
- **Cloud & DevOps:** Vercel · Supabase · GitHub Pages · GitHub Actions (CI, scheduled jobs) · Playwright end-to-end tests
- **AI tooling:** Claude Code · Claude Agent SDK · Gemini · multi-agent workflows (two AI assistants splitting tasks in parallel)

## 🧭 How I work
- **Security first:** the main repository is public, so keys live only in local env files and a pre-commit hook blocks anything that looks like a secret.
- **Zero extra cost:** everything runs on free tiers and existing subscriptions; daily limits protect free quotas.
- **Write it down:** every change is committed with a clear message, and a nightly job turns those commits into the work journal below.

## 📓 Recent work
<!-- journal:start -->
<!-- journal:end -->
