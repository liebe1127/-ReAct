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


def _inject_sky_cloud_theme_css(st: object) -> None:
    """하늘색 그라데이션 + 구름 느낌(방사형 그라데이션) 배경."""
    st.markdown(
        """
<style>
  /* 전체 앱: 하늘 그라데이션 + 반복 구름(흰색 타원 레이어) */
  .stApp {
    background:
      radial-gradient(ellipse 260px 100px at 48% 12%, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.35) 52%, transparent 72%),
      radial-gradient(ellipse 200px 85px at 8% 28%, rgba(255,255,255,0.78) 0%, transparent 68%),
      radial-gradient(ellipse 220px 90px at 92% 22%, rgba(255,255,255,0.72) 0%, transparent 68%),
      radial-gradient(ellipse 180px 75px at 22% 48%, rgba(255,255,255,0.55) 0%, transparent 65%),
      radial-gradient(ellipse 210px 80px at 78% 52%, rgba(255,255,255,0.5) 0%, transparent 65%),
      radial-gradient(ellipse 160px 65px at 55% 72%, rgba(255,255,255,0.4) 0%, transparent 62%),
      linear-gradient(180deg, #4da6d9 0%, #6eb8e8 18%, #8ec9f0 38%, #b8ddf7 62%, #d9eefb 82%, #eef8fc 100%) !important;
    background-attachment: fixed;
  }
  [data-testid="stSidebar"] {
    background: linear-gradient(185deg, rgba(232,248,255,0.97) 0%, rgba(200,230,250,0.92) 100%) !important;
    border-right: 1px solid rgba(80, 140, 200, 0.18);
  }
  [data-testid="stHeader"] {
    background: rgba(255,255,255,0.35);
    backdrop-filter: blur(8px);
  }
  .main .block-container {
    padding-top: 1.25rem;
    padding-bottom: 2rem;
  }
  /* 채팅 말풍선: 살짝 유리 느낌 */
  [data-testid="stChatMessage"] {
    background: rgba(255,255,255,0.72) !important;
    border: 1px solid rgba(100, 160, 220, 0.2);
    border-radius: 14px;
    backdrop-filter: blur(6px);
    margin-bottom: 0.5rem;
  }
  div[data-testid="stChatInput"] {
    border-radius: 12px;
    border: 1px solid rgba(80, 140, 200, 0.25);
    background: rgba(255,255,255,0.85);
  }
  h1 {
    color: #0d47a1 !important;
    text-shadow: 0 1px 2px rgba(255,255,255,0.8);
  }
</style>
""",
        unsafe_allow_html=True,
    )


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


def _effective_openai_key(st: object) -> Optional[str]:
    """사이드바 입력 > 환경변수/Secrets 순."""
    u = str(st.session_state.get("user_openai_key", "")).strip()
    if u:
        return u
    v = os.getenv("OPENAI_API_KEY")
    return v.strip() if v and v.strip() else None


def _compose_template_question(
    goal: str,
    cloud: str,
    region: str,
    product_hint: str,
    traffic: str,
    availability: str,
    tf_spec: str,
) -> str:
    """사이드바 선택값으로 자연어 질문 한 덩어리 생성."""
    c = (cloud or "azure").strip().lower()
    r = (region or "koreacentral").strip()
    if goal == "가격 조회":
        ph = (product_hint or "Virtual Machines").strip()
        return (
            f"{c.upper()} {r} 리전에서 {ph} 관련 공개 가격(온디맨드·공개 카탈로그)을 조회해 줘. "
            f"AWS/GCP는 시뮬레이션임을 분명히 하고, 금액은 USD로 알려 줘."
        )
    if goal == "월간 유지비 추정":
        t = (traffic or "100 RPS").strip()
        a = (availability or "다중 AZ").strip()
        return (
            f"트래픽은 {t}, 리전은 {r} (참고: {c.upper()}), 가용성은 {a}로 가정하고 "
            f"월간 유지비를 USD로 대략 추정해 줘. 공개 카탈로그 기준 참고 추정임을 명시해 줘."
        )
    if goal == "Terraform 초안":
        s = (tf_spec or "").strip() or (
            "한국 중부 리전, 리소스 그룹·VNet·서브넷만 있는 웹 앱용 최소 구성"
        )
        return (
            f"아래를 확정 사양으로 보고 Terraform 초안(.tf 텍스트)만 만들어 줘. apply/provisioning은 하지 마.\n\n"
            f"사양: {s}"
        )
    return ""


def _ensure_agent(st: object) -> Optional[MulticloudReActAgent]:
    ef = _effective_openai_key(st)
    if not ef:
        st.session_state.agent = None
        st.session_state._agent_bound_key = None
        return None

    prev = st.session_state.get("_agent_bound_key")
    if prev != ef:
        st.session_state.agent = None
        st.session_state.ui_messages = []
        st.session_state._agent_bound_key = ef

    if st.session_state.agent is not None:
        return st.session_state.agent

    os.environ["OPENAI_API_KEY"] = ef
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
    _inject_sky_cloud_theme_css(st)

    st.title("멀티 클라우드 비용·설계 ReAct")
    st.caption(
        "Azure 공개 가격 API | AWS·GCP 목 시뮬 | 월간 추정(USD) | Terraform 초안(텍스트만)"
    )

    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "ui_messages" not in st.session_state:
        st.session_state.ui_messages = []
    if "user_openai_key" not in st.session_state:
        st.session_state.user_openai_key = ""
    if "chat_draft" not in st.session_state:
        st.session_state.chat_draft = ""

    with st.sidebar:
        st.markdown("**OpenAI API 키**")
        st.text_input(
            "아래에 키를 입력하세요",
            type="password",
            key="user_openai_key",
            placeholder="sk-...",
            help="브라우저에만 유지되며 서버 로그에 출력하지 않습니다. "
            "비워 두면 .env / Streamlit Secrets의 OPENAI_API_KEY를 사용합니다.",
        )
        st.caption(
            "키는 세션 메모리에만 있으며, 저장소에 커밋되지 않습니다. "
            "공용 배포 시 본인 키 사용에 유의하세요."
        )
        st.markdown("---")
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
        with st.expander("질문 도우미 (템플릿)", expanded=False):
            st.caption("선택 후 아래 버튼으로 메시지 칸을 채웁니다. 필요하면 본문에서 수정하세요.")
            tpl_goal = st.radio(
                "목적",
                ("가격 조회", "월간 유지비 추정", "Terraform 초안", "자유 질문"),
                horizontal=False,
                key="tpl_goal",
            )
            cloud_labels = {
                "azure": "Azure",
                "aws": "AWS",
                "gcp": "GCP",
            }
            tpl_cloud = st.selectbox(
                "클라우드",
                ("azure", "aws", "gcp"),
                format_func=lambda x: cloud_labels.get(x, x),
                key="tpl_cloud",
            )
            region_presets: List[tuple[str, str]] = [
                ("Azure 한국 중부 (koreacentral)", "koreacentral"),
                ("AWS 서울 (ap-northeast-2)", "ap-northeast-2"),
                ("AWS 북미 (us-east-1)", "us-east-1"),
                ("GCP 서울 (asia-northeast3)", "asia-northeast3"),
                ("GCP 아이오와 (us-central1)", "us-central1"),
                ("직접 입력", "custom"),
            ]
            tpl_region_choice = st.selectbox(
                "리전",
                options=[x[0] for x in region_presets],
                key="tpl_region_label",
            )
            region_map = dict(region_presets)
            _label = tpl_region_choice
            tpl_region = region_map[_label]
            if tpl_region == "custom":
                tpl_region = st.text_input(
                    "리전 코드",
                    value="koreacentral",
                    key="tpl_region_custom",
                ).strip()

            tpl_product = st.text_input(
                "제품/서비스 힌트 (가격 조회)",
                value="Virtual Machines",
                key="tpl_product",
                help="예: Virtual Machines, Storage",
            )
            tpl_traffic = st.text_input(
                "트래픽 (월비 추정)",
                value="50 RPS",
                key="tpl_traffic",
                help="숫자와 단위: RPS, 일 요청 수, GB/월 등",
            )
            tpl_avail = st.radio(
                "가용성 (월비 추정)",
                ("단일 AZ", "다중 AZ"),
                horizontal=True,
                key="tpl_avail",
            )
            tpl_tf = st.text_area(
                "Terraform 사양 요약",
                value="koreacentral, 리소스 그룹·VNet·서브넷, 웹 앱용 최소 구성",
                height=80,
                key="tpl_tf",
            )
            if st.button("이 설정으로 메시지 칸 채우기", type="secondary"):
                if tpl_goal == "자유 질문":
                    st.session_state.chat_draft = ""
                else:
                    st.session_state.chat_draft = _compose_template_question(
                        tpl_goal,
                        tpl_cloud,
                        tpl_region,
                        tpl_product,
                        tpl_traffic,
                        tpl_avail,
                        tpl_tf,
                    )
                st.rerun()

        if st.button("대화 초기화"):
            if st.session_state.agent is not None:
                st.session_state.agent.reset()
            st.session_state.ui_messages = []
            st.rerun()

    agent = _ensure_agent(st)
    if agent is None:
        st.warning(
            "**OpenAI API 키**가 필요합니다.\n\n"
            "- **왼쪽 사이드바**에 본인의 `OPENAI_API_KEY`를 입력하거나,\n"
            f"- **로컬:** `{_APP_DIR}` 또는 상위 폴더 `.env`에 설정하거나,\n"
            "- **Streamlit Cloud:** 앱 **Secrets**에 `OPENAI_API_KEY`를 넣어 주세요."
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

        st.markdown("**메시지** (사이드바 템플릿으로 채우거나 직접 입력)")
        st.text_area(
            "메시지 본문",
            label_visibility="collapsed",
            height=120,
            key="chat_draft",
            placeholder="예: Azure koreacentral에서 VM 가격을 USD로 알려줘 …",
        )
        send_col1, send_col2 = st.columns([1, 5])
        with send_col1:
            do_send = st.button("전송", type="primary", use_container_width=True)
        with send_col2:
            st.caption("전송 후 아래에 답변이 쌓입니다.")

        if do_send:
            prompt = str(st.session_state.get("chat_draft", "")).strip()
            if prompt:
                with st.spinner("ReAct 실행 중…"):
                    try:
                        reply = agent.chat(prompt)
                    except Exception as e:
                        reply = f"오류: {e}"
                st.session_state.ui_messages.append(("user", prompt))
                st.session_state.ui_messages.append(("assistant", reply))
                st.session_state.chat_draft = ""
                st.rerun()
            else:
                st.warning("메시지를 입력하거나 사이드바에서 템플릿을 채운 뒤 전송하세요.")


def _main() -> None:
    run_streamlit()


if __name__ == "__main__":
    _main()
