# 보너스 1 — 확인봇 배포 가이드

최종 프롬프트를 **재사용 가능한 형태**로 배포하는 방법입니다.
아래 중 **하나 이상** 완료하면 보너스 1 조건을 충족합니다.

| 방식 | 난이도 | 비용 | 추천 상황 |
|------|--------|------|-----------|
| A. Custom GPT / 커스텀 인스트럭션 | 낮음 | ChatGPT 플랜 | 가장 빠른 제출 |
| B. Streamlit Community Cloud | 중간 | 무료 | 링크 공유·포트폴리오 |
| C. 로컬 Streamlit | 낮음 | API 키만 | 데모·검증 |
| D. Firebase Hosting + 정적 안내 | 중간 | 무료 티어 | 프롬프트 패키지 호스팅 |

---

## A. Custom GPT (가장 빠름)

1. ChatGPT → **Explore GPTs** → **Create a GPT**
2. `deploy/custom_gpt_instructions.md`의 **Instructions 본문** 붙여넣기
3. (선택) Knowledge에 `bot/prompts/` 파일 업로드
4. Conversation starters 3개 설정
5. **Only me** 또는 **Anyone with a link**로 저장
6. 공유 링크를 README 보너스 1 섹션에 기록

커스텀 인스트럭션만 쓸 경우: 같은 파일의 **4) Custom instructions** 절을 계정 설정에 넣습니다.

---

## B. Streamlit Community Cloud (권장 웹 배포)

### 사전 준비

1. GitHub에 이 저장소 push
2. [Google AI Studio](https://aistudio.google.com/apikey)에서 **Gemini API 키** 발급 (무료 티어로 충분)
3. [share.streamlit.io](https://share.streamlit.io) 로그인 (GitHub 연동)

### 배포 단계

1. **New app** → 저장소 선택
2. Main file path: `bot/app.py`
3. **Advanced settings → Secrets**에 다음 추가:

```toml
GEMINI_API_KEY = "여기에_키"
```

OpenAI/Grok를 쓸 경우:

```toml
OPENAI_API_KEY = "여기에_키"
# Grok 예시
# OPENAI_BASE_URL 은 앱 사이드바에서 https://api.x.ai/v1 입력
```

4. Deploy → 발급된 URL을 README에 기입

### 로컬 실행

```powershell
cd C:\Users\seong\Desktop\ProJect\CODYSSEY_1_ProJect-main
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r bot/requirements.txt
streamlit run bot/app.py
```

브라우저에서 `http://localhost:8501` 접속.

---

## C. 재사용 패키지 구조 (핵심 산출물)

```
bot/
  app.py                 # Streamlit UI + LLM 호출
  requirements.txt
  prompts/
    system_prompt.md     # 최종 시스템 프롬프트 (v2)
    few_shot.json        # Few-shot 3건 (모호 입력 1건 포함)
    input_template.md    # 입력 템플릿
deploy/
  custom_gpt_instructions.md
  DEPLOY.md              # 이 문서
  firebase/              # (선택) 정적 프롬프트 호스팅
```

**재사용성 포인트**

- 프롬프트·예시·템플릿이 **코드와 분리**되어 있어, UI 없이도 GPT/다른 에이전트에 이식 가능
- Streamlit 앱은 같은 파일을 로드하므로 **단일 진실 공급원(Single Source of Truth)**
- temperature·모델명은 사이드바에 노출 → 과제 **재현성 기록**과 연결

---

## D. Firebase (선택 — 프롬프트 패키지 호스팅)

Firebase에 **인덱스/설정 파일**을 올려 팀원이 URL로 받게 할 때 사용합니다.
(LLM 추론 서버가 아니라 **정적 배포 + 문서 공유** 용도)

```powershell
# Firebase CLI 설치 후
cd deploy/firebase
firebase login
firebase init hosting   # public 폴더 = public
firebase deploy --only hosting
```

`deploy/firebase/public/` 에 `system_prompt.md`, `input_template.md` 복사본을 두고
호스팅 URL을 README에 적으면 “재사용 가능한 형태” 배포로 인정받기 쉽습니다.

> 참고: 과제 문구의 `.index` / Firebase는 **벡터 인덱스·설정 파일을 클라우드에 올려 공유**하는 패턴을 염두에 둔 선택지입니다.
> 확인봇은 RAG 없이도 프롬프트 패키지 배포로 보너스 1을 충족합니다.

---

## 제출 시 README에 적을 내용 (복붙용)

```markdown
## 보너스 1 – 확인봇 배포

- **배포 형태**: (Custom GPT / Streamlit / Firebase 중 기입)
- **URL 또는 공유 방식**: (링크 또는 "로컬 실행: streamlit run bot/app.py")
- **재사용 패키지 경로**: `bot/prompts/`
- **포함 요소**: 시스템 프롬프트 v2, Few-shot 3, 입력 템플릿
- **재현성**: provider / model / temperature 는 앱 사이드바 또는 Custom GPT 설정에 기록
```

---

## 동작 검증 (제출 전 5분)

| # | 입력 | 기대 |
|---|------|------|
| 1 | `그냥 절차 메일 써줘` | 되묻기 (이메일 즉시 작성 X) |
| 2 | 배경+모르는 것 1건 | 제목+본문, 실행 가능 질문 |
| 3 | `카톡 톤으로` | 확인사항 유지, 톤만 변경 |
| 4 | 예산 126 vs 150 추가 | 불일치 질문화, 임의 단정 X |
