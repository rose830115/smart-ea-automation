"""Zone sheet 名稱解析（SSOT）。

業務回傳的環境資料 Excel，分頁名稱不一定跟標準名完全相符：
- 大小寫、前後 / 中間多餘空白會不同。
- 常在後面加廠區 / 製程後綴，例如 `Raw Material warehouse-CKL1`、
  `Production Line-CKL1 (CuttingSt`（Excel 分頁名 31 字元上限還會截斷）。
- 同一個 zone 可能被拆成多個分頁（例如產線 CKL1 / CKL2 各一頁）。

所以比對規則放寬成「正規化後的前綴比對」：分頁名正規化後只要以某個
zone 標準名開頭（且前綴後是分隔字元或結尾），就歸給那個 zone；同一個
zone 允許對到多個分頁。zone 標準名彼此不互為前綴、也跟 Outside /
Instructions / item list 這些分頁不重疊，所以不會誤判。

validation.py / smart_ea_automation.py / app.py 都吃這一份，改規則只改這裡。
"""

from __future__ import annotations

import re

# (標準分頁名, zone code)。順序不影響比對（三個標準名互不為前綴）。
ZONE_SHEET_DEFS: tuple[tuple[str, str], ...] = (
    ("Raw Material warehouse", "RMW"),
    ("Production Line", "PL"),
    ("Finished Goods Warehouse", "FGW"),
)

OUTSIDE_SHEET = "Outside"


def normalize_sheet_name(name) -> str:
    """大小寫不敏感 + 前後與中間多餘空白壓成單一空白。"""
    if name is None:
        return ""
    return re.sub(r"\s+", " ", str(name)).strip().casefold()


def _matches_prefix(norm_name: str, prefix_canonical: str) -> bool:
    """norm_name 是否以 prefix（標準名正規化）開頭，且前綴後為結尾或非英數字。

    前綴後要求「非英數字」是為了避免 `production lineX` 這種黏字誤判，
    但允許 `-`、空白、`(` 這類真實後綴分隔符。
    """
    prefix = normalize_sheet_name(prefix_canonical)
    if not prefix:
        return False
    if norm_name == prefix:
        return True
    if norm_name.startswith(prefix):
        return not norm_name[len(prefix)].isalnum()
    return False


def zone_for_sheet(sheet_name) -> str | None:
    """回傳這個分頁屬於哪個 zone code；不屬於任何 zone 回 None。"""
    norm = normalize_sheet_name(sheet_name)
    for canonical, zone in ZONE_SHEET_DEFS:
        if _matches_prefix(norm, canonical):
            return zone
    return None


def resolve_zone_sheets(sheetnames) -> list[tuple[str, str]]:
    """回傳 [(實際分頁名, zone code), ...]，保持原順序，允許同 zone 多頁。"""
    resolved: list[tuple[str, str]] = []
    for name in sheetnames:
        zone = zone_for_sheet(name)
        if zone is not None:
            resolved.append((name, zone))
    return resolved


def outside_sheets(sheetnames) -> list[str]:
    """回傳所有室外分頁的實際名稱（同樣容忍後綴，例如 `Outside-CKL1`）。"""
    return [
        name
        for name in sheetnames
        if _matches_prefix(normalize_sheet_name(name), OUTSIDE_SHEET)
    ]


def missing_zones(sheetnames) -> list[str]:
    """回傳缺少的 zone 標準名清單（三個 zone 至少各要有一個分頁）。"""
    found = {zone for _, zone in resolve_zone_sheets(sheetnames)}
    return [canonical for canonical, zone in ZONE_SHEET_DEFS if zone not in found]


def is_vendor_workbook(sheetnames) -> bool:
    """三個 zone 都至少有一個分頁 → 視為業務回傳環境資料檔。"""
    return not missing_zones(sheetnames)
