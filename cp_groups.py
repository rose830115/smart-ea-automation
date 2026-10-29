"""群組採樣點：業務檔 Col A 把同一個 Report Area 的多個 Checking Point 寫在同一格（`1,2,3`）。

只支援實際看到的寫法：半形逗號、全形逗號、頓號（前後空白容忍）。
區間（`1-3`）與空白分隔不支援——不過度設計，寫成那樣會被事前檢查擋下。
"""

from __future__ import annotations

import re

_GROUP_SEP = re.compile(r"[,，、]")


def split_cp_group(text: str) -> list[str]:
    """把群組標籤拆成成員 CP（轉大寫、去空白、略過空成員）。

    單一 CP 回傳只含自己的 list；空字串回傳 []。
    """
    if not text:
        return []
    return [part.strip().upper() for part in _GROUP_SEP.split(str(text)) if part.strip()]


def is_cp_group(text: str) -> bool:
    return len(split_cp_group(text)) > 1
