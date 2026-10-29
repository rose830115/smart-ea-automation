"""CFU 類別順序：後台微生物卡片 + 標準化 Excel CFU 列排序。 .venv/bin/python -m unittest discover -s tests"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from smart_ea_automation import ReferenceData, sort_cfu_rows_for_backend_order  # noqa: E402
from yims_payload_builder import build_microbiology_rows  # noqa: E402


def micro(swab, cat):
    return {"swab": swab, "category_to_select": cat, "count_to_enter": 1, "cfu_per_m2_for_check": 3333}


class CfuOrderTest(unittest.TestCase):
    def test_cards_sorted_by_display_order_unknown_last(self):
        area = {"microbiology": [micro(1, "設備"), micro(2, "不存在類別"), micro(3, "原材料"), micro(4, "設備"), micro(5, "建築本體")]}
        rows = build_microbiology_rows(area)
        self.assertEqual([r["microbiology_sampling_object_type"] for r in rows], [1, 6, 7, 0])
        # 卡片內物件維持原列序
        equip = rows[1]["microbiology_sampling_objects"]
        self.assertEqual([o["microbiology_sampling_object_sampling_number"] for o in equip], ["1", "4"])

    def test_other_category_displays_last_despite_smaller_id(self):
        # 其他 id=9 < 生產設備 11 / 通風與除濕設備 12，但下拉顯示在最後；不可用 id 升冪
        area = {"microbiology": [micro(1, "其他"), micro(2, "通風與除濕設備"), micro(3, "生產設備"), micro(4, "乘載器具")]}
        rows = build_microbiology_rows(area)
        self.assertEqual([r["microbiology_sampling_object_type"] for r in rows], [10, 11, 12, 9])

    def test_excel_cfu_rows_sorted_zone_area_category_stable(self):
        ref = ReferenceData({}, {"Area 1": {"zone": "RMW"}, "Area 2": {"zone": "PL"}}, {}, {}, {}, {}, {})
        def r(sw, area, cls):
            return {"Swab": sw, "Report Area": area, "Main Zone": "", "Classification": cls}
        rows = [r(1, "Area 2", "f.設備"), r(2, "Area 1", "l.其他"), r(3, "Area 1", "a.原材料"), r(4, "Area 1", "未知"), r(5, "Area 1", "a.原材料"), r(6, "Area 1", "j.生產設備")]
        out = [x["Swab"] for x in sort_cfu_rows_for_backend_order(rows, ref)]
        # RMW(Area 1) 先；原材料(3,5 原序) -> 生產設備(id 11 但顯示序在其他前) -> 其他 -> 未知(id0)最後；PL(Area 2)在後
        self.assertEqual(out[:5], [3, 5, 6, 2, 4])
        self.assertEqual(out[5], 1)


if __name__ == "__main__":
    unittest.main()
