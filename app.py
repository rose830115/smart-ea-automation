from __future__ import annotations

import json
import re
import os
import subprocess
import sys
import time
import warnings
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from openpyxl import load_workbook

from smart_ea_automation import run_automation, run_from_standardized
from validation import validate_inputs


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_ROOT = PROJECT_DIR / "web_outputs"
UPLOAD_ROOT = PROJECT_DIR / "uploads"

IS_CLOUD = str(PROJECT_DIR).startswith("/mount/src")

VENDOR_SHEETS = {"Raw Material warehouse", "Production Line", "Finished Goods Warehouse"}
TARGET_HINT_SHEETS = {"Areas", "Env. Data", "Moisture", "CFU"}

warnings.filterwarnings("ignore", message="Data Validation extension is not supported")


def arrow_safe(data: Any) -> pd.DataFrame:
    """把要用 st.dataframe 顯示的資料統一轉成純文字 DataFrame。

    像 checking_point 這種欄位常有 '16B' 與數字混在一起，Streamlit 顯示時
    要序列化成 Arrow，pyarrow 會先猜成 int64 再遇到 '16B' 直接失敗；在較新的
    Python（雲端 3.14）上這個失敗會惡化成整個行程 segmentation fault。
    先全部轉成字串，Arrow 就只會看到單一字串型別，永遠不會踩到這個雷。
    """
    df = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
    # astype(str) 統一型別（pandas 3.0 會保留空值為 NaN，較舊版本會變字串 "nan"）；
    # replace + fillna 兩種情況都清成空字串，顯示才乾淨。
    return df.astype(str).replace({"nan": "", "None": "", "NaT": "", "<NA>": ""}).fillna("")


def sanitize_case_name(value: str) -> str:
    value = value.strip() or "Smart_EA_case"
    value = re.sub(r"[^\w.-]+", "_", value, flags=re.UNICODE)
    value = value.strip("._")
    return value or "Smart_EA_case"


def workbook_sheets(path: Path) -> set[str]:
    try:
        wb = load_workbook(path, read_only=True, data_only=False)
        return set(wb.sheetnames)
    except Exception:
        return set()


def excel_files_in(case_dir: Path) -> list[Path]:
    if not case_dir.exists() or not case_dir.is_dir():
        return []
    return sorted(
        [
            path
            for path in case_dir.glob("*.xlsx")
            if path.is_file() and not path.name.startswith("~$") and not path.name.startswith(".")
        ],
        key=lambda p: p.name.casefold(),
    )


def detect_workbooks(case_dir: Path) -> tuple[list[Path], list[Path]]:
    vendor_candidates: list[Path] = []
    target_candidates: list[Path] = []

    for path in excel_files_in(case_dir):
        sheets = workbook_sheets(path)
        if VENDOR_SHEETS.issubset(sheets):
            vendor_candidates.append(path)
        if TARGET_HINT_SHEETS.issubset(sheets) or {"Areas", "ITEMLIST"}.issubset(sheets):
            target_candidates.append(path)

    return vendor_candidates, target_candidates


def choose_default(options: list[Path], preferred_words: tuple[str, ...] = ()) -> int:
    if not options:
        return 0
    for idx, path in enumerate(options):
        name = path.name.casefold()
        if any(word.casefold() in name for word in preferred_words):
            return idx
    return 0


def path_label(path: Path) -> str:
    return str(path)


def save_uploaded_file(uploaded_file: Any, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / uploaded_file.name
    target_path.write_bytes(uploaded_file.getbuffer())
    return target_path


def show_download(path: Path, label: str) -> None:
    if not path or not path.exists():
        return
    st.download_button(
        label=label,
        data=path.read_bytes(),
        file_name=path.name,
        mime="application/octet-stream",
        use_container_width=True,
    )


def run_case(case_name: str, vendor_path: Path, target_path: Path | None, outdir: Path) -> dict[str, Any]:
    return run_automation(
        vendor_path=vendor_path,
        target_path=target_path,
        outdir=outdir,
        case_name=case_name,
    )


def yims_login_ready(account: str = "", password: str = "") -> bool:
    if st.session_state.get("yims_browser_token"):
        return True
    if "YIMS_ACCOUNT" in st.secrets and "YIMS_PASSWORD" in st.secrets:
        return True
    return bool(account.strip() and password)


@st.cache_resource(show_spinner=False)
def install_chromium() -> None:
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        capture_output=True,
    )


def playwright_yims_login(account: str, password: str) -> tuple[str | None, list, str | None]:
    from yims_playwright_login import login_with_debug
    return login_with_debug(account, password)


def check_password() -> bool:
    if st.session_state.get("authenticated"):
        return True
    st.title("MRC Smart EA 小工具")
    pwd = st.text_input("請輸入工具密碼", type="password", key="password_input")
    if pwd:
        if pwd == st.secrets.get("app_password", ""):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("密碼錯誤")
    return False


def render_main_area_matching(yims_result: dict[str, Any]) -> None:
    """顯示工具倉間與後台倉間的配對結果。

    倉間可以拆成 PL1 / PL2，同仁又會在後台把名稱改成客戶要的寫法，工具送的名稱
    就對不上後台。對不上時系統改用順序配對——照片與可視性風險不會消失，而是留在
    順序相同的另一個倉間，比清空更難發現，所以一定要攤開給人確認。
    """
    try:
        payload = json.loads(yims_result.get("stdout") or "{}")
    except json.JSONDecodeError:
        return
    rows = payload.get("main_area_matching") or []
    warnings = payload.get("main_area_warnings") or []
    if not rows:
        return
    if warnings:
        for message in warnings:
            (st.warning if message.startswith("⚠️") else st.info)(message)
    with st.expander(f"倉間對應（{len(rows)} 個）", expanded=bool(warnings)):
        st.dataframe(
            arrow_safe(pd.DataFrame([
                {
                    "順序": row["position"],
                    "工具的倉間": row["tool_name"],
                    "後台的倉間": row["backend_name"] or "（新增）",
                    "怎麼對上的": {"name": "名稱相同", "position": "靠順序", "new": "後台沒有，新增"}
                    .get(row["matched_by"], row["matched_by"]),
                }
                for row in rows
            ])),
            use_container_width=True,
            hide_index=True,
        )


def run_yims_bot(
    order_id: str,
    paths: dict[str, Path],
    outdir: Path,
    save: bool,
    account: str = "",
    password: str = "",
) -> dict[str, Any]:
    logs_dir = outdir / "99_logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = logs_dir / f"yims_{order_id}_{'saved' if save else 'preview'}.png"
    cmd = [
        sys.executable,
        str(PROJECT_DIR / "yims_api_client.py"),
        "--payload",
        str(paths["backend_payload"]),
        "--order-id",
        order_id,
        "--outdir",
        str(outdir),
    ]
    if save:
        cmd.append("--save")

    env = os.environ.copy()
    if st.session_state.get("yims_browser_token"):
        env["YIMS_TOKEN"] = st.session_state["yims_browser_token"]
    elif "YIMS_ACCOUNT" in st.secrets:
        env["YIMS_ACCOUNT"] = str(st.secrets["YIMS_ACCOUNT"])
        if "YIMS_PASSWORD" in st.secrets:
            env["YIMS_PASSWORD"] = str(st.secrets["YIMS_PASSWORD"])
    elif account.strip() and password:
        env["YIMS_ACCOUNT"] = account.strip()
        env["YIMS_PASSWORD"] = password

    started = time.strftime("%Y-%m-%d %H:%M:%S")
    completed = subprocess.run(
        cmd,
        cwd=str(PROJECT_DIR),
        env=env,
        text=True,
        capture_output=True,
        timeout=240,
    )
    return {
        "command": " ".join(cmd),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "screenshot": screenshot_path,
        "started": started,
        "save": save,
    }


st.set_page_config(page_title="MRC Smart EA Tool", layout="wide")

if not check_password():
    st.stop()

install_chromium()

st.title("MRC Smart EA 小工具")
st.caption("案件資料整理、後台輸入資料包與後台填表")

with st.sidebar:
    st.header("案件設定")
    case_name_input = st.text_input("案件名稱", value="SEA_test")
    case_name = sanitize_case_name(case_name_input)
    yims_order_id = st.text_input("後台案件代號", value="", help="用於填入後台資料。")

    st.divider()
    st.header("後台登入")
    if st.session_state.get("yims_browser_token"):
        st.success("後台已登入")
        if st.button("登出後台", use_container_width=True):
            st.session_state.pop("yims_browser_token", None)
            st.rerun()
        yims_account = ""
        yims_password = ""
    else:
        yims_account = st.text_input("後台帳號")
        yims_password = st.text_input("後台密碼", type="password")
        if st.button("登入後台", use_container_width=True, disabled=not (yims_account and yims_password)):
            with st.spinner("正在登入後台，請稍候..."):
                token, screenshots, error = playwright_yims_login(yims_account, yims_password)
            if token:
                st.session_state["yims_browser_token"] = token
                st.rerun()
            else:
                st.error(f"後台登入失敗：{error}")
                import base64
                for i, shot_b64 in enumerate(screenshots):
                    st.image(base64.b64decode(shot_b64), caption=f"截圖 {i+1}")

source_ready = False
vendor_path: Path | None = None
target_path: Path | None = None
adjusted_path: Path | None = None
outdir: Path | None = None

MODE_FRESH = "① 從業務 Excel 整理"
MODE_ADJUSTED = "② 用調整後的標準化 Excel 直接建後台資料"
input_mode = st.radio(
    "資料來源",
    [MODE_FRESH, MODE_ADJUSTED],
    horizontal=True,
    help="② 用在：資料統整後你們又手動改了分類，把調整好的標準化 Excel 丟回來，"
    "工具直接用它重建後台資料包，不用一格一格手動輸入後台。",
)

upload_dir = UPLOAD_ROOT / f"{case_name}_{int(time.time())}"
outdir = DEFAULT_OUTPUT_ROOT / case_name

if input_mode == MODE_FRESH:
    col1, col2 = st.columns(2)
    with col1:
        vendor_upload = st.file_uploader("上傳業務回傳環境資料 Excel", type=["xlsx"])
    with col2:
        target_upload = st.file_uploader("上傳人工標準化 / 公式範本 Excel", type=["xlsx"])
    if vendor_upload is not None:
        vendor_path = save_uploaded_file(vendor_upload, upload_dir)
    if target_upload is not None:
        target_path = save_uploaded_file(target_upload, upload_dir)
    source_ready = vendor_path is not None
else:
    adjusted_upload = st.file_uploader(
        "上傳調整後的標準化 Excel（工具先前產出的 SEA_xxx_standardized_from_vendor.xlsx）",
        type=["xlsx"],
    )
    if adjusted_upload is not None:
        adjusted_path = save_uploaded_file(adjusted_upload, upload_dir)
    source_ready = adjusted_path is not None

st.divider()

if input_mode == MODE_FRESH and source_ready and vendor_path and outdir:
    st.subheader("準備執行")
    st.write(f"案件名稱：`{case_name}`")
    st.write(f"輸出位置：`{outdir}`")
    st.caption("這一步只整理資料與產生檔案;後台輸入會在處理完成後,於下方的後台區塊另外執行。")

    violations = validate_inputs(vendor_path, target_path)
    if violations:
        st.error(
            "上傳的檔案未通過事前檢查,請修正下列項目後重新上傳:\n\n"
            + "\n".join(f"- {v}" for v in violations)
        )
        st.caption(
            "規範參考：`200_Reference/templates/smart-ea_業務交檔規格.md` 與 "
            "`smart-ea_公式範本填表規格.md`"
        )
    else:
        st.success("事前檢查通過,可以開始跑流水線。")

    run_button = st.button(
        "開始處理案件",
        type="primary",
        use_container_width=True,
        disabled=bool(violations),
    )
    if run_button:
        try:
            with st.spinner("處理中，正在整理 Excel 與輸出檔案..."):
                result = run_case(case_name, vendor_path, target_path, outdir)
            st.session_state["last_result"] = result
            st.session_state["last_cfu_data"] = result.get("cfu_data", [])
            st.success("處理完成")
        except Exception as exc:
            st.error("處理失敗，請確認 Excel 格式與資料夾路徑。")
            st.exception(exc)

elif input_mode == MODE_ADJUSTED and source_ready and adjusted_path:
    # 從檔名自動偵測案件名稱（SEA_xxx_standardized_from_vendor.xlsx → SEA_xxx），
    # 讓輸出資料夾與菌種來源對得上，不用逼使用者去側欄改案件名稱。
    STD_SUFFIX = "_standardized_from_vendor.xlsx"
    if adjusted_path.name.endswith(STD_SUFFIX):
        case_name_eff = sanitize_case_name(adjusted_path.name[: -len(STD_SUFFIX)])
    else:
        case_name_eff = case_name
    outdir_eff = DEFAULT_OUTPUT_ROOT / case_name_eff

    st.subheader("準備執行（調整後 Excel → 後台資料）")
    st.write(f"偵測案件名稱：`{case_name_eff}`")
    st.write(f"輸出位置：`{outdir_eff}`")
    st.caption("菌種直接讀這份標準化 Excel 的「Isolate Mold Species」欄，不依賴其他檔案；隔天或換電腦重傳也讀得到。")

    run_button_adj = st.button(
        "用這份 Excel 建立後台資料", type="primary", use_container_width=True
    )
    if run_button_adj:
        try:
            with st.spinner("讀取調整後 Excel、依你改過的分類重建後台資料包..."):
                result = run_from_standardized(adjusted_path, outdir_eff, case_name_eff)
            st.session_state["last_result"] = result
            st.session_state["last_cfu_data"] = result.get("cfu_data", [])
            species_source = result.get("species_source")
            species_matched = result.get("species_matched", 0)
            if species_source == "excel_column":
                species_note = f"菌種讀自 Excel 菌種欄，共 {species_matched} 筆。"
            elif species_source == "payload_fallback":
                species_note = f"這份 Excel 沒有菌種欄（舊版），退回從第一次結果帶回 {species_matched} 筆。"
            else:
                species_note = "注意：這份 Excel 沒有菌種資料，微生物菌種會留空。"
            st.success(f"完成。{species_note}可到下方「後台輸入」檢查 / 儲存。")
        except Exception as exc:
            st.error("處理失敗，請確認這是工具先前產出的標準化 Excel（分頁與欄位需維持原樣）。")
            st.exception(exc)

else:
    if input_mode == MODE_ADJUSTED:
        st.info("請上傳調整後的標準化 Excel（工具先前產出的 SEA_xxx_standardized_from_vendor.xlsx）。")
    else:
        st.info("請先提供業務回傳環境資料 Excel。")

result = st.session_state.get("last_result")
if result:
    paths = result["paths"]
    summary = result["backend_summary"]
    quality_issues = result["quality_issues"]

    st.divider()
    st.subheader("輸出結果")
    metric_cols = st.columns(5)
    metric_cols[0].metric("Env. Data", summary.get("env_rows", 0))
    metric_cols[1].metric("Moisture", summary.get("moisture_rows", 0))
    metric_cols[2].metric("Microbiology", summary.get("microbiology_rows", 0))
    metric_cols[3].metric("室內區域", summary.get("indoor_area_count", 0))
    metric_cols[4].metric("資料問題", summary.get("quality_issue_count", 0))

    if quality_issues:
        st.warning("有資料問題需要人工確認。")
        st.dataframe(arrow_safe(quality_issues), use_container_width=True)

    download_cols = st.columns(2)
    with download_cols[0]:
        show_download(paths["standardized_workbook"], "下載整理後 Excel")
    with download_cols[1]:
        show_download(paths["validation_report"], "下載比對報告")

    st.subheader("後台輸入")
    st.info("下方按鈕改用後台 API，不開瀏覽器。檢查只驗證登入、案件、資料包與送出格式；勾選確認後才會寫入後台。")

    if not yims_order_id.strip():
        st.warning("請先在左側輸入後台案件代號，才能執行後台填表。")
    else:
        login_ready = yims_login_ready(yims_account, yims_password)
        if not login_ready:
            st.warning("請在左側輸入後台帳號與密碼。")
        yims_cols = st.columns(2)
        with yims_cols[0]:
            if st.button("檢查後台（不儲存）", use_container_width=True):
                with st.spinner("正在檢查後台、案件資料與送出格式..."):
                    try:
                        yims_result = run_yims_bot(
                            yims_order_id.strip(),
                            paths,
                            result["outdir"],
                            save=False,
                            account=yims_account,
                            password=yims_password,
                        )
                        st.session_state["last_yims_result"] = yims_result
                    except subprocess.TimeoutExpired:
                        st.error("後台填表逾時。請確認網路與案件代號。")
        with yims_cols[1]:
            confirm_save = st.checkbox("我確認要儲存到後台")
            if st.button("快速儲存到後台", type="primary", use_container_width=True, disabled=not confirm_save):
                with st.spinner("正在透過後台 API 儲存..."):
                    try:
                        yims_result = run_yims_bot(
                            yims_order_id.strip(),
                            paths,
                            result["outdir"],
                            save=True,
                            account=yims_account,
                            password=yims_password,
                        )
                        st.session_state["last_yims_result"] = yims_result
                    except subprocess.TimeoutExpired:
                        st.error("後台儲存逾時。請到後台確認是否已儲存。")

    yims_result = st.session_state.get("last_yims_result")
    if yims_result:
        if yims_result["returncode"] == 0:
            st.success("後台動作完成。")
            if yims_result["save"]:
                st.write("這次已透過後台 API 儲存。")
            else:
                st.write("這次只有檢查後台與資料包，沒有儲存到後台。")
            render_main_area_matching(yims_result)
        else:
            st.error("後台動作失敗。")
            st.code(yims_result["stderr"] or yims_result["stdout"], language="text")
            st.warning("若錯誤內容提到尚未登入，請先在工具主機終端機手動登入一次後台，或設定 YIMS_ACCOUNT / YIMS_PASSWORD。")
