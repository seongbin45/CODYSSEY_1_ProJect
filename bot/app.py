"""
확인봇 — 창업지원 실무 이메일 작성 코치 (Streamlit 배포용)

보너스 1: 최종 시스템 프롬프트를 재사용 가능한 형태로 배포.
- 로컬: py -3 -m streamlit run bot/app.py
- 클라우드: Streamlit Community Cloud, Main file = bot/app.py

다중 제공자 + Fallback:
  Gemini 실패 시 → Groq / OpenRouter 무료 모델 / OpenAI 순으로 자동 전환
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

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
# Provider catalog
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Provider:
    id: str
    label: str
    kind: str  # "openai_compatible" | "gemini"
    default_model: str
    base_url: str | None
    secret_keys: tuple[str, ...]
    free_note: str
    is_free_tier: bool


PROVIDERS: dict[str, Provider] = {
    "groq": Provider(
        id="groq",
        label="Groq (무료 티어 · 권장)",
        kind="openai_compatible",
        default_model="llama-3.3-70b-versatile",
        base_url="https://api.groq.com/openai/v1",
        secret_keys=("GROQ_API_KEY",),
        free_note="https://console.groq.com 에서 무료 키 발급. 한도 내 무료.",
        is_free_tier=True,
    ),
    "openrouter": Provider(
        id="openrouter",
        label="OpenRouter (무료 모델)",
        kind="openai_compatible",
        default_model="meta-llama/llama-3.3-70b-instruct:free",
        base_url="https://openrouter.ai/api/v1",
        secret_keys=("OPENROUTER_API_KEY",),
        free_note="https://openrouter.ai 키 발급 후 `:free` 모델 사용.",
        is_free_tier=True,
    ),
    "openai": Provider(
        id="openai",
        label="OpenAI ChatGPT (API)",
        kind="openai_compatible",
        default_model="gpt-4o-mini",
        base_url=None,  # 공식 OpenAI
        secret_keys=("OPENAI_API_KEY",),
        free_note="platform.openai.com 키 필요. 무료 크레딧/유료 결제 후 사용.",
        is_free_tier=False,
    ),
    "gemini": Provider(
        id="gemini",
        label="Google Gemini",
        kind="gemini",
        default_model="gemini-2.0-flash",
        base_url=None,
        secret_keys=("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        free_note="Google AI Studio 무료 티어. 지역/쿼터 제한 시 Fallback 사용.",
        is_free_tier=True,
    ),
    "custom": Provider(
        id="custom",
        label="직접 입력 (OpenAI 호환)",
        kind="openai_compatible",
        default_model="gpt-4o-mini",
        base_url="",
        secret_keys=("OPENAI_API_KEY", "CUSTOM_API_KEY"),
        free_note="Base URL을 직접 넣는 범용 엔드포인트 (xAI Grok 등).",
        is_free_tier=False,
    ),
}

# Gemini 실패 시 기본 시도 순서 (키가 있는 것만 실제 호출)
FALLBACK_ORDER: tuple[str, ...] = (
    "groq",
    "openrouter",
    "openai",
    "gemini",
)


# ---------------------------------------------------------------------------
# Secrets / env helpers
# ---------------------------------------------------------------------------


def secret_or_env(*keys: str) -> str:
    for k in keys:
        try:
            v = st.secrets.get(k, "") or ""
        except Exception:
            v = ""
        if not v:
            v = os.getenv(k, "") or ""
        if v:
            return str(v).strip()
    return ""


def resolve_api_key(provider: Provider, manual: str = "") -> str:
    if manual.strip():
        return manual.strip()
    return secret_or_env(*provider.secret_keys)


def available_providers() -> list[Provider]:
    """Secrets/env에 키가 등록된 제공자 목록."""
    found: list[Provider] = []
    for pid in FALLBACK_ORDER:
        p = PROVIDERS[pid]
        if resolve_api_key(p):
            found.append(p)
    return found


# ---------------------------------------------------------------------------
# Prompt loading
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
    messages: list[dict] = [{"role": "system", "content": system_prompt}]
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
    extra_headers: dict | None = None,
) -> str:
    from openai import OpenAI

    kwargs: dict = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    if extra_headers:
        kwargs["default_headers"] = extra_headers

    client = OpenAI(**kwargs)
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
    try:
        from google import genai
        from google.genai import types
    except ImportError as e:
        raise RuntimeError(
            "google-genai 패키지가 없습니다. `pip install google-genai` 후 다시 시도하세요."
        ) from e

    client = genai.Client(api_key=api_key)
    system_parts = [m["content"] for m in messages if m["role"] == "system"]
    system_instruction = "\n\n".join(system_parts) or None

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


def call_provider(
    provider: Provider,
    messages: list[dict],
    *,
    api_key: str,
    model: str,
    temperature: float,
    base_url_override: str | None = None,
) -> str:
    if provider.kind == "gemini":
        return call_gemini(
            messages, api_key=api_key, model=model, temperature=temperature
        )

    base_url = base_url_override if base_url_override is not None else provider.base_url
    extra = None
    if provider.id == "openrouter":
        # OpenRouter 권장 헤더 (앱 식별)
        extra = {
            "HTTP-Referer": "https://github.com/seongbin45/CODYSSEY_1_ProJect",
            "X-Title": "ConfirmBot",
        }
    return call_openai_compatible(
        messages,
        api_key=api_key,
        base_url=base_url or None,
        model=model,
        temperature=temperature,
        extra_headers=extra,
    )


def generate_with_fallback(
    messages: list[dict],
    *,
    temperature: float,
    primary_id: str | None,
    manual_keys: dict[str, str],
    model_overrides: dict[str, str],
    custom_base_url: str | None,
    on_try: Callable[[str, str], None] | None = None,
) -> tuple[str, str, str]:
    """
    Returns (reply, used_provider_id, used_model).
    Tries primary first (if set), then FALLBACK_ORDER for any provider with a key.
    """
    tried: list[str] = []
    errors: list[str] = []

    order: list[str] = []
    if primary_id and primary_id != "auto":
        order.append(primary_id)
    for pid in FALLBACK_ORDER:
        if pid not in order:
            order.append(pid)
    if "custom" not in order and manual_keys.get("custom"):
        order.append("custom")

    for pid in order:
        provider = PROVIDERS[pid]
        key = manual_keys.get(pid) or resolve_api_key(provider)
        if not key:
            continue

        model = model_overrides.get(pid) or provider.default_model
        base_override = custom_base_url if pid == "custom" else None

        label = provider.label
        if on_try:
            on_try(pid, model)
        tried.append(f"{label} ({model})")

        try:
            reply = call_provider(
                provider,
                messages,
                api_key=key,
                model=model,
                temperature=temperature,
                base_url_override=base_override,
            )
            if not reply:
                raise RuntimeError("빈 응답")
            return reply, pid, model
        except Exception as e:
            errors.append(f"· {label}: {e}")
            continue

    detail = "\n".join(errors) if errors else "등록된 API 키가 없습니다."
    tried_s = ", ".join(tried) if tried else "(시도 없음)"
    raise RuntimeError(
        "모든 LLM 호출에 실패했습니다.\n"
        f"시도: {tried_s}\n\n"
        f"{detail}\n\n"
        "해결: Streamlit Secrets에 GROQ_API_KEY / OPENROUTER_API_KEY / "
        "OPENAI_API_KEY / GEMINI_API_KEY 중 하나 이상을 등록하세요.\n"
        "무료 권장: Groq (console.groq.com) → OPENROUTER → (유료/크레딧) OpenAI → Gemini"
    )


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
    "창업지원 실무 이메일 코치 · 다중 LLM (Groq 무료 / OpenRouter 무료 / OpenAI / Gemini) "
    "+ 자동 Fallback"
)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_template" not in st.session_state:
    st.session_state.pending_template = None
if "last_provider" not in st.session_state:
    st.session_state.last_provider = None

# ---- Sidebar ----
with st.sidebar:
    st.header("⚙️ LLM 설정")

    mode = st.radio(
        "호출 모드",
        ["자동 Fallback (권장)", "수동 선택"],
        help=(
            "자동: 키가 있는 제공자를 순서대로 시도. "
            "한 곳이 실패(쿼터/지역/오류)해도 다음 무료·유료 키로 이어갑니다."
        ),
    )

    provider_options = {
        "groq": PROVIDERS["groq"].label,
        "openrouter": PROVIDERS["openrouter"].label,
        "openai": PROVIDERS["openai"].label,
        "gemini": PROVIDERS["gemini"].label,
        "custom": PROVIDERS["custom"].label,
    }

    primary_id: str | None
    if mode == "자동 Fallback (권장)":
        primary_id = "auto"
        st.info(
            "**Fallback 순서:** Groq(무료) → OpenRouter(무료) → OpenAI → Gemini\n\n"
            "등록된 키만 실제로 호출합니다. Gemini가 막혀도 Groq 키가 있으면 동작합니다."
        )
    else:
        pick = st.selectbox(
            "Provider",
            list(provider_options.keys()),
            format_func=lambda k: provider_options[k],
        )
        primary_id = pick

    # Status of registered keys
    st.subheader("키 등록 상태")
    for pid in ("groq", "openrouter", "openai", "gemini"):
        p = PROVIDERS[pid]
        ok = bool(resolve_api_key(p))
        badge = "✅" if ok else "⬜"
        free = "무료" if p.is_free_tier else "유료/크레딧"
        st.caption(f"{badge} {p.label} · {free}")

    st.divider()
    st.subheader("키 / 모델 (수동 입력 가능)")

    manual_keys: dict[str, str] = {}
    model_overrides: dict[str, str] = {}

    with st.expander("Groq (무료 권장)", expanded=(primary_id in ("auto", "groq"))):
        st.caption(PROVIDERS["groq"].free_note)
        manual_keys["groq"] = st.text_input(
            "GROQ_API_KEY",
            value=resolve_api_key(PROVIDERS["groq"]),
            type="password",
            key="key_groq",
        )
        model_overrides["groq"] = st.text_input(
            "Groq 모델",
            value=PROVIDERS["groq"].default_model,
            key="model_groq",
        )

    with st.expander("OpenRouter (무료 모델)", expanded=(primary_id == "openrouter")):
        st.caption(PROVIDERS["openrouter"].free_note)
        manual_keys["openrouter"] = st.text_input(
            "OPENROUTER_API_KEY",
            value=resolve_api_key(PROVIDERS["openrouter"]),
            type="password",
            key="key_or",
        )
        model_overrides["openrouter"] = st.text_input(
            "OpenRouter 모델",
            value=PROVIDERS["openrouter"].default_model,
            key="model_or",
            help="무료 모델은 이름 끝에 :free",
        )

    with st.expander("OpenAI ChatGPT", expanded=(primary_id == "openai")):
        st.caption(PROVIDERS["openai"].free_note)
        manual_keys["openai"] = st.text_input(
            "OPENAI_API_KEY",
            value=resolve_api_key(PROVIDERS["openai"]),
            type="password",
            key="key_oai",
        )
        model_overrides["openai"] = st.text_input(
            "OpenAI 모델",
            value=PROVIDERS["openai"].default_model,
            key="model_oai",
            help="gpt-4o-mini / gpt-4o / gpt-4.1-mini 등",
        )

    with st.expander("Google Gemini", expanded=(primary_id == "gemini")):
        st.caption(PROVIDERS["gemini"].free_note)
        manual_keys["gemini"] = st.text_input(
            "GEMINI_API_KEY",
            value=resolve_api_key(PROVIDERS["gemini"]),
            type="password",
            key="key_gem",
        )
        model_overrides["gemini"] = st.text_input(
            "Gemini 모델",
            value=PROVIDERS["gemini"].default_model,
            key="model_gem",
        )

    custom_base_url = None
    with st.expander("직접 입력 (OpenAI 호환)", expanded=(primary_id == "custom")):
        st.caption(PROVIDERS["custom"].free_note)
        manual_keys["custom"] = st.text_input(
            "API Key",
            value=resolve_api_key(PROVIDERS["custom"]),
            type="password",
            key="key_custom",
        )
        custom_base_url = st.text_input(
            "Base URL",
            value=os.getenv("OPENAI_BASE_URL", "https://api.x.ai/v1"),
            key="base_custom",
            help="예: https://api.x.ai/v1 (Grok)",
        ).strip() or None
        model_overrides["custom"] = st.text_input(
            "모델명",
            value="grok-2-latest",
            key="model_custom",
        )

    temperature = st.slider("temperature", 0.0, 1.0, 0.3, 0.05)

    if st.session_state.last_provider:
        st.success(f"직전 사용: **{st.session_state.last_provider}**")

    st.divider()
    st.subheader("📦 재사용 패키지")
    st.markdown(
        """
- `bot/prompts/system_prompt.md`
- `bot/prompts/few_shot.json`
- `bot/prompts/input_template.md`
- `deploy/custom_gpt_instructions.md`
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
        st.session_state.last_provider = None
        st.rerun()

    st.divider()
    st.caption(
        "Secrets 예시: GROQ_API_KEY / OPENROUTER_API_KEY / "
        "OPENAI_API_KEY / GEMINI_API_KEY\n"
        "→ .streamlit/secrets.toml.example 참고"
    )

# ---- Main ----
col_chat, col_help = st.columns([2, 1])

with col_help:
    st.subheader("사용 방법")
    st.markdown(
        """
1. **무료로 쓰려면** Groq 또는 OpenRouter 키를 Secrets에 넣습니다.
2. **ChatGPT**를 쓰려면 OpenAI API 키를 넣습니다.
3. **자동 Fallback**이면 Gemini가 실패해도 다음 키로 이어집니다.
4. 입력 템플릿으로 배경·모르는 것을 채웁니다.

**모호하면 되묻기** · **수치 단정 금지** · **순서 질문은 다음 행동까지**
        """
    )
    st.subheader("Gemini가 안 될 때")
    st.markdown(
        """
| 상황 | 대응 |
|------|------|
| 지역/쿼터 오류 | 자동 Fallback → **Groq** |
| 키 없음 | console.groq.com 무료 키 |
| 그래도 실패 | OpenRouter `:free` 모델 |
| 품질 우선 | OpenAI `gpt-4o-mini` |

앱은 **키가 있는 제공자만** 순서대로 시도합니다.
Gemini에 의존하지 않습니다.
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

    user_input = st.chat_input("배경 상황과 모르는 것을 입력하세요…")

    if default_chat:
        st.info("템플릿이 준비되었습니다. 아래를 채운 뒤 전송하세요.")
        filled = st.text_area(
            "템플릿 입력", value=default_chat, height=220, key="template_box"
        )
        if st.button("템플릿 전송", type="primary"):
            user_input = filled.strip()

    if user_input:
        user_input = user_input.strip()
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        any_key = any(
            (manual_keys.get(pid) or resolve_api_key(PROVIDERS[pid]))
            for pid in FALLBACK_ORDER
        ) or bool(manual_keys.get("custom"))

        if not any_key:
            with st.chat_message("assistant"):
                st.error(
                    "등록된 API 키가 없습니다.\n\n"
                    "무료 권장: [Groq](https://console.groq.com) 에서 키 발급 → "
                    "사이드바 또는 Streamlit Secrets에 `GROQ_API_KEY`\n\n"
                    "또는 OpenRouter / OpenAI / Gemini 키 중 하나."
                )
                st.session_state.messages.pop()
        else:
            with st.chat_message("assistant"):
                status = st.empty()
                with st.spinner("확인봇이 초안을 작성 중…"):
                    try:
                        msgs = build_messages(
                            load_system_prompt(),
                            load_few_shot(),
                            st.session_state.messages[:-1],
                            user_input,
                        )

                        def _on_try(pid: str, model: str) -> None:
                            status.caption(
                                f"시도 중: {PROVIDERS[pid].label} · `{model}`"
                            )

                        reply, used_pid, used_model = generate_with_fallback(
                            msgs,
                            temperature=temperature,
                            primary_id=primary_id,
                            manual_keys=manual_keys,
                            model_overrides=model_overrides,
                            custom_base_url=custom_base_url,
                            on_try=_on_try,
                        )
                        used_label = PROVIDERS[used_pid].label
                        st.session_state.last_provider = f"{used_label} / {used_model}"
                        status.caption(f"✓ 사용: **{used_label}** · `{used_model}`")
                        st.markdown(reply)
                        st.session_state.messages.append(
                            {"role": "assistant", "content": reply}
                        )
                    except Exception as e:
                        status.empty()
                        st.error(str(e))
                        st.session_state.messages.pop()
