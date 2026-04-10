# 멀티 클라우드 비용·설계 ReAct 에이전트

[![Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)

**Streamlit** 기반 채팅 UI와 **LangGraph `create_react_agent`** 로 동작하는 대화형 에이전트입니다. 사용자의 인프라 요구를 바탕으로 **멀티 클라우드 가격 참고**, **트래픽 기준 월간 유지비 추정(USD)**, **Terraform 초안 텍스트**까지 한 흐름에서 다루는 것을 목표로 합니다.  
설계 근거는 `multicloud_react_agent.seed.yaml`(v1.0)과 이를 바탕으로 작성한 설계 보고서(HTML, `multicloud_react_agent_spec_report.html`)의 내용을 요약·반영했습니다.

---

## 이 프로젝트가 하는 일

- **대화형 워크플로:** 단순 가격 나열이 아니라, 질문·가정 정리·도구 호출·요약이 이어지는 **ReAct** 패턴입니다. 복잡한 상태기계(if 분기 남용) 대신 LLM이 다음 행동(도구 선택·최종 답)을 고릅니다.
- **Azure 가격(실연동):** [Azure Retail Prices REST API](https://prices.azure.com/) 계열로 **공개 소매 카탈로그**를 조회합니다. 구독 청구 연동 없이 공개 조회만 사용합니다(온디맨드·공개 카탈로그 수준).
- **AWS / GCP 가격(시뮬):** 별도 유료 클라우드 과금 API 없이, 앱 내 **고정 목 테이블**로 참고 값을 주며 응답에 **시뮬레이션**임을 명시합니다.
- **월간 유지비 추정:** 구조화된 입력(`traffic`, `region`, `availability`, `currency_display=USD`)만 받는 **CalculatorInput** 스키마로 추정합니다. 자연어 한 덩어리만 넘기는 방식은 쓰지 않습니다.
- **Terraform 초안:** 확정된 사양 문자열을 받아 **`.tf` 형태의 텍스트 초안**만 생성합니다. **실제 `terraform apply`나 리소스 프로비저닝은 하지 않습니다.**

금액 표시는 **USD 중심**이며, 공개 카탈로그·참고 추정이며 실제 청구와 다를 수 있음을 UI·응답에서 안내합니다.

---

## 기술 스택

| 구분 | 사용 |
|------|------|
| UI | [Streamlit](https://streamlit.io/) |
| 에이전트 | [LangGraph](https://github.com/langchain-ai/langgraph) `create_react_agent`, [LangChain](https://github.com/langchain-ai/langchain) Tools |
| LLM | [OpenAI API](https://platform.openai.com/) (`langchain-openai` / Chat 모델) — ReAct 추론·도구 선택에 필요 |
| 설정 | `python-dotenv`(로컬), Streamlit Secrets(배포) |

---

## 외부 연동 요약

| 대상 | 방식 | 비고 |
|------|------|------|
| **Azure** | Retail Prices API (`prices.azure.com`) | 공개 조회, v1에서는 예약·엔터프라이즈 할인 등 복잡 과금 제외 |
| **AWS / GCP** | 앱 내 목 데이터 | 시뮬레이션 명시 |
| **OpenAI** | API 키·토큰 과금 | 에이전트 동작에 사용 |

---

## 도구(Tools) 구성

| 도구 | 역할 |
|------|------|
| `lookup_cloud_price` | 클라우드·리전·제품 힌트로 가격 조회 (Azure 실연동 / AWS·GCP 목) |
| `estimate_monthly_cost` | `CalculatorInput` 필드만으로 월간 유지비 추정(면책 문구 포함) |
| `generate_terraform_draft` | 확정 사양 문자열 → Terraform 초안 텍스트(다운로드 강제 없음) |

워크플로는 전형적인 **에이전트 ↔ 도구 루프**(START → agent → tools → … → agent → END)로, 시퀀스는 사용자 → Streamlit → ReAct 에이전트 → 도구(Azure API / 목 / 계산 / 초안) → 응답 순입니다.

---

## v1 범위와 비목표

**포함**

- Streamlit 멀티턴 대화, 위 도구 호출 가능
- Azure 가격 실패 시 짧은 오류 안내
- 목·추정치에 대한 출처·한계 표시

**포함하지 않음 (v1)**

- 실제 `terraform apply` 또는 클라우드 리소스 생성
- 예약 인스턴스·Savings Plans·엔터프라이즈 할인 등 복잡 과금 모델
- 사용자 Azure 구독에 연결한 실제 청구 조회

---

## 저장소 구조 (이 앱만)

| 파일 | 설명 |
|------|------|
| `multicloud_react_agent_app.py` | Streamlit 진입점·에이전트·대화 상태 |
| `multicloud_tools.py` | 가격·계산·Terraform 초안 도구 |
| `requirements.txt` | Python 의존성 |
| `.streamlit/config.toml` | Streamlit 설정 |
| `.env.example` | 환경 변수 예시 (`OPENAI_API_KEY` 등) |

**저장소:** [github.com/liebe1127/-ReAct](https://github.com/liebe1127/-ReAct)

---

## 로컬 실행

```powershell
git clone https://github.com/liebe1127/-ReAct.git
cd -ReAct
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# .env에 OPENAI_API_KEY 설정 후:
streamlit run multicloud_react_agent_app.py
```

---

## Streamlit Community Cloud 배포

배포 화면: **[share.streamlit.io/deploy](https://share.streamlit.io/deploy)** (또는 [share.streamlit.io](https://share.streamlit.io) 로그인 후 **New app**)

| 단계 | 할 일 |
|------|--------|
| 1 | GitHub로 Streamlit에 로그인하고, **저장소 접근 권한**을 Streamlit 앱에 허용합니다. |
| 2 | **Repository**에서 `liebe1127/-ReAct` 를 선택합니다. (목록에 없으면 **Configure**에서 조직/계정 권한을 다시 허용) |
| 3 | **Branch:** `main` |
| 4 | **Main file path:** `multicloud_react_agent_app.py` (이 저장소 루트에 앱 파일이 있음) |
| 5 | **Advanced settings** → **Python version** 은 기본값이면 보통 충분합니다. **Requirements file** 은 비워 두면 루트의 `requirements.txt` 가 사용됩니다. |
| 6 | **Deploy** 를 누릅니다. 빌드가 끝나면 `*.streamlit.app` 형태의 URL이 열립니다. |

### Secrets (필수)

앱이 동작하려면 OpenAI 키가 필요합니다. 배포된 앱 대시보드에서 **Settings → Secrets** 에 아래처럼 넣습니다(TOML 형식).

```toml
OPENAI_API_KEY = "sk-..."
# 선택
OPENAI_MODEL = "gpt-4o-mini"
```

저장 후 앱을 **Reboot** 하거나 잠시 기다리면 반영됩니다. 로컬 `.env` 는 GitHub에 없으므로 **Cloud에서는 Secrets만** 사용합니다.

---

## 면책

이 저장소의 추정·목 데이터·Terraform 초안은 **참고용**이며, 실제 인프라 비용·가용성·보안·규정 준수를 보장하지 않습니다. 프로덕션 배포 전에는 반드시 각 클라우드 공식 가격·아키텍처 검토를 수행하세요.

---

## 라이선스

저장소에 `LICENSE` 파일이 없다면, 필요 시 본인이 선택한 라이선스를 추가하시면 됩니다.
