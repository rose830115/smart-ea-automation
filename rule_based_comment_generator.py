from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from statistics import mean
from typing import Any


ZONE_ORDER = ["RMW", "PL", "FGW"]
ZONE_LABELS = {
    "RMW": "Raw Material Warehouse",
    "PL": "Production Line",
    "FGW": "Finished Goods Warehouse",
}

CATEGORY_LABELS = {
    "原材料": "raw materials",
    "半成品": "semi-finished goods",
    "成品": "finished goods",
    "外包裝": "outer packaging",
    "設備": "equipment",
    "建築本體": "building structures",
    "工作人員": "workers",
    "生產設備": "operating equipment",
    "通風與除濕設備": "ventilation and dehumidification equipment",
    "其它": "other items",
    "其他": "other items",
}

CATEGORY_IMPACTS = {
    "raw materials": "could directly carry spores into the production process",
    "semi-finished goods": "could transfer contamination to later production stages",
    "finished goods": "could directly affect product quality during storage",
    "outer packaging": "could contact products or transfer spores between warehouses",
    "equipment": "could contaminate materials and goods through repeated contact",
    "building structures": "could act as persistent indoor contamination sources",
    "workers": "could contribute to cross-contamination during handling",
    "operating equipment": "could transfer spores to goods during production",
    "ventilation and dehumidification equipment": "could disperse spores through air movement during operation",
    "other items": "could become potential contamination sources in the space",
}

OBJECT_NAME_MAP = {
    "carton box": "carton boxes",
    "inner box": "inner boxes",
    "wooden rack": "wooden racks",
    "wooden pallet": "wooden pallets",
    "wooden equipment": "wooden equipment",
    "rack": "racks",
    "table": "tables",
    "trolley": "trolleys",
    "dehumidifier filter": "dehumidifier filters",
    "fan": "fans",
    "building structure": "building structures",
    "finished goods": "finished goods",
    "gloves": "gloves",
    "upper": "uppers",
    "leather": "leather",
    "fabric": "fabric",
    "mesh": "mesh",
    "foam": "foam",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def numbers(values: list[Any]) -> list[float]:
    parsed = [number(value) for value in values or []]
    return [value for value in parsed if value is not None]


def avg(values: list[Any]) -> float | None:
    vals = numbers(values)
    return mean(vals) if vals else None


def fmt(value: Any, digits: int = 1) -> str:
    parsed = number(value)
    if parsed is None:
        return "N.A."
    if abs(parsed - round(parsed)) < 0.000001:
        return str(int(round(parsed)))
    return f"{parsed:.{digits}f}"


def fmt_pct(value: Any, digits: int = 1) -> str:
    return f"{fmt(value, digits)}%"


def fmt_count(value: Any) -> str:
    parsed = number(value)
    if parsed is None:
        return "N.A."
    return f"{parsed:,.0f}"


def area_sort_key(area: str) -> tuple[int, Any]:
    match = re.search(r"\d+", str(area))
    if match:
        return (0, int(match.group()))
    return (1, str(area))


def join_items(items: list[str], limit: int = 5) -> str:
    cleaned = []
    seen = set()
    for item in items:
        text = str(item).strip()
        key = text.casefold()
        if text and key not in seen:
            cleaned.append(text)
            seen.add(key)
    if not cleaned:
        return "none"
    shown = cleaned[:limit]
    if len(shown) == 1:
        return shown[0]
    if len(shown) == 2:
        return f"{shown[0]} and {shown[1]}"
    return ", ".join(shown[:-1]) + f", and {shown[-1]}"


def join_phrases(items: list[str], limit: int = 5) -> str:
    cleaned = []
    seen = set()
    for item in items:
        text = str(item).strip()
        key = text.casefold()
        if text and key not in seen:
            cleaned.append(text)
            seen.add(key)
    if not cleaned:
        return ""
    shown = cleaned[:limit]
    if len(shown) == 1:
        return shown[0]
    if len(shown) == 2:
        return f"{shown[0]}; and {shown[1]}"
    return "; ".join(shown[:-1]) + f"; and {shown[-1]}"


def normalized_object_key(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip().replace("-", " "))
    return text.casefold()


def object_name(value: Any) -> str:
    key = normalized_object_key(value)
    if not key:
        return "sampled objects"
    return OBJECT_NAME_MAP.get(key, key)


def object_family(object_value: Any, category: str) -> str:
    text = normalized_object_key(object_value)
    if any(token in text for token in ["carton", "inner box", "cardboard", "paper box"]):
        return "paper_packaging"
    if "wood" in text:
        return "wooden_items"
    if category == "raw materials":
        return "raw_materials"
    if category == "semi-finished goods":
        return "semi_finished_goods"
    if category == "finished goods":
        return "finished_goods"
    if category == "ventilation and dehumidification equipment":
        return "ventilation_equipment"
    if category in {"equipment", "operating equipment"}:
        return "equipment"
    if category == "building structures":
        return "building_structures"
    if category == "workers":
        return "workers"
    return "other_items"


def category_label(value: Any) -> str:
    text = str(value or "").strip()
    if "." in text:
        text = text.split(".", 1)[1]
    return CATEGORY_LABELS.get(text, text.lower() if text else "other items")


def risk_level(value: float | None, overall: bool = False) -> str:
    if value is None:
        return "undetermined"
    if overall:
        if value <= 20:
            return "low"
        if value <= 40:
            return "moderate-low"
        if value <= 60:
            return "moderate"
        if value <= 80:
            return "moderate-high"
        return "high"
    if value <= 25:
        return "low"
    if value <= 50:
        return "medium"
    if value <= 75:
        return "moderate-high"
    return "high"


def cfu_level(value: float | None) -> str:
    if value is None:
        return "undetermined"
    if value > 125000:
        return "high"
    if value >= 25000:
        return "moderate"
    return "low"


def area_average(area: dict[str, Any], field: str) -> float | None:
    return avg(area.get("env", {}).get(field, []))


def area_air_count(area: dict[str, Any]) -> float | None:
    pm10 = area_average(area, "pm10_ug_m3")
    return pm10 * 210 if pm10 is not None else None


def outside_baselines(payload: dict[str, Any]) -> dict[str, float | None]:
    outside_groups = payload.get("outside", [])
    if not outside_groups:
        return {"rh": None, "pm10": None}
    areas = outside_groups[0].get("areas", [])
    rh_values: list[Any] = []
    pm10_values: list[Any] = []
    for area in areas:
        env = area.get("env", {})
        rh_values.extend(env.get("humidity_percent", []))
        pm10_values.extend(env.get("pm10_ug_m3", []))
    return {"rh": avg(rh_values), "pm10": avg(pm10_values)}


def moisture_items(areas: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    failed: list[dict[str, Any]] = []
    by_category: dict[str, dict[str, Any]] = {}
    for area in areas:
        for item in area.get("moisture", []):
            vals = numbers(item.get("values", []))
            if not vals:
                continue
            failed_vals = [v for v in vals if v > 10]
            category = category_label(item.get("category_to_select") or item.get("classification_source"))
            stat = by_category.setdefault(category, {"values": [], "failed": 0, "objects": set()})
            stat["values"].extend(vals)
            stat["failed"] += len(failed_vals)
            if failed_vals:
                stat["objects"].add(item.get("object", ""))
                failed.append(
                    {
                        "area": area.get("assessment_area", ""),
                        "object": item.get("object", ""),
                        "category": category,
                        "avg": mean(vals),
                        "max": max(vals),
                        "failed_ratio": len(failed_vals) / len(vals) * 100,
                    }
                )
    for stat in by_category.values():
        total = len(stat["values"])
        stat["failed_ratio"] = stat["failed"] / total * 100 if total else 0
        stat["objects"] = sorted([obj for obj in stat["objects"] if obj], key=str.casefold)
    return failed, by_category


def microbiology_items(areas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for area in areas:
        for item in area.get("microbiology", []):
            cfu = number(item.get("cfu_per_m2_for_check"))
            rows.append(
                {
                    "area": area.get("assessment_area", ""),
                    "object": item.get("object", ""),
                    "category": category_label(item.get("category_to_select") or item.get("classification_source")),
                    "cfu": cfu,
                    "level": cfu_level(cfu),
                    "swab": item.get("swab"),
                }
            )
    return rows


def zone_stats(payload: dict[str, Any], risk_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    baselines = outside_baselines(payload)
    stats: dict[str, dict[str, Any]] = {}
    for zone_group in payload.get("indoor", []):
        zone = zone_group.get("main_zone")
        if zone not in ZONE_ORDER:
            continue
        areas = sorted(zone_group.get("areas", []), key=lambda item: area_sort_key(item.get("assessment_area", "")))
        rh = [area_average(area, "humidity_percent") for area in areas]
        co2 = [area_average(area, "co2_ppm") for area in areas]
        wind = [area_average(area, "wind_flow_m_s") for area in areas]
        pm10 = [area_average(area, "pm10_ug_m3") for area in areas]
        rh_vals = [v for v in rh if v is not None]
        co2_vals = [v for v in co2 if v is not None]
        wind_vals = [v for v in wind if v is not None]
        pm10_vals = [v for v in pm10 if v is not None]
        avg_rh = mean(rh_vals) if rh_vals else None
        avg_pm10 = mean(pm10_vals) if pm10_vals else None
        hpr = avg_rh / baselines["rh"] * 100 if avg_rh is not None and baselines["rh"] else None
        sir = avg_pm10 / baselines["pm10"] * 100 if avg_pm10 is not None and baselines["pm10"] else None
        failed_moisture, moisture_by_category = moisture_items(areas)
        micro_rows = microbiology_items(areas)
        area_air = {area.get("assessment_area", ""): area_air_count(area) for area in areas}
        stats[zone] = {
            "zone": zone,
            "label": ZONE_LABELS[zone],
            "areas": areas,
            "avg_rh": mean(rh_vals) if rh_vals else None,
            "avg_co2": mean(co2_vals) if co2_vals else None,
            "avg_wind": mean(wind_vals) if wind_vals else None,
            "avg_pm10": avg_pm10,
            "humidity_permeability": hpr,
            "spore_infiltration": sir,
            "area_rh": {area.get("assessment_area", ""): area_average(area, "humidity_percent") for area in areas},
            "area_co2": {area.get("assessment_area", ""): area_average(area, "co2_ppm") for area in areas},
            "area_wind": {area.get("assessment_area", ""): area_average(area, "wind_flow_m_s") for area in areas},
            "area_sir": {
                area.get("assessment_area", ""): (
                    area_average(area, "pm10_ug_m3") / baselines["pm10"] * 100
                    if area_average(area, "pm10_ug_m3") is not None and baselines["pm10"]
                    else None
                )
                for area in areas
            },
            "area_air": area_air,
            "failed_moisture": failed_moisture,
            "moisture_by_category": moisture_by_category,
            "microbiology": micro_rows,
            "env_risk": number(risk_data.get("env_risk", {}).get(zone)),
            "micro_risk": number(risk_data.get("micro_risk", {}).get(zone)),
            "overall_risk": number(risk_data.get("overall_risk", {}).get(zone)),
        }
    return stats


def exceeded_areas(area_values: dict[str, float | None], predicate) -> list[str]:
    return [area for area, value in area_values.items() if value is not None and predicate(value)]


def max_area(area_values: dict[str, float | None]) -> tuple[str, float] | None:
    values = [(area, value) for area, value in area_values.items() if value is not None]
    return max(values, key=lambda item: item[1]) if values else None


def moisture_summary(m: dict[str, Any]) -> tuple[str, str]:
    failed = sorted(m["failed_moisture"], key=lambda item: item["max"], reverse=True)
    if not failed:
        return "no specific objects exceeded the 10% moisture standard", ""
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for item in failed:
        label = object_name(item["object"])
        family = object_family(item["object"], item["category"])
        key = (label, family)
        group = grouped.setdefault(
            key,
            {
                "label": label,
                "family": family,
                "areas": set(),
                "max": 0.0,
                "category": item["category"],
            },
        )
        group["areas"].add(item["area"])
        group["max"] = max(group["max"], item["max"])

    groups = sorted(grouped.values(), key=lambda item: item["max"], reverse=True)
    object_phrases = []
    for group in groups[:7]:
        areas = join_items(sorted(group["areas"], key=area_sort_key), limit=8)
        object_phrases.append(
            f"{group['label']} in {areas} with a maximum moisture content of {fmt_pct(group['max'])}"
        )

    family_names: dict[str, list[str]] = {}
    for group in groups:
        family_names.setdefault(group["family"], []).append(group["label"])

    impacts = []
    if "paper_packaging" in family_names:
        names = join_items(family_names["paper_packaging"], limit=4)
        impacts.append(
            f"high moisture content in {names} could have provided a favorable environment for mold growth, and these packages may have affected material or product quality because they could contact raw materials, semi-finished goods, or finished goods"
        )
    if "wooden_items" in family_names:
        names = join_items(family_names["wooden_items"], limit=4)
        impacts.append(
            f"{names} could have provided nutrients required for mold growth; their high moisture content could have created a more suitable growth environment, and contact with raw materials or semi-finished goods may have affected material quality"
        )
    if "raw_materials" in family_names:
        names = join_items(family_names["raw_materials"], limit=4)
        impacts.append(
            f"high moisture content in {names} could have supported mold growth directly on raw materials and may have carried spores into the production process"
        )
    if "semi_finished_goods" in family_names:
        names = join_items(family_names["semi_finished_goods"], limit=4)
        impacts.append(
            f"high moisture content in {names} could have supported mold growth on semi-finished goods and may have transferred contamination to later production stages"
        )
    if "finished_goods" in family_names:
        names = join_items(family_names["finished_goods"], limit=4)
        impacts.append(
            f"high moisture content in {names} could have supported mold growth during storage and may have directly affected product quality"
        )
    if "equipment" in family_names:
        names = join_items(family_names["equipment"], limit=4)
        impacts.append(
            f"high moisture content on {names} could have allowed spores to remain on contact surfaces and may have transferred contamination during handling or production"
        )
    if "ventilation_equipment" in family_names:
        names = join_items(family_names["ventilation_equipment"], limit=4)
        impacts.append(
            f"high moisture content on {names} could have supported mold growth on ventilation-related surfaces and may have dispersed spores during operation"
        )
    if "building_structures" in family_names:
        names = join_items(family_names["building_structures"], limit=4)
        impacts.append(
            f"high moisture content in {names} could have made the building surfaces persistent indoor contamination sources"
        )
    if "other_items" in family_names:
        names = join_items(family_names["other_items"], limit=4)
        impacts.append(
            f"high moisture content in {names} could have made these items potential local contamination sources"
        )

    return join_phrases(object_phrases, limit=7), join_phrases(impacts, limit=5)


def micro_surface_summary(rows: list[dict[str, Any]], level_filter: set[str]) -> tuple[str, str]:
    selected = [row for row in rows if row["level"] in level_filter]
    selected = sorted(selected, key=lambda row: row["cfu"] or 0, reverse=True)
    if not selected:
        return "no moderate or high surface contamination", ""
    shown_rows = selected[:7]
    object_texts = [
        f"{object_name(row['object'])} in {row['area']} with {fmt_count(row['cfu'])} CFU/m2 at a {row['level']} level"
        for row in shown_rows
    ]
    impacts = []
    impact_seen = set()
    for row in shown_rows:
        family = object_family(row["object"], row["category"])
        if family in impact_seen:
            continue
        impact_seen.add(family)
        names = object_name(row["object"])
        if family == "paper_packaging":
            impacts.append(
                f"contaminated {names} may have transferred spores by direct contact with materials, packages, or goods"
            )
        elif family == "wooden_items":
            impacts.append(
                f"contaminated {names} may have retained spores on nutrient-rich surfaces and transferred them to contacted materials"
            )
        elif family == "raw_materials":
            impacts.append(f"contaminated {names} could have carried spores into the production process")
        elif family == "semi_finished_goods":
            impacts.append(f"contaminated {names} could have transferred spores to later production stages")
        elif family == "finished_goods":
            impacts.append(f"contaminated {names} may have directly affected product quality during storage")
        elif family == "ventilation_equipment":
            impacts.append(f"contaminated {names} may have dispersed spores through air movement during operation")
        elif family in {"equipment", "workers"}:
            impacts.append(f"contaminated {names} could have transferred spores through repeated contact")
        elif family == "building_structures":
            impacts.append(f"contaminated {names} could have acted as persistent indoor contamination sources")
        else:
            impacts.append(f"contaminated {names} could have become potential local contamination sources")
    return join_phrases(object_texts, limit=7), join_phrases(impacts, limit=5)


def issue_names(m: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if m["avg_rh"] is not None and m["avg_rh"] > 60:
        issues.append("relative humidity")
    if m["humidity_permeability"] is not None and m["humidity_permeability"] > 90:
        issues.append("humidity permeability rate")
    if m["avg_co2"] is not None and m["avg_co2"] > 600:
        issues.append("carbon dioxide")
    if exceeded_areas(m["area_wind"], lambda v: v < 0.4):
        issues.append("mold spore blow index")
    if m["spore_infiltration"] is not None and m["spore_infiltration"] > 90:
        issues.append("spore infiltration rate")
    if m["failed_moisture"]:
        issues.append("object moisture content")
    return issues


def environmental_comment(m: dict[str, Any]) -> str:
    issues = issue_names(m)
    if len(issues) == 1:
        lead = f"The main environmental issue in the {m['label']} was {issues[0]}."
    else:
        lead = f"The main environmental issues in the {m['label']} were {join_items(issues, limit=8)}."

    sentences = [lead]
    high_rh = exceeded_areas(m["area_rh"], lambda v: v > 60)
    max_rh = max_area(m["area_rh"])
    objects, impacts = moisture_summary(m)

    if high_rh and max_rh:
        sentences.append(
            f"Relative humidity exceeded the 60% standard in {join_items(high_rh)}, "
            f"with the highest value in {max_rh[0]} at {fmt_pct(max_rh[1])}; this could have increased moisture absorption by {objects}."
        )

    hpr = m["humidity_permeability"]
    if hpr is not None and hpr > 100:
        sentences.append(
            f"The humidity permeability rate was {fmt_pct(hpr)}, exceeding 100%, which indicated that moisture may have accumulated indoors and might not have been exhausted effectively because indoor humidity was higher than outdoor humidity."
        )
    elif hpr is not None and hpr > 90:
        sentences.append(
            f"The humidity permeability rate was {fmt_pct(hpr)}, which indicated that outdoor humidity could have strongly affected indoor humidity."
        )

    low_wind = exceeded_areas(m["area_wind"], lambda v: v < 0.4)
    high_sir_areas = exceeded_areas(m["area_sir"], lambda v: v > 90)
    if low_wind and high_sir_areas:
        sentences.append(
            f"Low mold spore blow index in {join_items(low_wind)} and spore infiltration above 90% in {join_items(high_sir_areas)} could have allowed spores to remain indoors, accumulate, and settle on object surfaces."
        )
    elif low_wind:
        sentences.append(
            f"Low mold spore blow index in {join_items(low_wind)} could have reduced the ability to dislodge spores from object surfaces."
        )
    elif high_sir_areas:
        sentences.append(
            f"Spore infiltration above 90% in {join_items(high_sir_areas)} suggested that spores may have remained indoors for a longer period."
        )

    high_co2 = exceeded_areas(m["area_co2"], lambda v: v > 600)
    if high_co2:
        sentences.append(
            f"Carbon dioxide exceeded 600 ppm in {join_items(high_co2)}, which could have been related to possible microbial activity or insufficient air exchange."
        )

    if m["failed_moisture"] and impacts:
        sentences.append(f"The exceeded objects were relevant because {impacts}.")

    return " ".join(sentences)


def microbiology_comment(m: dict[str, Any]) -> str:
    air_exceeded = [area for area, value in m["area_air"].items() if value is not None and value >= 10000]
    surface_text, impacts = micro_surface_summary(m["microbiology"], {"moderate", "high"})
    high_surface_text, _ = micro_surface_summary(m["microbiology"], {"high"})

    sentences: list[str] = []
    if air_exceeded:
        sentences.append(
            f"Air contamination exceeded the 10,000 cts/m3 standard in {join_items(air_exceeded)}, indicating that airborne spores may have increased the chance of surface deposition."
        )
    else:
        sentences.append(
            f"Air contamination in the {m['label']} complied with the 10,000 cts/m3 standard, but surface contamination still showed the main microbiological concern."
        )

    if surface_text != "no moderate or high surface contamination":
        sentences.append(f"Moderate to high surface contamination was detected on {surface_text}.")
    if high_surface_text != "no moderate or high surface contamination":
        sentences.append(
            f"The high-contamination objects could have acted as direct contamination sources even when air contamination remained within the standard."
        )
    if impacts:
        sentences.append(f"These objects were relevant because {impacts}.")

    return " ".join(sentences)


def ranked_zones(stats: dict[str, dict[str, Any]], field: str) -> list[str]:
    return sorted(ZONE_ORDER, key=lambda zone: stats.get(zone, {}).get(field) or -1, reverse=True)


def common_environmental_sources(stats: dict[str, dict[str, Any]]) -> list[str]:
    candidates = ["relative humidity", "humidity permeability rate", "mold spore blow index", "spore infiltration rate", "object moisture content", "carbon dioxide"]
    result = []
    for candidate in candidates:
        count = sum(1 for zone in ZONE_ORDER if candidate in issue_names(stats[zone]))
        if count >= 2:
            result.append(candidate)
    return result


def family_presence_summary(presence: dict[str, set[str]]) -> tuple[list[str], list[str]]:
    labels = {
        "paper_packaging": "paper-based packaging",
        "wooden_items": "wooden contact surfaces",
        "raw_materials": "raw materials",
        "semi_finished_goods": "semi-finished goods",
        "finished_goods": "finished goods",
        "equipment": "equipment and operating equipment",
        "ventilation_equipment": "ventilation and dehumidification equipment",
        "building_structures": "building structures",
        "workers": "workers' contact surfaces",
        "other_items": "other stored items",
    }
    shared = [labels[key] for key, zones in presence.items() if len(zones) >= 2 and key in labels]
    any_zone = [labels[key] for key, zones in presence.items() if zones and key in labels]
    return shared, any_zone


def moisture_family_presence(stats: dict[str, dict[str, Any]]) -> dict[str, set[str]]:
    presence: dict[str, set[str]] = {}
    for zone in ZONE_ORDER:
        for item in stats[zone]["failed_moisture"]:
            family = object_family(item["object"], item["category"])
            presence.setdefault(family, set()).add(zone)
    return presence


def microbiology_family_presence(stats: dict[str, dict[str, Any]]) -> dict[str, set[str]]:
    presence: dict[str, set[str]] = {}
    for zone in ZONE_ORDER:
        for row in stats[zone]["microbiology"]:
            if row["level"] not in {"moderate", "high"}:
                continue
            family = object_family(row["object"], row["category"])
            presence.setdefault(family, set()).add(zone)
    return presence


def overall_environmental_comment(stats: dict[str, dict[str, Any]]) -> str:
    ranking = ranked_zones(stats, "env_risk")
    top = ranking[0]
    sources = common_environmental_sources(stats)
    hpr_over_100 = [zone for zone in ZONE_ORDER if (stats[zone]["humidity_permeability"] or 0) > 100]
    moisture_shared, moisture_any = family_presence_summary(moisture_family_presence(stats))

    sentences = [
        "Across the three main zones, mold risk from the environmental perspective was mainly shaped by the same moisture-retention and spore-retention pattern.",
        f"The environmental risk ranking was {join_items([ZONE_LABELS[z] + ' ' + fmt_pct(stats[z]['env_risk']) for z in ranking], limit=3)}, with the {ZONE_LABELS[top]} showing the highest environmental mold risk.",
    ]
    if sources:
        sentences.append(
            f"The shared abnormal parameters were {join_items(sources, limit=6)}, indicating that the issue was not limited to a single warehouse."
        )
    if hpr_over_100:
        sentences.append(
            f"Humidity permeability above 100% in {join_items([ZONE_LABELS[z] for z in hpr_over_100], limit=3)} indicated that indoor moisture may have accumulated across the facility and might not have been exhausted effectively."
        )
    if moisture_shared:
        sentences.append(
            f"Moisture failures repeatedly involved {join_items(moisture_shared, limit=5)}, so absorbent contact surfaces could have provided water or nutrients for mold growth while materials, packages, or goods moved between warehouses."
        )
    elif moisture_any:
        sentences.append(
            f"Moisture failures involved {join_items(moisture_any, limit=5)}, which could have provided water or nutrients for mold growth on contact surfaces."
        )
    sentences.append(
        "Low mold spore blow index combined with high spore infiltration could have allowed spores to remain indoors and settle on the same moisture-retaining surfaces, linking the Raw Material Warehouse, Production Line, and Finished Goods Warehouse through material handling and storage flow."
    )
    if top == "FGW":
        sentences.append(
            "The Finished Goods Warehouse could have shown the highest environmental risk because moisture accumulation and spore retention may have persisted into the storage stage, where finished goods and packaging were exposed for longer periods."
        )
    else:
        sentences.append(
            f"The {ZONE_LABELS[top]} could have shown the highest environmental risk because shared moisture and spore-retention factors were most concentrated there."
        )
    return " ".join(sentences)


def overall_microbiology_comment(stats: dict[str, dict[str, Any]]) -> str:
    ranking = ranked_zones(stats, "micro_risk")
    top = ranking[0]
    surface_shared, surface_any = family_presence_summary(microbiology_family_presence(stats))
    air_within_standard = all(
        not [area for area, value in stats[zone]["area_air"].items() if value is not None and value >= 10000]
        for zone in ZONE_ORDER
    )

    sentences = [
        "Across the three main zones, microbiological risk was mainly driven by surface contamination rather than airborne contamination.",
        f"The microbiological risk ranking was {join_items([ZONE_LABELS[z] + ' ' + fmt_pct(stats[z]['micro_risk']) for z in ranking], limit=3)}, with the {ZONE_LABELS[top]} showing the highest microbiological risk.",
    ]
    if air_within_standard:
        sentences.append(
            "Air contamination in all three zones remained within the standard, so the shared microbiological concern was the presence of contaminated surfaces that could have acted as local reservoirs."
        )
    if surface_shared:
        sentences.append(
            f"The recurring contaminated surface types were {join_items(surface_shared, limit=5)}, showing that potential reservoirs existed on objects involved in storage, handling, air movement, or product contact."
        )
    elif surface_any:
        sentences.append(
            f"The contaminated surface types included {join_items(surface_any, limit=5)}, showing that potential reservoirs existed on objects involved in storage, handling, air movement, or product contact."
        )
    sentences.append(
        "This pattern could have supported cross-zone transfer: contaminated packaging or ventilation-related surfaces in the Raw Material Warehouse may have carried spores toward production, contaminated equipment and contact surfaces in the Production Line may have spread spores during processing, and contaminated stored objects or ventilation surfaces in the Finished Goods Warehouse may have retained spores during storage."
    )
    if top == "PL":
        sentences.append(
            "The Production Line could have shown the highest microbiological risk because it contained more repeated-contact surfaces, so surface contamination there may have affected both incoming materials and downstream goods."
        )
    else:
        sentences.append(
            f"The {ZONE_LABELS[top]} could have shown the highest microbiological risk because contaminated surface reservoirs were most concentrated there."
        )
    return " ".join(sentences)


def comprehensive_comment(stats: dict[str, dict[str, Any]]) -> str:
    ranking = ranked_zones(stats, "overall_risk")
    values = [stats[z]["overall_risk"] for z in ZONE_ORDER if stats[z]["overall_risk"] is not None]
    risk_range = f"{fmt_pct(min(values))} to {fmt_pct(max(values))}" if values else "N.A."
    top = ranking[0]

    sentences = [
        f"Based on the environmental and microbiological results, the overall mold risk of the evaluated areas ranged from {risk_range}, and the highest overall risk was found in the {ZONE_LABELS[top]} at {fmt_pct(stats[top]['overall_risk'])}.",
        f"The overall risk ranking was {join_items([ZONE_LABELS[z] + ' ' + fmt_pct(stats[z]['overall_risk']) for z in ranking], limit=3)}.",
    ]

    rmw_surface, _ = micro_surface_summary(stats["RMW"]["microbiology"], {"moderate", "high"})
    pl_surface, _ = micro_surface_summary(stats["PL"]["microbiology"], {"moderate", "high"})
    fgw_surface, _ = micro_surface_summary(stats["FGW"]["microbiology"], {"moderate", "high"})

    if rmw_surface != "no moderate or high surface contamination":
        sentences.append(
            "Surface contamination in the Raw Material Warehouse, especially on packaging or ventilation and dehumidification equipment, could have become a potential source carried toward the Production Line with materials or packages."
        )
    if pl_surface != "no moderate or high surface contamination":
        sentences.append(
            "In the Production Line, contaminated equipment, operating equipment, workers' contact surfaces, or finished goods could have transferred spores during processing and may have carried contamination into the storage stage."
        )
    if fgw_surface != "no moderate or high surface contamination":
        sentences.append(
            "In the Finished Goods Warehouse, high humidity, moisture accumulation, and contaminated stored objects or ventilation-related equipment could have allowed spores carried from earlier stages to remain on finished goods or surrounding surfaces."
        )
    sentences.append(
        "The combined pattern showed that environmental conditions could have supported spore persistence, while microbiological surface contamination provided potential contamination sources across the warehouse-to-production-to-storage flow."
    )
    return " ".join(sentences)


def generate_rule_based_comments(payload: dict[str, Any], risk_data: dict[str, Any]) -> dict[str, str]:
    stats = zone_stats(payload, risk_data)
    comments: dict[str, str] = {}
    for zone in ZONE_ORDER:
        comments[f"{zone}_env"] = environmental_comment(stats[zone])
        comments[f"{zone}_micro"] = microbiology_comment(stats[zone])
    comments["OVERALL_ENV"] = overall_environmental_comment(stats)
    comments["OVERALL_MICRO"] = overall_microbiology_comment(stats)
    comments["OVERALL_COMPREHENSIVE"] = comprehensive_comment(stats)
    return comments


def write_comments_txt(comments: dict[str, str], outdir: Path, case_name: str) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / f"{case_name}_rule_based_comments.txt"
    sections = [
        ("RMW_env", "Raw Material Warehouse - Environmental Comment"),
        ("PL_env", "Production Line - Environmental Comment"),
        ("FGW_env", "Finished Goods Warehouse - Environmental Comment"),
        ("OVERALL_ENV", "Overall Environmental Comment"),
        ("RMW_micro", "Raw Material Warehouse - Microbiology Comment"),
        ("PL_micro", "Production Line - Microbiology Comment"),
        ("FGW_micro", "Finished Goods Warehouse - Microbiology Comment"),
        ("OVERALL_MICRO", "Overall Microbiology Comment"),
        ("OVERALL_COMPREHENSIVE", "Comprehensive Overall Mold Risk Comment"),
    ]
    lines = [f"{case_name} Smart EA Rule-Based Comment Draft", ""]
    for key, title in sections:
        lines.extend([title, comments.get(key, ""), ""])
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return path


def generate_from_files(payload_path: Path, risk_path: Path, outdir: Path, case_name: str) -> dict[str, Any]:
    payload = load_json(payload_path)
    risk_data = load_json(risk_path)
    comments = generate_rule_based_comments(payload, risk_data)
    txt_path = write_comments_txt(comments, outdir, case_name)
    json_path = outdir / f"{case_name}_rule_based_comments.json"
    json_path.write_text(json.dumps(comments, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"comments": comments, "txt_path": txt_path, "json_path": json_path}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Smart EA rule-based comments without LLM API")
    parser.add_argument("--payload", required=True, type=Path)
    parser.add_argument("--risk", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    parser.add_argument("--case-name", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = generate_from_files(args.payload, args.risk, args.outdir, args.case_name)
    print(result["txt_path"])


if __name__ == "__main__":
    main()
