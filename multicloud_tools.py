"""
멀티 클라우드 가격·계산·Terraform 초안 도구 (Seed: multicloud_react_agent).
Azure: 공개 Retail Prices API. AWS/GCP: 목(시뮬레이션 명시).
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field

AZURE_RETAIL_BASE = "https://prices.azure.com/api/retail/prices"

# --- 목 가격 테이블 (AWS/GCP 시뮬레이션, USD) --------------------------------

_MOCK_AWS: dict[str, dict[str, object]] = {
    "us-east-1": {
        "ec2_t3_medium_od": 0.0416,
        "s3_std_per_gb": 0.023,
        "alb_lcu_per_hour": 0.0225,
        "note": "온디맨드 가정의 고정 목 값 (실제 청구와 다를 수 있음)",
    },
    "ap-northeast-2": {
        "ec2_t3_medium_od": 0.0448,
        "s3_std_per_gb": 0.025,
        "alb_lcu_per_hour": 0.024,
        "note": "온디맨드 가정의 고정 목 값 (실제 청구와 다를 수 있음)",
    },
}

_MOCK_GCP: dict[str, dict[str, object]] = {
    "asia-northeast3": {
        "n2_standard_2_od": 0.0971,
        "cloud_storage_std_per_gb": 0.020,
        "http_lb_proxy_per_hour": 0.025,
        "note": "온디맨드 가정의 고정 목 값 (실제 청구와 다를 수 있음)",
    },
    "us-central1": {
        "n2_standard_2_od": 0.0884,
        "cloud_storage_std_per_gb": 0.020,
        "http_lb_proxy_per_hour": 0.025,
        "note": "온디맨드 가정의 고정 목 값 (실제 청구와 다를 수 있음)",
    },
}


def _fetch_azure_retail_page(region: str, top: int = 200) -> dict:
    filt = f"armRegionName eq '{region}'"
    qs = urllib.parse.urlencode({"$filter": filt, "$top": str(top)})
    url = f"{AZURE_RETAIL_BASE}?{qs}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _azure_price_summary(region: str, product_or_service_hint: str) -> str:
    """공개 Retail API로 지역별 항목을 가져와 힌트로 필터링."""
    try:
        data = _fetch_azure_retail_page(region)
    except urllib.error.HTTPError as e:
        return f"Azure 가격 API HTTP 오류: {e.code} — 잠시 후 다시 시도하거나 리전·필터를 확인하세요."
    except urllib.error.URLError as e:
        return f"Azure 가격 API 연결 실패: {e.reason!s}"
    except (TimeoutError, json.JSONDecodeError, OSError) as e:
        return f"Azure 가격 조회 실패: {e!s}"

    items = data.get("Items") or []
    hint = (product_or_service_hint or "").strip().lower()
    matched: list[dict] = []
    for it in items:
        pn = (it.get("productName") or "").lower()
        sn = (it.get("serviceName") or "").lower()
        if hint and (hint in pn or hint in sn):
            matched.append(it)
    if not matched and hint:
        matched = items[:8]
    elif not matched:
        matched = items[:8]

    lines = [
        "**Azure 공개 Retail 카탈로그 (USD, 참고용)**",
        f"- 리전: `{region}` | 힌트: `{product_or_service_hint or '(전체 샘플)'}`",
        "",
    ]
    for it in matched[:12]:
        unit = it.get("unitOfMeasure") or ""
        cur = it.get("currencyCode") or "USD"
        price = it.get("retailPrice")
        name = it.get("productName") or it.get("serviceName") or "N/A"
        sku = it.get("skuName") or ""
        lines.append(f"- **{name}** ({sku}) — {price} {cur}/{unit}".strip())
    lines.append("")
    lines.append(
        "_공개 카탈로그 기준 참고 추정이며, 실제 청구·할인·세금과 다를 수 있습니다._"
    )
    return "\n".join(lines)


def _mock_aws_price(region: str, hint: str) -> str:
    row = _MOCK_AWS.get(region) or _MOCK_AWS["us-east-1"]
    lines = [
        "**AWS 가격 (시뮬레이션 / 목 데이터, USD)**",
        f"- 리전: `{region}` | 힌트: `{hint}`",
        "",
        f"- EC2 t3.medium 온디맨드(목): 약 **${row['ec2_t3_medium_od']}/시간**",
        f"- S3 표준 스토리지(목): 약 **${row['s3_std_per_gb']}/GB-월**",
        f"- ALB LCU(목): 약 **${row['alb_lcu_per_hour']}/LCU-시간** (개략)",
        "",
        f"_{row['note']}._",
    ]
    return "\n".join(lines)


def _mock_gcp_price(region: str, hint: str) -> str:
    row = _MOCK_GCP.get(region) or _MOCK_GCP["us-central1"]
    lines = [
        "**GCP 가격 (시뮬레이션 / 목 데이터, USD)**",
        f"- 리전: `{region}` | 힌트: `{hint}`",
        "",
        f"- N2 standard 2 vCPU(목): 약 **${row['n2_standard_2_od']}/시간**",
        f"- Cloud Storage 표준(목): 약 **${row['cloud_storage_std_per_gb']}/GB-월**",
        f"- HTTP(S) LB 프록시(목): 약 **${row['http_lb_proxy_per_hour']}/시간** (개략)",
        "",
        f"_{row['note']}._",
    ]
    return "\n".join(lines)


@tool
def lookup_cloud_price(
    cloud: str,
    region: str,
    product_or_service_hint: str = "",
) -> str:
    """인스턴스/서비스 사양별 가격 조회. cloud는 azure(실연동), aws(목), gcp(목). region은 공급자 리전 코드."""
    c = (cloud or "").strip().lower()
    if c == "azure":
        return _azure_price_summary(region.strip(), product_or_service_hint.strip())
    if c == "aws":
        return _mock_aws_price(region.strip(), product_or_service_hint.strip())
    if c == "gcp":
        return _mock_gcp_price(region.strip(), product_or_service_hint.strip())
    return (
        "cloud는 `azure`, `aws`, `gcp` 중 하나로 지정하세요. "
        "Azure는 공개 Retail API, AWS/GCP는 시뮬레이션 목입니다."
    )


class CalculatorInput(BaseModel):
    """월간 유지비 추정에 사용하는 구조화된 입력(ReAct가 대화에서 채운 뒤 도구 호출)."""

    traffic: str = Field(
        description="예상 트래픽 수치와 단위를 함께 명시(RPS, 일 요청 수, GB/월 등)."
    )
    region: str = Field(description="선호 리전 코드(예: Azure koreacentral).")
    availability: str = Field(
        description="가용성 목표(단일 AZ / 다중 AZ, 또는 가동률 가정 등)."
    )
    currency_display: Literal["USD"] = Field(
        default="USD",
        description="표시 통화. 본 프로젝트는 USD 고정 + 참고 추정 전제.",
    )


def _parse_traffic_numbers(text: str) -> list[float]:
    return [float(x) for x in re.findall(r"[\d.]+", text or "")]


@tool(args_schema=CalculatorInput)
def estimate_monthly_cost(
    traffic: str,
    region: str,
    availability: str,
    currency_display: Literal["USD"] = "USD",
) -> str:
    """사용자 트래픽 예상치 등 입력 필드 기반 월간 유지비 계산. 인자는 CalculatorInput 필드만 사용."""
    nums = _parse_traffic_numbers(traffic)
    primary = nums[0] if nums else 100.0
    tl = (traffic or "").lower()
    mult_az = "다중" in (availability or "") or "multi" in (availability or "").lower()

    if "rps" in tl:
        monthly_requests = primary * 3600 * 24 * 30
    elif "일" in tl or "day" in tl or "/일" in tl:
        monthly_requests = primary * 30
    elif "gb" in tl or "tb" in tl:
        monthly_requests = primary * 1e6
    else:
        monthly_requests = primary * 1e5

    base_infra = 45.0
    per_million = 0.35
    compute_units = max(1.0, monthly_requests / 1e6) * per_million
    storage_guess = min(500.0, 10.0 + primary * 0.02)
    storage_cost = storage_guess * 0.02
    az_factor = 1.45 if mult_az else 1.0

    subtotal = (base_infra + compute_units + storage_cost) * az_factor

    lines = [
        "**월간 유지비 추정 (USD, 참고용)**",
        f"- 리전(참고): `{region}`",
        f"- 가용성: `{availability}`",
        f"- 트래픽 입력: `{traffic}`",
        "",
        f"- 추정 월 비용(온디맨드·공개 카탈로그 수준 가정): **약 ${subtotal:,.2f} USD**",
        f"  - 베이스(관측/운영 레이어 목): ${base_infra * az_factor:,.2f}",
        f"  - 처리량 가중(개략): ${compute_units * az_factor:,.2f}",
        f"  - 스토리지 가정({storage_guess:.1f} GB 목): ${storage_cost * az_factor:,.2f}",
        "",
        "_예약 인스턴스·Savings Plans·엔터프라이즈 할인은 포함하지 않습니다._",
        "_실제 비용은 워크로드·SKU·네트워크에 따라 달라질 수 있습니다._",
    ]
    return "\n".join(lines)


@tool
def generate_terraform_draft(confirmed_specification: str) -> str:
    """확정된 사양 문자열을 받아 Terraform `.tf` 초안 텍스트를 반환한다(apply 없음, 다운로드 강제 없음)."""
    spec = (confirmed_specification or "").strip() or "기본 웹 애플리케이션 (리전·VM 크기 미지정)"
    safe = re.sub(r"[^a-zA-Z0-9가-힣_\-\s.,:/]", "", spec)[:500]
    return f"""# Terraform 초안 (참고용, terraform apply 미실행)
# 사양 요약: {safe}

terraform {{
  required_version = ">= 1.5"
}}

# 아래는 배포 자동화가 아닌 설계 대화용 스켈레톤입니다.
# 실제 provider·이름·SKU는 조직 표준에 맞게 조정하세요.

# resource "azurerm_resource_group" "app" {{
#   name     = "rg-multicloud-demo"
#   location = "koreacentral"
# }}

# resource "azurerm_virtual_network" "main" {{
#   name                = "vnet-app"
#   resource_group_name = azurerm_resource_group.app.name
#   location            = azurerm_resource_group.app.location
#   address_space       = ["10.0.0.0/16"]
# }}

# resource "azurerm_subnet" "app" {{
#   name                 = "subnet-app"
#   resource_group_name  = azurerm_resource_group.app.name
#   virtual_network_name = azurerm_virtual_network.main.name
#   address_prefixes     = ["10.0.1.0/24"]
# }}

# --- 네트워크·컴퓨트·스토리지는 확정 SKU와 피어링/방화벽 정책에 맞게 채움 ---

output "design_note" {{
  value = "이 초안은 대화에서 확정된 사양을 바탕으로 한 텍스트 초안입니다. 프로비저닝은 수행하지 않습니다."
}}
"""


MULTICLOUD_TOOLS = [
    lookup_cloud_price,
    estimate_monthly_cost,
    generate_terraform_draft,
]
