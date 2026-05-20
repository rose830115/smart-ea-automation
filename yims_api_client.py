from __future__ import annotations

import argparse
import copy
import json
import os
import statistics
import sys
import urllib.parse
from pathlib import Path
from typing import Any

import requests
try:
    import cloudscraper
    _HAS_CLOUDSCRAPER = True
except ImportError:
    _HAS_CLOUDSCRAPER = False

from yims_payload_builder import build_yims_extends_data, load_comments


BASE_URL = "https://mrc.ycmproducts.com"
AUTH_STATE = Path(__file__).resolve().parent / ".yims_auth_state.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def numeric_values(values: list[Any]) -> list[float]:
    result: list[float] = []
    for value in values or []:
        if value is None or value == "":
            continue
        try:
            result.append(float(value))
        except (TypeError, ValueError):
            continue
    return result


def rounded_mean(values: list[Any], digits: int = 1) -> float:
    numbers = numeric_values(values)
    if not numbers:
        return 0
    return round(statistics.mean(numbers), digits)


def normalize_number(value: float) -> int | float:
    return int(value) if float(value).is_integer() else value


ZONE_NAME_TO_CODE = {
    "raw material warehouse": "RMW",
    "production line": "PL",
    "finished goods warehouse": "FGW",
}


def parse_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _extract_chart_rows(chart_obj: Any) -> list:
    """Extract row list from a YIMS chart object, trying common nesting paths."""
    if not isinstance(chart_obj, dict):
        return []
    # Try chart_item.en (some chart types use this wrapper)
    chart_item = chart_obj.get("chart_item")
    if isinstance(chart_item, dict):
        rows = chart_item.get("en") or chart_item.get("zh") or []
        if isinstance(rows, list) and rows:
            return rows
    # Fall back to direct en / zh key
    rows = chart_obj.get("en") or chart_obj.get("zh") or []
    return rows if isinstance(rows, list) else []


def chart_rows_to_zone_risk(rows: list[Any]) -> dict[str, float | None]:
    risks: dict[str, float | None] = {"RMW": None, "PL": None, "FGW": None}
    for row in rows[1:]:
        if not isinstance(row, list) or len(row) < 2:
            continue
        zone_code = ZONE_NAME_TO_CODE.get(str(row[0]).strip().lower())
        if zone_code:
            risks[zone_code] = parse_float(row[1])
    return risks


def recompute_top_level_calculated_fields(extends_data: dict[str, Any]) -> None:
    particulate_matter_average = rounded_mean(extends_data.get("particulate_matter_10s", []), 1)
    object_failure_rates = [
        item.get("object_moisture_content_failure_rate")
        for item in extends_data.get("object_moisture_content_array", [])
        if isinstance(item, dict)
    ]
    microbiology_averages = [
        item.get("microbiology_sampling_object_sampling_cfu_average")
        for item in extends_data.get("microbiology_sampling_object_array", [])
        if isinstance(item, dict)
    ]

    extends_data["temperature_average"] = normalize_number(rounded_mean(extends_data.get("temperatures", []), 1))
    extends_data["relative_humidity_average"] = normalize_number(rounded_mean(extends_data.get("relative_humidities", []), 1))
    extends_data["carbon_dioxide_average"] = normalize_number(rounded_mean(extends_data.get("carbon_dioxides", []), 1))
    extends_data["spore_blow_index_average"] = normalize_number(rounded_mean(extends_data.get("spore_blow_indexes", []), 2))
    extends_data["particulate_matter_10_average"] = normalize_number(particulate_matter_average)
    extends_data["air_pollution_level"] = round(particulate_matter_average * 210)
    extends_data["space_lumen_index_average"] = round(rounded_mean(extends_data.get("space_lumen_indexes", []), 0))
    extends_data["object_moisture_content_total_failure_rate"] = normalize_number(rounded_mean(object_failure_rates, 1))
    extends_data["microbiology_sampling_object_total_sampling_cfu_average"] = normalize_number(
        rounded_mean(microbiology_averages, 1)
    )


def normalize_extends_data_for_save(extends_data: dict[str, Any]) -> None:
    recompute_top_level_calculated_fields(extends_data)


def iter_form_fields(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    fields: list[tuple[str, str]] = []
    if prefix == "filesFormdata":
        return fields
    if value is None:
        return [(prefix, "")]
    if isinstance(value, (str, int, float)):
        return [(prefix, str(value))]
    if isinstance(value, list):
        for idx, item in enumerate(value):
            fields.extend(iter_form_fields(item, f"{prefix}[{idx}]"))
        return fields
    if isinstance(value, dict):
        for key, item in value.items():
            field_name = f"{prefix}[{key}]" if prefix else str(key)
            fields.extend(iter_form_fields(item, field_name))
        return fields
    return fields


class YimsApiClient:
    def __init__(self, base_url: str = BASE_URL, auth_state: Path = AUTH_STATE) -> None:
        self.base_url = base_url.rstrip("/")
        self.auth_state = auth_state
        self.session = cloudscraper.create_scraper() if _HAS_CLOUDSCRAPER else requests.Session()
        self.token: str | None = None
        self.user: dict[str, Any] | None = None
        self.session.headers.update(
            {
                "Accept": "application/json, text/plain, */*",
                "X-Requested-With": "XMLHttpRequest",
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.7727.15 Safari/537.36"
                ),
            }
        )

    def load_auth_state(self) -> None:
        if not self.auth_state.exists():
            return
        state = load_json(self.auth_state)
        for cookie in state.get("cookies", []):
            self.session.cookies.set(
                cookie["name"],
                cookie["value"],
                domain=cookie.get("domain"),
                path=cookie.get("path", "/"),
            )
        for origin in state.get("origins", []):
            if origin.get("origin") != self.base_url:
                continue
            local_storage = {item["name"]: item["value"] for item in origin.get("localStorage", [])}
            self.token = local_storage.get("lab_admins_token") or self.token
            if local_storage.get("lab_admins"):
                try:
                    self.user = json.loads(local_storage["lab_admins"])
                except json.JSONDecodeError:
                    self.user = None
        self.apply_auth_headers(referer=f"{self.base_url}/admin/lab_admins/me")

    def write_auth_state(self) -> None:
        cookies = []
        for cookie in self.session.cookies:
            cookies.append(
                {
                    "name": cookie.name,
                    "value": cookie.value,
                    "domain": cookie.domain,
                    "path": cookie.path,
                    "expires": -1,
                    "httpOnly": "session" in cookie.name,
                    "secure": True,
                    "sameSite": "Lax",
                }
            )
        local_storage = []
        if self.user is not None:
            local_storage.append({"name": "lab_admins", "value": json.dumps(self.user, ensure_ascii=False)})
        if self.token:
            local_storage.append({"name": "lab_admins_token", "value": self.token})
        self.auth_state.write_text(
            json.dumps(
                {
                    "cookies": cookies,
                    "origins": [{"origin": self.base_url, "localStorage": local_storage}],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def apply_auth_headers(self, referer: str | None = None) -> None:
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"
        xsrf = self.session.cookies.get("XSRF-TOKEN")
        if xsrf:
            self.session.headers["X-XSRF-TOKEN"] = urllib.parse.unquote(xsrf)
        if referer:
            self.session.headers["Referer"] = referer

    def request_json(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        self.apply_auth_headers(kwargs.pop("referer", None))
        response = self.session.request(method, f"{self.base_url}{path}", timeout=30, **kwargs)
        if not response.ok:
            body_preview = (response.text or "")[:500].replace("\n", " ")
            raise requests.HTTPError(
                f"{response.status_code} {response.reason} for {method} {path} | body: {body_preview}",
                response=response,
            )
        return response.json()

    def login(self, account: str, password: str) -> None:
        self.session.get(f"{self.base_url}/login", timeout=30)
        self.apply_auth_headers(referer=f"{self.base_url}/login")
        response = self.session.post(
            f"{self.base_url}/api/lab_admins/login",
            json={"account": account, "password": password, "login_platform": "mrc"},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        self.token = payload["data"]["token"]
        self.user = payload["data"].get("user")
        self.apply_auth_headers(referer=f"{self.base_url}/admin/lab_admins/me")
        self.write_auth_state()

    def ensure_authenticated(self, account: str = "", password: str = "") -> None:
        # Accept pre-obtained token from browser-side login
        env_token = os.getenv("YIMS_TOKEN")
        if env_token:
            self.token = env_token
            self.apply_auth_headers()
            try:
                self.request_json("POST", "/api/lab_admins/is_login")
                return
            except requests.RequestException:
                pass

        self.load_auth_state()
        if self.token:
            try:
                self.request_json("POST", "/api/lab_admins/is_login")
                return
            except requests.RequestException:
                pass
        if not account or not password:
            raise RuntimeError("YIMS API 尚未登入，請在網頁側欄輸入 YIMS 帳號與密碼。")
        self.login(account, password)

    def get_service_id(self, order_id: str) -> int:
        payload = self.request_json(
            "GET",
            f"/api/orders/customer_applications/one?orders_id={order_id}",
            referer=f"{self.base_url}/admin/orders/detail/{order_id}",
        )
        return int(payload["data"]["orders_customer_applications"]["services_id"])

    def get_test_result(self, order_id: str, service_id: int) -> dict[str, Any]:
        payload = self.request_json(
            "GET",
            f"/api/orders/test_result/one?services_id={service_id}&orders_id={order_id}",
            referer=f"{self.base_url}/admin/orders/detail/{order_id}",
        )
        test_result = payload.get("data", {}).get("order_test_results")
        if not test_result:
            raise RuntimeError(f"YIMS 案件 {order_id} 尚未建立 Smart EA test result，無法用 API 直寫。")
        return test_result

    def get_molds(self) -> list[dict[str, Any]]:
        payload = self.request_json(
            "GET",
            "/api/molds/fetch?is_all=1",
            referer=f"{self.base_url}/admin/orders",
        )
        molds = payload.get("data", {}).get("molds", [])
        if isinstance(molds, dict):
            return molds.get("data", [])
        return molds if isinstance(molds, list) else []

    def build_save_payload(self, order_id: str, extends_data: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        service_id = self.get_service_id(order_id)
        test_result = self.get_test_result(order_id, service_id)
        save_payload = copy.deepcopy(test_result)
        save_payload.setdefault("extends_data", {})
        for key, value in extends_data.items():
            save_payload["extends_data"][key] = value
        normalize_extends_data_for_save(save_payload["extends_data"])
        save_payload["service_id"] = service_id
        save_payload["filesFormdata"] = {}
        return service_id, save_payload

    def save_test_result(self, order_id: str, save_payload: dict[str, Any]) -> dict[str, Any]:
        fields = iter_form_fields(save_payload)
        multipart_fields = [(key, (None, value)) for key, value in fields]
        response = self.session.post(
            f"{self.base_url}/api/orders/test_result/save/{order_id}",
            files=multipart_fields,
            timeout=60,
            headers={
                **self.session.headers,
                "Referer": f"{self.base_url}/admin/orders/detail/{order_id}",
            },
        )
        response.raise_for_status()
        return response.json()

    def get_print_data(self, order_id: str, service_id: int) -> list[dict[str, Any]]:
        payload = self.request_json(
            "GET",
            f"/api/orders/print/data?orders_id={order_id}&service_id={service_id}",
            referer=(
                f"{self.base_url}/admin/orders/html-to-pdf/smart_ea"
                f"?orders_id={order_id}&services_id={service_id}&lang=en"
            ),
        )
        data = payload.get("data", [])
        return data if isinstance(data, list) else []

    def get_print_risk_data(self, order_id: str, service_id: int) -> dict[str, Any]:
        print_data = self.get_print_data(order_id, service_id)
        raw_charts: dict[str, Any] = {}
        risk_data: dict[str, Any] = {
            "source": "/api/orders/print/data",
            "order_id": order_id,
            "service_id": service_id,
            "env_risk": {"RMW": None, "PL": None, "FGW": None},
            "micro_risk": {"RMW": None, "PL": None, "FGW": None},
            "overall_risk": {"RMW": None, "PL": None, "FGW": None},
        }

        for item in print_data:
            if not isinstance(item, dict):
                continue
            item_type = item.get("type")
            data = item.get("data") if isinstance(item.get("data"), dict) else {}
            chart_data = data.get("chart_data")

            if item_type == "overall_environmental_risk_analysis_line_chart" and isinstance(chart_data, dict):
                env_chart = chart_data.get("environmental_mold_risk")
                if isinstance(env_chart, dict):
                    rows = _extract_chart_rows(env_chart)
                    risk_data["env_risk"] = chart_rows_to_zone_risk(rows)
                    raw_charts["environmental_mold_risk"] = env_chart

            elif item_type == "overall_microbiological_risk_analysis" and isinstance(chart_data, dict):
                rows = _extract_chart_rows(chart_data)
                risk_data["micro_risk"] = chart_rows_to_zone_risk(rows)
                raw_charts["microbiological_risk"] = chart_data

            elif item_type == "overall_mold_risk_detection_result" and isinstance(chart_data, dict):
                rows = _extract_chart_rows(chart_data)
                risk_data["overall_risk"] = chart_rows_to_zone_risk(rows)
                raw_charts["overall_mold_risk"] = chart_data

        risk_data["raw_charts"] = raw_charts
        risk_data["debug_item_types"] = [
            item.get("type") for item in print_data if isinstance(item, dict)
        ]
        return risk_data


def run_api_fill(args: argparse.Namespace) -> dict[str, Any]:
    backend_payload = load_json(args.payload)
    comments = load_comments(args.metrics) if args.metrics else {}

    client = YimsApiClient(base_url=args.base_url, auth_state=args.auth_state)
    client.ensure_authenticated(
        account=os.getenv("YIMS_ACCOUNT", ""),
        password=os.getenv("YIMS_PASSWORD", ""),
    )
    extends_data = build_yims_extends_data(backend_payload, comments=comments, mold_options=client.get_molds())
    service_id, save_payload = client.build_save_payload(args.order_id, extends_data)

    outdir = args.outdir or args.payload.parent
    outdir.mkdir(parents=True, exist_ok=True)
    preview_path = outdir / f"yims_{args.order_id}_api_payload_preview.json"
    preview_path.write_text(json.dumps(save_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    result = {
        "mode": "api",
        "order_id": args.order_id,
        "service_id": service_id,
        "main_area_count": len(save_payload["extends_data"].get("main_area_array", [])),
        "assessment_area_count": sum(
            len(zone.get("assessment_area_array", []))
            for zone in save_payload["extends_data"].get("main_area_array", [])
            if isinstance(zone, dict)
        ),
        "preview_payload": str(preview_path),
        "saved": False,
    }

    if args.save:
        response_payload = client.save_test_result(args.order_id, save_payload)
        response_path = outdir / f"yims_{args.order_id}_api_save_response.json"
        response_path.write_text(json.dumps(response_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        verify_payload = client.get_test_result(args.order_id, service_id)
        verify_path = outdir / f"yims_{args.order_id}_api_verify.json"
        verify_path.write_text(json.dumps(verify_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        # 風險資料抓取是儲存後的下游動作; 後台前端若被弄壞會回 500,
        # 但儲存本身已完成, 不該讓整個流程 crash
        risk_path = outdir / f"yims_{args.order_id}_risk_data.json"
        risk_error: str | None = None
        try:
            risk_data = client.get_print_risk_data(args.order_id, service_id)
            risk_path.write_text(json.dumps(risk_data, ensure_ascii=False, indent=2), encoding="utf-8")
        except requests.HTTPError as exc:
            risk_error = f"{exc}"
            risk_path.write_text(
                json.dumps(
                    {"error": risk_error, "order_id": args.order_id, "service_id": service_id},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        result.update(
            {
                "saved": True,
                "response": str(response_path),
                "verify": str(verify_path),
                "risk_data": str(risk_path),
                "risk_data_error": risk_error,
                "verified_main_area_count": len(verify_payload.get("extends_data", {}).get("main_area_array", [])),
            }
        )

    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fill YIMS Smart EA data through internal API")
    parser.add_argument("--payload", required=True, type=Path, help="*_backend_input_payload.json")
    parser.add_argument("--metrics", type=Path, help="*_environment_metrics.json")
    parser.add_argument("--order-id", required=True, help="YIMS order id / 案件代號")
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--auth-state", default=AUTH_STATE, type=Path)
    parser.add_argument("--outdir", type=Path)
    parser.add_argument("--save", action="store_true", help="Actually write data to YIMS. Default is dry-run only.")
    return parser


def main() -> None:
    result = run_api_fill(build_parser().parse_args())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
