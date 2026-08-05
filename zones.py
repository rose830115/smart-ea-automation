"""倉間代碼解析（SSOT）。

一份案件預設三個倉間 RMW / PL / FGW，但兩種情況會拆更多：

1. 一個倉間的 area 超過 8 個，報告版面太擁擠 → 把 area 平均分成兩個倉間。
2. 案件有兩條不同產品的產線，分開分析比較有意義（不見得超過 8 個 area）。

拆出來的倉間在 `Areas` 分頁的 zone 欄用「基底代碼 + 編號」表示：`PL1`、`PL2`。
編號只是工具用來辨識與排序的，**後台顯示名稱由同仁自行修改**（例如改成
`PBB's Production Line`），工具不覆寫（見 yims_payload_builder 的人工欄位保護）。

為什麼不讓 zone 欄直接填自由名稱：zone 欄打錯字時，全放行會靜默多生一個倉間，
資料被分到沒人發現的地方；限定格式才擋得住。

改倉間規則只改這一份：validation / smart_ea_automation / comment_data /
comment_audit 都吃這裡。
"""

from __future__ import annotations

import re

# 基底倉間：(代碼, 英文全名, 排序序位)。順序＝報告與後台的倉間順序。
BASE_ZONES: tuple[tuple[str, str, int], ...] = (
    ("RMW", "Raw Material Warehouse", 1),
    ("PL", "Production Line", 2),
    ("FGW", "Finished Goods Warehouse", 3),
    ("OUTSIDE", "Outside", 4),
)

BASE_LABELS: dict[str, str] = {code: label for code, label, _ in BASE_ZONES}
BASE_ORDER: dict[str, int] = {code: order for code, _, order in BASE_ZONES}

# 室內倉間才能拆（Outside 不是報告倉間，不給編號）
SPLITTABLE = ("RMW", "PL", "FGW")

ZONE_PATTERN = re.compile(r"^(RMW|PL|FGW)(\d*)$", re.IGNORECASE)


def parse_zone(value) -> tuple[str, int] | None:
    """`PL2` → `("PL", 2)`；`PL` → `("PL", 0)`；不合格式回 None。

    OUTSIDE 不走這裡（不可拆），由 `is_valid_zone` 另外放行。
    """
    if value is None:
        return None
    match = ZONE_PATTERN.fullmatch(str(value).strip())
    if match is None:
        return None
    base = match.group(1).upper()
    suffix = match.group(2)
    return base, int(suffix) if suffix else 0


def normalize_zone(value) -> str | None:
    """把使用者填的值正規化成標準代碼（`pl1` → `PL1`）；不合格式回 None。"""
    text = "" if value is None else str(value).strip()
    if text.upper() == "OUTSIDE":
        return "OUTSIDE"
    parsed = parse_zone(text)
    if parsed is None:
        return None
    base, index = parsed
    return f"{base}{index}" if index else base


def is_valid_zone(value) -> bool:
    return normalize_zone(value) is not None


def zone_label(value) -> str:
    """倉間的英文全名。`PL1` → `Production Line 1`。

    無法解析時原樣回傳：後台可能有工具沒見過的倉間，這裡不該把它變成空字串。
    """
    normalized = normalize_zone(value)
    if normalized is None:
        return "" if value is None else str(value).strip()
    if normalized == "OUTSIDE":
        return BASE_LABELS["OUTSIDE"]
    base, index = parse_zone(normalized)  # type: ignore[misc]
    label = BASE_LABELS[base]
    return f"{label} {index}" if index else label


def zone_sort_key(value) -> tuple[int, int, str]:
    """RMW → RMW1 → PL → PL1 → PL2 → FGW → OUTSIDE → 其他。

    第三個元素讓無法解析的代碼有穩定順序（排最後但彼此照字母排）。
    """
    normalized = normalize_zone(value)
    text = "" if value is None else str(value).strip()
    if normalized is None:
        return (99, 0, text.upper())
    if normalized == "OUTSIDE":
        return (BASE_ORDER["OUTSIDE"], 0, "")
    base, index = parse_zone(normalized)  # type: ignore[misc]
    return (BASE_ORDER[base], index, "")


def sort_zones(codes) -> list[str]:
    return sorted(codes, key=zone_sort_key)


def indoor_zones(codes) -> list[str]:
    """排除 Outside 的倉間清單，依報告順序。"""
    return [z for z in sort_zones(codes) if normalize_zone(z) != "OUTSIDE"]


def labels_longest_first(codes) -> list[tuple[str, str]]:
    """`[(小寫全名, 代碼), ...]`，長的排前面。

    給「標題裡提到哪個倉間」這種子字串比對用：`Production Line 1` 也包含
    `Production Line`，短的先比會把 PL1 誤判成 PL。
    """
    pairs = [(zone_label(code).lower(), normalize_zone(code) or str(code)) for code in codes]
    return sorted(pairs, key=lambda kv: -len(kv[0]))


def describe_allowed() -> str:
    """給違規訊息用的人話說明。"""
    return (
        "只接受 RMW / PL / FGW，倉間拆成多個時加編號（PL1、PL2）；"
        "不可填全名或加空格（`Production Line 1`、`PL 1` 都不行）"
    )
