from __future__ import annotations

import copy
import json
from pathlib import Path
from statistics import mean
from typing import Any


OBJECT_MOISTURE_CATEGORY_IDS = {
    "原材料": 1,
    "半成品": 2,
    "成品": 3,
    "包裝材": 4,
    "包裝材料": 4,  # ITEMLIST 用「包裝材料」(4字), 對應後台同一個包裝材選項(id 4)
    "外包裝": 5,
    "設備": 6,
    "建築本體": 7,
    "其它": 8,
    "其他": 8,
}

MICROBIOLOGY_CATEGORY_IDS = {
    "原材料": 1,
    "半成品": 2,
    "成品": 3,
    "包裝材": 4,
    "包裝材料": 4,  # ITEMLIST 用「包裝材料」(4字), 對應後台同一個包裝材選項(id 4)
    "外包裝": 5,
    "設備": 6,
    "建築本體": 7,
    "工作人員": 8,
    "其它": 9,
    "其他": 9,
    "乘載器具": 10,
    "生產設備": 11,
    "通風與除濕設備": 12,
}

FALLBACK_MOLD_NAME_TO_ID = {
    "alternaria sp.": 134,
    "aspergillus flavus": 43,
    "aspergillus fumigatus": 44,
    "aspergillus niger": 46,
    "aspergillus sp.": 107,
    "aureobasidium pullulans": 55,
    "chaetomium globosum": 59,
    "cladosporium sp.": 110,
    "curvularia sp.": 133,
    "fusarium equiseti": 73,
    "fusarium sp.": 71,
    "neurospora crassa": 123,
    "nigrospora sp.": 450,
    "paecilomyces sp.": 135,
    "penicillium citrinum": 87,
    "penicillium oxalicum": 8,
    "penicillium sp.": 106,
    "rhizopus sp.": 66,
    "trichoderma sp.": 97,
}


def safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def maybe_int(value: float | int | None) -> float | int | None:
    if value is None:
        return None
    if float(value).is_integer():
        return int(value)
    return round(float(value), 3)


def number_list(values: list[Any]) -> list[float | int]:
    cleaned: list[float | int] = []
    for value in values:
        parsed = safe_float(value)
        if parsed is not None:
            compacted = maybe_int(parsed)
            if compacted is not None:
                cleaned.append(compacted)
    return cleaned


def avg(values: list[Any]) -> float | int:
    nums = [safe_float(value) for value in values]
    nums = [value for value in nums if value is not None]
    if not nums:
        return 0
    return maybe_int(mean(nums)) or 0


def rounded_avg(values: list[Any], digits: int = 1) -> float | int:
    nums = [safe_float(value) for value in values]
    nums = [value for value in nums if value is not None]
    if not nums:
        return 0
    return maybe_int(round(mean(nums), digits)) or 0


def ratio_percent(numerator: Any, denominator: Any) -> float | int:
    top = safe_float(numerator)
    bottom = safe_float(denominator)
    if not top or not bottom:
        return 0
    return maybe_int(round(top / bottom * 100, 1)) or 0


def failure_rate(values: list[Any], threshold: float = 10) -> float | int:
    nums = [safe_float(value) for value in values]
    nums = [value for value in nums if value is not None]
    if not nums:
        return 0
    return maybe_int(round(sum(1 for value in nums if value > threshold) / len(nums) * 100, 1)) or 0


def cfu_from_count(value: Any) -> float | int:
    parsed = safe_float(value)
    if parsed is None:
        return 0
    return round(parsed / 3 * 10000)


def air_pollution_level(value: Any) -> float | int:
    parsed = safe_float(value) or 0
    return maybe_int(parsed * 210) or 0


def mold_contamination_weight_from_air_pollution(value: Any) -> int:
    parsed = safe_float(value) or 0
    return 1 if parsed > 10000 else 0


def microbiology_weight(cfus: list[Any], average: Any) -> float | int:
    numbers = [safe_float(value) for value in cfus]
    numbers = [value for value in numbers if value is not None]
    outlier_weight = 0
    if any(value > 125000 for value in numbers):
        outlier_weight = 1
    elif any(25000 < value <= 125000 for value in numbers):
        outlier_weight = 0.5

    parsed_average = safe_float(average) or 0
    if parsed_average < 25000:
        average_weight = 0
    elif parsed_average <= 125000:
        average_weight = 1
    else:
        average_weight = 2
    return maybe_int(average_weight + outlier_weight) or 0


def object_contamination_label(value: Any) -> str:
    parsed = safe_float(value) or 0
    if parsed >= 50000:
        return "高"
    if parsed >= 10000:
        return "中"
    return "低"


def lang(en: str = "", zh: str = "") -> dict[str, str]:
    return {"zh-tw": zh, "en": en}


def default_visibility_risk() -> dict[str, Any]:
    return {
        "visibility_risk_selected": None,
        "second_options": [],
        "visibility_risk_selected_array": [
            {
                "selected_value": None,
                "selected_photos": [],
            }
        ],
    }


def default_moisture_row() -> dict[str, Any]:
    return {
        "object_moisture_content_type": 0,
        "object_moisture_contents": ["", "", ""],
        "object_moisture_content_average": 0,
        "object_moisture_content_failure_rate": 0,
    }


def default_microbiology_row() -> dict[str, Any]:
    return {
        "microbiology_sampling_object_type": 0,
        "microbiology_sampling_objects": [
            {
                "microbiology_sampling_object_sampling_number": "",
                "microbiology_sampling_object_sampling_value": "",
                "microbiology_sampling_object_sampling_cfu": 0,
            }
        ],
        "microbiology_sampling_object_sampling_cfu_average": 0,
        "microbiology_sampling_object_isolate_mold_species": [0],
    }


def default_assessment_area() -> dict[str, Any]:
    return {
        "is_assessment_area_array_hidden": 0,
        "assessment_area_name": lang(),
        "function_name": lang(),
        "dehumidifier_quantity": 0,
        "exhaust_fans_quantity": 0,
        "temperatures": ["", "", "", "", "", ""],
        "temperature_average": 0,
        "relative_humidities": ["", "", "", "", "", ""],
        "relative_humidity_average": 0,
        "humidity_permeability": 0,
        "carbon_dioxides": ["", "", "", "", "", ""],
        "carbon_dioxide_average": 0,
        "particulate_matter_10s": ["", "", "", "", "", ""],
        "particulate_matter_10_average": 0,
        "air_pollution_level": 0,
        "spore_infiltration_rate": 0,
        "mold_contamination_index_weighted": 0,
        "spore_blow_indexes": ["", "", "", "", "", ""],
        "spore_blow_index_average": 0,
        "space_lumen_indexes": ["", "", "", "", "", ""],
        "space_lumen_index_average": 0,
        "object_moisture_content_array": [default_moisture_row()],
        "object_moisture_content_total_failure_rate": 0,
        "microbiology_sampling_object_array": [default_microbiology_row()],
        "microbiology_sampling_object_total_sampling_cfu_average": 0,
        "microbiology_sampling_mold_contamination_index_weighted": 0,
        "atp_sampling_object_array": [
            {
                "atp_sampling_object_type": 0,
                "atp_sampling_objects": [{"atp_sampling_object_sampling_number": "", "atp_sampling_object_sampling_value": ""}],
                "atp_sampling_object_sampling_rlu_average": 0,
            }
        ],
        "atp_sampling_object_total_sampling_rlu_average": 0,
        "atp_sampling_object_mold_contamination_index_weighted": 0,
        "air_sampling_object_array": [
            {
                "air_sampling_object_type": "MB2",
                "air_sampling_objects": [{"air_sampling_object_sampling_number": "", "air_sampling_object_sampling_value": ""}],
                "air_sampling_object_sampling_cfu": 0,
            },
            {
                "air_sampling_object_type": "MB3",
                "air_sampling_objects": [{"air_sampling_object_sampling_number": "", "air_sampling_object_sampling_value": ""}],
                "air_sampling_object_sampling_cfu": 0,
            },
        ],
        "air_sampling_object_sampling_cfu_average": 0,
        "air_sampling_object_isolate_mold_species": [0],
        "air_sampling_object_mold_contamination_index_weighted": 0,
        "distribution_of_mold": [],
    }


def default_main_area() -> dict[str, Any]:
    return {
        "main_area_name": lang(),
        "main_area_photo": [],
        "evaluation_area_division": [],
        "mold_risk_floor_plan": [],
        "non_compliance_array": [],
        "ordinary_risk": [],
        "visibility_risk_array": [default_visibility_risk()],
        "assessment_area_array": [default_assessment_area()],
        "environmental_conclusion": lang(),
        "microbiological_conclusion": lang(),
    }


# 後台 main_area 裡「由人工維護、工具完全不產生」的欄位。
# 這些欄位需要人工在後台選項目 / 上傳照片 (可視性風險、工廠照片、發霉風險平面圖、
# 不符合項、一般風險、評估區域劃分)。工具存檔時若用空白預設整批覆蓋, 會清掉同事已填的內容,
# 所以存檔前要從後台既有資料把它們原封搬回來。
HUMAN_MANAGED_MAIN_AREA_FIELDS = (
    "main_area_photo",
    "evaluation_area_division",
    "mold_risk_floor_plan",
    "non_compliance_array",
    "ordinary_risk",
    "visibility_risk_array",
)


def _main_area_match_key(main_area: dict[str, Any]) -> str:
    name = main_area.get("main_area_name")
    if isinstance(name, dict):
        return (
            str(name.get("en") or "").strip().casefold()
            or str(name.get("zh-tw") or "").strip().casefold()
        )
    return str(name or "").strip().casefold()


def preserve_human_managed_main_area_fields(
    new_main_areas: list[dict[str, Any]],
    existing_main_areas: list[dict[str, Any]] | None,
) -> None:
    """把後台既有的人工欄位 (可視性風險、照片、平面圖等) 保留到新 payload。

    工具只負責環境 / Moisture / 微生物數據; 上面 HUMAN_MANAGED_MAIN_AREA_FIELDS
    列的欄位是人工在後台手動維護的, 工具重建 main_area_array 時一律是空白預設,
    直接存檔會覆蓋掉人工輸入。這裡依 main_area 名稱 (退而求其次用位置) 對回後台既有資料,
    只要後台原本有該欄位就整個搬過來, 避免清掉同事的可視性風險與照片。
    """
    existing_main_areas = existing_main_areas or []
    existing_by_key: dict[str, dict[str, Any]] = {}
    for area in existing_main_areas:
        if isinstance(area, dict):
            existing_by_key.setdefault(_main_area_match_key(area), area)

    for idx, new_area in enumerate(new_main_areas or []):
        if not isinstance(new_area, dict):
            continue
        existing = existing_by_key.get(_main_area_match_key(new_area))
        if existing is None and idx < len(existing_main_areas):
            candidate = existing_main_areas[idx]
            existing = candidate if isinstance(candidate, dict) else None
        if existing is None:
            continue
        for field in HUMAN_MANAGED_MAIN_AREA_FIELDS:
            if field in existing:
                new_area[field] = copy.deepcopy(existing[field])


def category_id(label: str, mapping: dict[str, int]) -> int:
    return mapping.get(label.strip(), mapping.get(label.strip().replace("其他", "其它"), 0))


def normalize_mold_name(value: Any) -> str:
    text = str(value or "").strip()
    text = text.replace("spp.", "sp.").replace("Spp.", "sp.")
    text = text.replace(" spp", " sp").replace(" Spp", " sp")
    text = " ".join(text.split())
    return text.casefold()


def mold_name_to_id_map(mold_options: list[dict[str, Any]] | None = None) -> dict[str, int]:
    mapping = dict(FALLBACK_MOLD_NAME_TO_ID)
    for mold in mold_options or []:
        mold_id = mold.get("molds_id")
        if mold_id is None:
            continue
        genus = str(mold.get("genus") or "").strip()
        species = str(mold.get("species") or "").strip()
        if not species or species.casefold() == "none":
            continue
        names = [genus, f"{genus} {species}".strip()]
        for name in names:
            if name:
                mapping[normalize_mold_name(name)] = int(mold_id)
    return mapping


def mold_species_ids(names: list[Any], mold_options: list[dict[str, Any]] | None = None) -> list[int]:
    mapping = mold_name_to_id_map(mold_options)
    ids: list[int] = []
    for name in names or []:
        mold_id = mapping.get(normalize_mold_name(name))
        if mold_id is not None and mold_id not in ids:
            ids.append(mold_id)
    return ids or [0]


def build_moisture_rows(area: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in area.get("moisture", []):
        values = number_list(item.get("values", []))
        row = default_moisture_row()
        row["object_moisture_content_type"] = category_id(item.get("category_to_select", ""), OBJECT_MOISTURE_CATEGORY_IDS)
        row["object_moisture_contents"] = values or [""]
        row["object_moisture_content_average"] = rounded_avg(values, 1)
        row["object_moisture_content_failure_rate"] = failure_rate(values)
        rows.append(row)
    return rows or [default_moisture_row()]


def build_microbiology_rows(area: dict[str, Any], mold_options: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    grouped: dict[int, dict[str, Any]] = {}
    for item in area.get("microbiology", []):
        cat_id = category_id(item.get("category_to_select", ""), MICROBIOLOGY_CATEGORY_IDS)
        if cat_id not in grouped:
            grouped[cat_id] = {
                "microbiology_sampling_object_type": cat_id,
                "microbiology_sampling_objects": [],
                "microbiology_sampling_object_sampling_cfu_average": 0,
                "microbiology_sampling_object_isolate_mold_species": [0],
            }
        species_ids = mold_species_ids(item.get("isolate_mold_species_names", []), mold_options)
        if species_ids != [0]:
            existing_ids = grouped[cat_id]["microbiology_sampling_object_isolate_mold_species"]
            if existing_ids == [0]:
                existing_ids = []
            for mold_id in species_ids:
                if mold_id not in existing_ids:
                    existing_ids.append(mold_id)
            grouped[cat_id]["microbiology_sampling_object_isolate_mold_species"] = existing_ids or [0]
        count = item.get("count_to_enter")
        cfu = item.get("cfu_per_m2_for_check")
        if cfu is None:
            cfu = cfu_from_count(count)
        grouped[cat_id]["microbiology_sampling_objects"].append(
            {
                "microbiology_sampling_object_sampling_number": str(item.get("swab") or ""),
                "microbiology_sampling_object_sampling_value": "" if count is None else str(maybe_int(safe_float(count))),
                "microbiology_sampling_object_sampling_cfu": cfu,
            }
        )

    rows = []
    for row in grouped.values():
        cfus = [obj["microbiology_sampling_object_sampling_cfu"] for obj in row["microbiology_sampling_objects"]]
        row["microbiology_sampling_object_sampling_cfu_average"] = rounded_avg(cfus, 1)
        rows.append(row)
    return rows or [default_microbiology_row()]


def build_assessment_area(
    area: dict[str, Any],
    outside_rh: float | None,
    outside_pm10: float | None,
    mold_options: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    yims_area = default_assessment_area()
    env = area.get("env", {})
    temperatures = number_list(env.get("temperature_c", []))
    humidities = number_list(env.get("humidity_percent", []))
    carbon_dioxides = number_list(env.get("co2_ppm", []))
    wind = number_list(env.get("wind_flow_m_s", []))
    pm10 = number_list(env.get("pm10_ug_m3", []))

    yims_area["assessment_area_name"] = lang(str(area.get("assessment_area", "")))
    yims_area["function_name"] = lang(str(area.get("function", "")))
    yims_area["temperatures"] = temperatures or [""]
    yims_area["temperature_average"] = rounded_avg(temperatures, 1)
    yims_area["relative_humidities"] = humidities or [""]
    yims_area["relative_humidity_average"] = rounded_avg(humidities, 1)
    yims_area["humidity_permeability"] = ratio_percent(yims_area["relative_humidity_average"], outside_rh)
    yims_area["carbon_dioxides"] = carbon_dioxides or [""]
    yims_area["carbon_dioxide_average"] = rounded_avg(carbon_dioxides, 1)
    yims_area["spore_blow_indexes"] = wind or [""]
    yims_area["spore_blow_index_average"] = rounded_avg(wind, 2)
    yims_area["particulate_matter_10s"] = pm10 or [""]
    yims_area["particulate_matter_10_average"] = rounded_avg(pm10, 1)
    yims_area["air_pollution_level"] = air_pollution_level(yims_area["particulate_matter_10_average"])
    yims_area["spore_infiltration_rate"] = ratio_percent(yims_area["particulate_matter_10_average"], outside_pm10)
    yims_area["mold_contamination_index_weighted"] = mold_contamination_weight_from_air_pollution(
        yims_area["air_pollution_level"]
    )

    moisture_rows = build_moisture_rows(area)
    yims_area["object_moisture_content_array"] = moisture_rows
    yims_area["object_moisture_content_total_failure_rate"] = rounded_avg(
        [row.get("object_moisture_content_failure_rate") for row in moisture_rows],
        1,
    )

    microbiology_rows = build_microbiology_rows(area, mold_options=mold_options)
    yims_area["microbiology_sampling_object_array"] = microbiology_rows
    all_cfus = []
    for row in microbiology_rows:
        all_cfus.extend(obj.get("microbiology_sampling_object_sampling_cfu") for obj in row.get("microbiology_sampling_objects", []))
    yims_area["microbiology_sampling_object_total_sampling_cfu_average"] = rounded_avg(all_cfus, 1)
    yims_area["microbiology_sampling_mold_contamination_index_weighted"] = microbiology_weight(
        all_cfus,
        yims_area["microbiology_sampling_object_total_sampling_cfu_average"],
    )
    return yims_area


def outside_average(payload: dict[str, Any], field: str) -> float | None:
    values = []
    for group in payload.get("outside", []):
        for area in group.get("areas", []):
            values.extend(area.get("env", {}).get(field, []))
    nums = [safe_float(value) for value in values]
    nums = [value for value in nums if value is not None]
    return mean(nums) if nums else None


def outside_values(payload: dict[str, Any], field: str) -> list[float | int]:
    values = []
    for group in payload.get("outside", []):
        for area in group.get("areas", []):
            values.extend(area.get("env", {}).get(field, []))
    return number_list(values)


def form_values(values: list[float | int], fallback_count: int = 6) -> list[float | int | str]:
    return values if values else [""] * fallback_count


def build_outside_extends_data(backend_payload: dict[str, Any]) -> dict[str, Any]:
    temperatures = outside_values(backend_payload, "temperature_c")
    humidities = outside_values(backend_payload, "humidity_percent")
    carbon_dioxides = outside_values(backend_payload, "co2_ppm")
    wind = outside_values(backend_payload, "wind_flow_m_s")
    pm10 = outside_values(backend_payload, "pm10_ug_m3")
    pm10_average = rounded_avg(pm10, 1)

    return {
        "temperatures": form_values(temperatures),
        "temperature_average": rounded_avg(temperatures, 1),
        "relative_humidities": form_values(humidities),
        "relative_humidity_average": rounded_avg(humidities, 1),
        "carbon_dioxides": form_values(carbon_dioxides),
        "carbon_dioxide_average": rounded_avg(carbon_dioxides, 1),
        "spore_blow_indexes": form_values(wind),
        "spore_blow_index_average": rounded_avg(wind, 2),
        "particulate_matter_10s": form_values(pm10),
        "particulate_matter_10_average": pm10_average,
        "air_pollution_level": air_pollution_level(pm10_average),
    }


def build_yims_extends_data(
    backend_payload: dict[str, Any],
    comments: dict[str, str] | None = None,
    mold_options: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    comments = comments or {}
    outside_rh = outside_average(backend_payload, "humidity_percent")
    outside_pm10 = outside_average(backend_payload, "pm10_ug_m3")
    main_area_array = []

    for group in backend_payload.get("indoor", []):
        main_area = default_main_area()
        zone = group.get("main_zone", "")
        main_area["main_area_name"] = lang(str(group.get("main_zone_label") or zone))
        main_area["assessment_area_array"] = [
            build_assessment_area(
                area,
                outside_rh=outside_rh,
                outside_pm10=outside_pm10,
                mold_options=mold_options,
            )
            for area in group.get("areas", [])
        ] or [default_assessment_area()]
        if zone in comments:
            main_area["environmental_conclusion"] = lang(comments[zone])
        main_area_array.append(main_area)

    extends_data = build_outside_extends_data(backend_payload)
    extends_data.update(
        {
            "main_area_array": main_area_array or [default_main_area()],
        }
    )
    return extends_data


def build_fill_plan(backend_payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for group in backend_payload.get("indoor", []):
        for area in group.get("areas", []):
            rows.append(
                {
                    "main_zone": group.get("main_zone"),
                    "main_zone_label": group.get("main_zone_label"),
                    "assessment_area": area.get("assessment_area"),
                    "function": area.get("function"),
                    "env": area.get("env", {}),
                    "moisture_rows": len(area.get("moisture", [])),
                    "microbiology_rows": len(area.get("microbiology", [])),
                    "checking_points": area.get("checking_points", []),
                }
            )
    return rows


def load_comments(metrics_path: Path | None) -> dict[str, str]:
    if not metrics_path or not metrics_path.exists():
        return {}
    data = json.loads(metrics_path.read_text(encoding="utf-8"))
    return data.get("comments", {})


def write_yims_fill_plan(
    backend_payload: dict[str, Any],
    json_path: Path,
    markdown_path: Path,
    comments: dict[str, str] | None = None,
) -> dict[str, Any]:
    extends_data = build_yims_extends_data(backend_payload, comments=comments)
    plan = build_fill_plan(backend_payload)
    output = {
        "case_name": backend_payload.get("case_name", ""),
        "purpose": "yims_fill_plan",
        "mode": "vue_state_injection_then_manual_review",
        "safety": {
            "default_behavior": "Fill the YIMS page UI state only; do not click submit unless explicitly requested.",
            "submit_control": "yims_bot.py requires --save before it calls the YIMS save method.",
        },
        "summary": {
            "main_area_count": len(extends_data["main_area_array"]),
            "assessment_area_count": sum(len(zone["assessment_area_array"]) for zone in extends_data["main_area_array"]),
            "plan_rows": len(plan),
        },
        "plan": plan,
        "extends_data": extends_data,
    }
    json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# YIMS Fill Plan",
        "",
        f"- Case: `{output['case_name']}`",
        f"- Main areas: {output['summary']['main_area_count']}",
        f"- Assessment areas: {output['summary']['assessment_area_count']}",
        "",
        "Default behavior: fill the YIMS page state for review only. The bot will not click `送出` unless run with `--save`.",
        "",
        "| Main Zone | Assessment Area | Function | Env Fields | Moisture Rows | Microbiology Rows |",
        "|---|---|---|---|---:|---:|",
    ]
    for row in plan:
        env_fields = ", ".join(f"{key}:{len(value)}" for key, value in row["env"].items())
        lines.append(
            f"| {row['main_zone_label']} | {row['assessment_area']} | {row['function']} | "
            f"{env_fields} | {row['moisture_rows']} | {row['microbiology_rows']} |"
        )
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return output
