"""
확인봇 — 창업지원 실무 이메일 작성 코치 (Streamlit 배포용)

보너스 1: 최종 시스템 프롬프트를 재사용 가능한 형태로 배포.
- 로컬: streamlit run bot/app.py
- 클라우드: Streamlit Community Cloud에 이 저장소 연결
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = BASE_DIR / "prompts"
SYSTEM_PROMPT_PATH = PROMPTS_DIR / "system_prompt.md"
FEW_SHOT_PATH = PROMPTS_DIR / "few_shot.json"
INPUT_TEMPLATE_PATH = PROMPTS_DIR / "input_template.md"

# ---------------------------------------------------------------------------
# Load packaged prompts (reusability core)
# ---------------------------------------------------------------------------


@st.cache_data
def load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


@st.cache_data
def load_few_shot() -> list[dict]:
    return json.loads(FEW_SHOT_PATH.read_text(encoding="utf-8"))


@st.cache_data
def load_input_template() -> str:
    return INPUT_TEMPLATE_PATH.read_text(encoding="utf-8")


def build_messages(
    system_prompt: str,
    few_shot: list[dict],
    history: list[dict],
    user_text: str,
) -> list[dict]:
    """OpenAI-compatible chat messages including few-shot + history."""
    messages: list[dict] = [{"role": "system", "content": system_prompt}]

    # Few-shot as frozen demonstration turns (not shown in UI history)
    for ex in few_shot:
        messages.append({"role": "user", "content": ex["user"]})
        messages.append({"role": "assistant", "content": ex["assistant"]})

    for turn in history:
        messages.append({"role": turn["role"], "content": turn["content"]})

    messages.append({"role": "user", "content": user_text})
    return messages


# ---------------------------------------------------------------------------
# LLM backends
# ---------------------------------------------------------------------------


def call_openai_compatible(
    messages: list[dict],
    *,
    api_key: str,
    base_url: str | None,
    model: str,
    temperature: float,
) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url or None)
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return (resp.choices[0].message.content or "").strip()


def call_gemini(
    messages: list[dict],
    *,
    api_key: str,
    model: str,
    temperature: float,
) -> str:
    """Gemini via google-genai (OpenAI-compatible path preferred if available)."""
    try:
        from google import genai
        from google.genai import types
    except ImportError as e:
        raise RuntimeError(
            "google-genai 패키지가 없습니다. `pip install google-genai` 후 다시 시도하세요."
        ) from e

    client = genai.Client(api_key=api_key)

    system_parts = [m["content"] for m in messages if m["role"] == "system"]
    system_instruction = "\n\n".join(system_parts) if system_parts else None

    contents: list = []
    for m in messages:
        if m["role"] == "system":
            continue
        role = "user" if m["role"] == "user" else "model"
        contents.append(
            types.Content(role=role, parts=[types.Part.from_text(text=m["content"])])
        )

    config = types.GenerateContentConfig(
        temperature=temperature,
        system_instruction=system_instruction,
    )
    resp = client.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )
    return (resp.text or "").strip()


def generate_reply(
    messages: list[dict],
    provider: str,
    api_key: str,
    model: str,
    temperature: float,
    base_url: str | None = None,
) -> str:
    if provider == "OpenAI 호환 (OpenAI / Grok / 기타)":
        return call_openai_compatible(
            messages,
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
        )
    if provider == "Google Gemini":
        return call_gemini(
            messages,
            api_key=api_key,
            model=model,
            temperature=temperature,
        )
    raise ValueError(f"지원하지 않는 provider: {provider}")


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="확인봇 | 창업지원 실무 이메일 코치",
    page_icon="✉️",
    layout="wide",
)

st.title("✉️ 확인봇")
st.caption(
    "창업지원 실무 이메일 작성 코치 · 보너스1 재사용 배포 패키지 "
    "(시스템 프롬프트 + Few-shot + 입력 템플릿)"
)

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_template" not in st.session_state:
    st.session_state.pending_template = None

# ---- Sidebar: config + reusable package ----
with st.sidebar:
    st.header("⚙️ 설정")

    provider = st.selectbox(
        "LLM Provider",
        ["Google Gemini", "OpenAI 호환 (OpenAI / Grok / 기타)"],
        help="무료로 시작하려면 Gemini API 키(Google AI Studio)를 권장합니다.",
    )

    default_models = {
        "Google Gemini": "gemini-2.0-flash",
        "OpenAI 호환 (OpenAI / Grok / 기타)": "gpt-4o-mini",
    }
    model = st.text_input("모델명", value=default_models[provider])

    base_url = None
    if provider.startswith("OpenAI"):
        base_url = st.text_input(
            "Base URL (선택)",
            value=os.getenv("OPENAI_BASE_URL", ""),
            placeholder="비우면 기본 OpenAI / 예: https://api.x.ai/v1",
            help="Grok 사용 시 https://api.x.ai/v1",
        )
        base_url = base_url.strip() or None

    # Secrets > env > empty
    env_key_map = {
        "Google Gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        "OpenAI 호환 (OpenAI / Grok / 기타)": ("OPENAI_API_KEY", "XAI_API_KEY"),
    }
    secret_key = ""
    for k in env_key_map[provider]:
        from_secrets = ""
        try:
            from_secrets = st.secrets.get(k, "") or ""
        except Exception:
            from_secrets = ""
        secret_key = from_secrets or os.getenv(k, "")
        if secret_key:
            break

    api_key = st.text_input(
        "API Key",
        value=secret_key,
        type="password",
        help="Streamlit Cloud에서는 Secrets에 GEMINI_API_KEY 또는 OPENAI_API_KEY를 넣으세요.",
    )

    temperature = st.slider("temperature", 0.0, 1.0, 0.3, 0.05)

    st.divider()
    st.subheader("📦 재사용 패키지")
    st.markdown(
        """
- `bot/prompts/system_prompt.md` — 시스템 프롬프트
- `bot/prompts/few_shot.json` — Few-shot 3건
- `bot/prompts/input_template.md` — 입력 템플릿
- `deploy/custom_gpt_instructions.md` — Custom GPT용
        """
    )

    with st.expander("시스템 프롬프트 미리보기"):
        st.markdown(load_system_prompt())

    with st.expander("입력 템플릿"):
        st.markdown(load_input_template())
        if st.button("템플릿을 채팅 입력란에 넣기"):
            st.session_state.pending_template = (
                "[업무 과업] 정책/절차 확인 이메일 작성\n"
                "[배경 상황]\n- \n\n"
                "[확실히 모르는 것]\n1) \n2) \n3) \n\n"
                "[타겟] 담당 매니저\n"
                "[톤] 정중하고 간결한 실무 메일체\n"
                "[분량] 본문 250~350자\n"
                "[서명] "
            )
            st.rerun()

    if st.button("대화 초기화", type="secondary"):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.caption(
        "과제 문서: README.md · 실행 로그: all_log.md / log_raw.md\n"
        "재현성: temperature·모델명은 사이드바에 기록 가능"
    )

# ---- Main chat ----
col_chat, col_help = st.columns([2, 1])

with col_help:
    st.subheader("사용 방법")
    st.markdown(
        """
1. 사이드바에서 **API Key**와 모델을 설정합니다.
2. 입력 템플릿으로 배경·모르는 것을 채웁니다.
3. 확인봇이 **제목+본문 이메일**을 작성합니다.
4. 톤/채널 변경·확인사항 추가를 이어서 요청해 보세요.

**모호하면 되묻기**, **수치 불일치는 단정 금지**,
**순서 질문은 다음 행동까지** — 이게 확인봇의 핵심 규칙입니다.
        """
    )
    st.subheader("Few-shot 요약")
    for ex in load_few_shot():
        with st.expander(ex["title"]):
            st.markdown("**입력**")
            st.code(ex["user"], language=None)
            st.markdown("**출력**")
            st.code(ex["assistant"], language=None)

with col_chat:
    st.subheader("대화")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    default_chat = st.session_state.pending_template or ""
    if st.session_state.pending_template:
        st.session_state.pending_template = None

    user_input = st.chat_input(
        "배경 상황과 모르는 것을 입력하세요…",
    )

    # If template was requested, show a text area prefilled once
    if default_chat:
        st.info("템플릿이 준비되었습니다. 아래를 채운 뒤 전송하세요.")
        filled = st.text_area("템플릿 입력", value=default_chat, height=220, key="template_box")
        if st.button("템플릿 전송", type="primary"):
            user_input = filled.strip()

    if user_input:
        user_input = user_input.strip()
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        if not api_key:
            with st.chat_message("assistant"):
                st.error(
                    "API Key가 없습니다. 사이드바에 키를 입력하거나 "
                    "환경변수/Streamlit Secrets에 등록하세요."
                )
        else:
            with st.chat_message("assistant"):
                with st.spinner("확인봇이 초안을 작성 중…"):
                    try:
                        msgs = build_messages(
                            load_system_prompt(),
                            load_few_shot(),
                            st.session_state.messages[:-1],
                            user_input,
                        )
                        reply = generate_reply(
                            msgs,
                            provider=provider,
                            api_key=api_key,
                            model=model,
                            temperature=temperature,
                            base_url=base_url,
                        )
                        st.markdown(reply)
                        st.session_state.messages.append(
                            {"role": "assistant", "content": reply}
                        )
                    except Exception as e:
                        st.error(f"호출 실패: {e}")
                        st.session_state.messages.pop()
