# GitHub Push + Streamlit Cloud 배포 체크리스트

확인봇(`bot/app.py`)을 공개 URL로 올리는 절차입니다.
각 단계 완료 시 `[ ]` → `[x]` 로 표시하세요.

---

## 0. 사전 준비

| # | 항목 | 상태 |
|---|------|------|
| 0-1 | GitHub 계정 로그인 가능 | [ ] |
| 0-2 | **무료 권장:** [Groq](https://console.groq.com) API 키 발급 (Gemini 대체 1순위) | [ ] |
| 0-2b | (선택) [OpenRouter](https://openrouter.ai) 키 · (선택) [OpenAI](https://platform.openai.com/api-keys) 키 | [ ] |
| 0-2c | (선택) Gemini 키 — 없어도 Fallback으로 동작 | [ ] |
| 0-3 | 로컬에 시크릿 파일 없음 확인 (`.streamlit/secrets.toml` 이 git에 안 들어감) | [ ] |
| 0-4 | 저장소에 `requirements.txt`(루트) + `bot/app.py` 존재 | [ ] |

API 키는 **절대** README·커밋·채팅에 붙여 넣지 마세요. Streamlit **Secrets**에만 넣습니다.

**Gemini가 안 될 때:** 앱 기본 모드는 **자동 Fallback** — Groq → OpenRouter → OpenAI → Gemini 순으로
키가 있는 제공자만 시도합니다. Groq 키만 있어도 배포·제출에 충분합니다.

---

## 1. 로컬 Git 커밋

PowerShell에서 프로젝트 폴더로 이동:

```powershell
cd C:\Users\seong\Desktop\ProJect\CODYSSEY_1_ProJect-main
```

이미 `git init` 및 1차 커밋이 되어 있으면 1-2~1-3만 확인:

```powershell
git status
git log -1 --oneline
```

처음부터라면:

```powershell
git init -b main
git add -A
git status
# .streamlit/secrets.toml 이 staged 에 없어야 함
git commit -m "Add 확인봇 Streamlit package for bonus deploy"
```

| # | 항목 | 상태 |
|---|------|------|
| 1-1 | `main` 브랜치 | [ ] |
| 1-2 | 커밋 1개 이상 존재 | [ ] |
| 1-3 | `secrets.toml` / `.env` 가 커밋에 없음 | [ ] |

---

## 2. GitHub 원격 저장소 생성 + Push

### 방법 A — 웹 UI (gh CLI 없을 때 권장)

1. 브라우저: https://github.com/new  
2. **Repository name**: `CODYSSEY_1_ProJect` (또는 원하는 이름)  
3. **Public** 권장 (Streamlit Cloud 무료 티어와 연동이 단순함)  
4. **README / .gitignore / license 추가하지 않기** (로컬에 이미 있음)  
5. **Create repository**

생성 후 화면에 나오는 주소를 사용 (예: `https://github.com/YOUR_ID/CODYSSEY_1_ProJect.git`):

```powershell
cd C:\Users\seong\Desktop\ProJect\CODYSSEY_1_ProJect-main
git remote add origin https://github.com/YOUR_ID/REPO_NAME.git
git push -u origin main
```

로그인 창이 뜨면 GitHub 계정으로 인증합니다.
(Personal Access Token 사용 시 Password 칸에 토큰 입력)

### 방법 B — GitHub CLI (설치 시)

```powershell
winget install GitHub.cli
gh auth login
gh repo create CODYSSEY_1_ProJect --public --source=. --remote=origin --push
```

| # | 항목 | 상태 |
|---|------|------|
| 2-1 | GitHub에 empty repo 생성 | [ ] |
| 2-2 | `git remote -v` 에 origin 표시 | [ ] |
| 2-3 | `git push -u origin main` 성공 | [ ] |
| 2-4 | 웹에서 `bot/app.py`, `requirements.txt` 보임 | [ ] |

---

## 3. Streamlit Community Cloud 연결

1. https://share.streamlit.io 접속 → **GitHub로 로그인**  
2. 권한 요청 시 해당 저장소 접근 허용  
3. **Create app** / **New app**  
4. 설정값:

| 필드 | 값 |
|------|-----|
| Repository | `YOUR_ID/REPO_NAME` |
| Branch | `main` |
| Main file path | `bot/app.py` |
| App URL (선택) | 예: `confirm-bot` → `https://confirm-bot.streamlit.app` |

5. **Advanced settings** → **Secrets** 에 아래 중 **하나 이상** 붙여넣기 (무료 권장: Groq):

```toml
# 무료 1순위
GROQ_API_KEY = "gsk_여기에_Groq_키"

# 선택 — 무료 모델
# OPENROUTER_API_KEY = "sk-or-..."

# 선택 — ChatGPT API
# OPENAI_API_KEY = "sk-..."

# 선택 — Gemini (실패해도 Fallback이 처리)
# GEMINI_API_KEY = "..."
```

6. **Deploy** 클릭 → 빌드 로그에서 `pip install` 완료·앱 기동 확인

| # | 항목 | 상태 |
|---|------|------|
| 3-1 | share.streamlit.io GitHub 연동 | [ ] |
| 3-2 | Main file = `bot/app.py` | [ ] |
| 3-3 | Secrets에 `GROQ_API_KEY` (또는 다른 키) 등록 | [ ] |
| 3-4 | Deploy 성공, 공개 URL 발급 | [ ] |

---

## 4. 배포 후 동작 검증 (5분)

브라우저에서 앱 URL 접속 후:

| # | 테스트 | 기대 | 상태 |
|---|--------|------|------|
| 4-1 | 페이지 로드 | "확인봇" 제목, 사이드바 설정 표시 | [ ] |
| 4-2 | `그냥 절차 메일 써줘` | 이메일을 바로 안 쓰고 **되묻기** | [ ] |
| 4-3 | 배경+모르는 것 입력 | 제목+본문, 번호 목록 질문 | [ ] |
| 4-4 | `카톡 톤으로` | 확인사항 유지, 톤만 변경 | [ ] |

사이드바 호출 모드는 **자동 Fallback (권장)** 유지.
직전 사용 제공자(예: Groq / llama-3.3-70b)가 사이드바에 표시되면 정상입니다.

---

## 5. 제출물 반영

README 보너스 1 표에 URL 기입:

```markdown
| Streamlit URL | https://YOUR-APP.streamlit.app |
```

| # | 항목 | 상태 |
|---|------|------|
| 5-1 | README에 Streamlit URL 기록 | [ ] |
| 5-2 | (선택) 커밋·push 후 최신 문서 반영 | [ ] |

```powershell
# URL 기입 후
git add README.md
git commit -m "Add Streamlit Cloud deploy URL for bonus 1"
git push
```

Streamlit Cloud는 `main` push 시 **자동 재배포**됩니다.

---

## 문제 해결

| 증상 | 원인 / 조치 |
|------|-------------|
| `ModuleNotFoundError` | 루트 `requirements.txt` 확인 후 **Reboot app** |
| `등록된 API 키가 없습니다` | Secrets에 `GROQ_API_KEY` 등 등록 후 Reboot |
| Gemini 지역/쿼터 오류 | 정상 — Fallback이 Groq/OpenRouter로 전환. Groq 키 확인 |
| OpenAI 결제/한도 오류 | `OPENAI_API_KEY` 결제 상태 확인, 또는 Groq만 사용 |
| OpenRouter 모델 없음 | 모델명 끝에 `:free` 확인 |
| GitHub private repo 연동 실패 | Streamlit에 repo 권한 재부여 또는 **Public** 전환 |
| Windows `python` 오류 (로컬만) | `py -3 -m streamlit run bot/app.py` 사용 |
| Push 인증 실패 | GitHub → Settings → Developer settings → PAT (repo 권한) 발급 후 비밀번호 대신 사용 |

---

## 한 줄 요약

```
로컬 커밋 → GitHub new repo → git push → share.streamlit.io
→ Main: bot/app.py → Secrets: GEMINI_API_KEY → Deploy → README에 URL
```
