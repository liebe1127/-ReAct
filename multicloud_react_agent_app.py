"""
멀티 클라우드 비용·프로비저닝 ReAct 에이전트 (Streamlit).
Seed: multicloud_react_agent - Azure 실연동 가격, AWS/GCP 목, CalculatorInput, Terraform 초안.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

load_dotenv(_APP_DIR / ".env")
load_dotenv(_APP_DIR.parent / ".env")
load_dotenv()

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from multicloud_tools import MULTICLOUD_TOOLS

SYSTEM_PROMPT = """당신은 멀티 클라우드(Azure, AWS, GCP) 비용·아키텍처 자문가입니다.

역할:
- 사용자 요구를 파악하고, 필요하면 도구로 공개 가격·월간 추정·Terraform 초안을 제공합니다.
- Azure 가격은 공개 Retail API(실연동), AWS/GCP 가격 도구는 시뮬레이션(목)입니다. 혼동하지 않도록 응답에 분명히 적습니다.
- 월간 유지비는 반드시 `estimate_monthly_cost` 도구를 사용하며, 인자는 traffic, region, availability, currency_display(USD) 네 필드만 사용합니다. 값이 부족하면 사용자에게 짧게 질문한 뒤 호출합니다.
- 가격·비용은 항상 USD로 안내하고, 공개 카탈로그·참고 추정이며 실제 청구와 다를 수 있음을 한 문장 이상 포함합니다.
- Terraform은 `generate_terraform_draft`로 확정된 사양 문자열만 받아 초안을 냅니다. apply나 실제 프로비저닝은 하지 않습니다.
- 한국어로 간결하고 실무적으로 답합니다. 다음에 물어볼 만한 한 가지를 제안할 수 있습니다."""


class MulticloudReActAgent:
    """create_react_agent 그래프를 감싸 멀티턴 대화 맥락을 유지합니다."""

    def __init__(self, model: Optional[str] = None) -> None:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY가 설정되어 있지 않습니다.")
        self._llm = ChatOpenAI(model=model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
        self._graph = create_react_agent(
            self._llm,
            MULTICLOUD_TOOLS,
            prompt=SYSTEM_PROMPT,
        )
        self.history: List[BaseMessage] = []

    def chat(self, user_input: str) -> str:
        self.history.append(HumanMessage(content=user_input))
        result = self._graph.invoke({"messages": self.history})
        self.history = list(result["messages"])
        last = self.history[-1]
        if isinstance(last, AIMessage) and last.content:
            return str(last.content)
        return "(도구 호출만 있고 최종 텍스트가 없습니다. 다시 시도해 주세요.)"

    def reset(self) -> None:
        self.history = []


def _inject_openai_secrets_from_streamlit(st: object) -> None:
    """Streamlit Community Cloud 등: 대시보드 Secrets를 os.environ에 반영."""
    try:
        secrets = getattr(st, "secrets", None)
        if not secrets:
            return
        for key in ("OPENAI_API_KEY", "OPENAI_MODEL"):
            if key in secrets:
                os.environ[key] = str(secrets[key])
    except Exception:
        pass


def _ensure_agent(st: object) -> Optional[MulticloudReActAgent]:
    if st.session_state.agent is not None:
        return st.session_state.agent
    if not os.getenv("OPENAI_API_KEY"):
        return None
    st.session_state.agent = MulticloudReActAgent()
    return st.session_state.agent


def run_streamlit() -> None:
    import streamlit as st

    st.set_page_config(
        page_title="멀티 클라우드 ReAct",
        page_icon="☁️",
        layout="wide",
    )
    _inject_openai_secrets_from_streamlit(st)

    st.title("멀티 클라우드 비용·설계 ReAct")
    st.caption(
        "Azure 공개 가격 API | AWS·GCP 목 시뮬 | 월간 추정(USD) | Terraform 초안(텍스트만)"
    )

    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "ui_messages" not in st.session_state:
        st.session_state.ui_messages = []

    with st.sidebar:
        st.markdown("**안내**")
        st.info(
            "모든 금액은 **USD** 기준 **참고 추정**입니다. "
            "공개 카탈로그 수준이며, 예약·엔터프라이즈 할인·실제 청구와 다를 수 있습니다."
        )
        st.markdown("**도구**")
        st.markdown(
            "- `lookup_cloud_price`: Azure 실연동 / AWS·GCP 목\n"
            "- `estimate_monthly_cost`: CalculatorInput 필드만\n"
            "- `generate_terraform_draft`: 확정 사양 문자열"
        )
        if st.button("대화 초기화"):
            if st.session_state.agent is not None:
                st.session_state.agent.reset()
            st.session_state.ui_messages = []
            st.rerun()

    agent = _ensure_agent(st)
    if agent is None:
        st.warning(
            "**OPENAI_API_KEY**가 없습니다.\n\n"
            f"- **로컬:** `{_APP_DIR}` 또는 상위 폴더의 `.env`에 "
            "`OPENAI_API_KEY=sk-...` 를 넣고 새로고침하세요.\n"
            "- **Streamlit Cloud:** 앱 설정 → **Secrets**에 "
            "`OPENAI_API_KEY` / (선택) `OPENAI_MODEL` 을 TOML 형식으로 추가하세요."
        )
        st.stop()

    col_chat, col_hint = st.columns([2, 1])
    with col_hint:
        st.subheader("한 화면 요약")
        st.markdown(
            "비용·권장안·다음 질문은 채팅에서 이어집니다. "
            "Azure는 공개 Retail API, AWS/GCP 조회는 시뮬레이션입니다."
        )

    with col_chat:
        for role, text in st.session_state.ui_messages:
            with st.chat_message(role):
                st.markdown(text)

        if prompt := st.chat_input("요구사항이나 리전·트래픽을 입력하세요…"):
            st.session_state.ui_messages.append(("user", prompt))
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("ReAct 실행 중…"):
                    try:
                        reply = agent.chat(prompt)
                    except Exception as e:
                        reply = f"오류: {e}"
                st.markdown(reply)
            st.session_state.ui_messages.append(("assistant", reply))


def _main() -> None:
    run_streamlit()


if __name__ == "__main__":
    _main()
