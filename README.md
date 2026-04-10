# 멀티 클라우드 가격·설계 ReAct (Streamlit)

**저장소:** [github.com/liebe1127/-ReAct](https://github.com/liebe1127/-ReAct)

이 폴더만 복사하거나 이 폴더만 GitHub 저장소로 올리면 됩니다. (노트북·기타 실습 파일 불필요)

## 포함 파일

| 파일 | 설명 |
|------|------|
| `multicloud_react_agent_app.py` | Streamlit 진입점 |
| `multicloud_tools.py` | 가격·계산·Terraform 초안 도구 |
| `requirements.txt` | Python 의존성 |
| `.streamlit/config.toml` | Streamlit 설정 |
| `.env.example` | API 키 템플릿 (실제 키는 `.env`에, 커밋 금지) |

## 로컬 실행

```powershell
cd multicloud-app
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# .env에 OPENAI_API_KEY 편집 후:
streamlit run multicloud_react_agent_app.py
```

## Streamlit Community Cloud

1. [share.streamlit.io](https://share.streamlit.io)에서 이 GitHub 저장소를 연결합니다.
2. Main file path: `multicloud_react_agent_app.py` (저장소 루트가 `multicloud-app`인 경우)
3. Secrets에 `OPENAI_API_KEY` (및 선택 `OPENAI_MODEL`)를 설정합니다.

저장소 루트가 상위 폴더인 경우 Main file path는 `multicloud-app/multicloud_react_agent_app.py` 로 지정합니다.
