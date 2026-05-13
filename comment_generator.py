#!/usr/bin/env python3
"""
Smart EA Comment Generator
Calls OpenAI ChatGPT to generate comments based on YIMS backend risk data and local metrics.

Risk data (env_risk / micro_risk per zone) must come from the YIMS backend report page,
fetched automatically by yims_bot.py after data entry.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ZONE_LABELS = {
    "RMW": "Raw Material Warehouse",
    "PL": "Production Line",
    "FGW": "Finished Goods Warehouse",
}

# ---------------------------------------------------------------------------
# Writing guidelines extracted from Smart EA 評論撰寫指引 20251205.xmind
# ---------------------------------------------------------------------------

_GUIDE_ENV_SMALL = """
ENVIRONMENTAL SMALL COMMENT WRITING GUIDE (per zone)

Start with one of:
- "The risk sources in the [Zone] were [parameters]."
- "The main issue in the [Zone] was [single parameter]."
- "The issues in the [Zone] were [parameter] and [parameter]."

Then describe each exceeded parameter with its actual value:

Relative Humidity (standard ≤60%):
- Exceeded: "The relative humidity exceeded the standard value of 60%, which indicated that the indoor environment was favorable for mold growth."
  Link to moisture: "High humidity might increase the moisture content of [objects] inside the [Zone], providing a suitable environment for mold growth."
- Near threshold (55–60%): "Although the relative humidity met the standard value, it was very close to 60%, so proper management was still necessary."

Humidity Permeability Rate (standard ≤90%):
- "The humidity permeability rate reached over the standard threshold of 90%. This could mean that outdoor relative humidity had a large effect on influencing indoor relative humidity."
- "The high humidity permeability rate could imply that the indoor relative humidity in this zone was easily affected by the higher outdoor relative humidity."
- If the value exceeds 100%, explain that moisture had clearly accumulated indoors and was not easily exhausted because indoor humidity was already higher than outdoor humidity.

Object Moisture Content (standard ≤10%):
- "Moisture content in most [object category], such as [objects], reached more than 10%, which was an indication that these objects could readily provide moisture and nutrients for mold growth."
- "The moisture content for [objects] was still high because most [objects] consist of [material] that could easily absorb water from the environment."

Mold Spore Blow Index (standard ≥0.4 m/s):
- "The mold spore blow index was below the minimum required value, which might be an indication that there was not sufficient wind force to dislodge lingering spores from the surface of objects, leading to spore accumulation."
- "Low mold spore blow index indicated insufficient ventilation, which would lead to the accumulation of spores and dust inside the space."

Spore Infiltration Rate (standard ≤90%):
- "The spore infiltration rate was higher than the suggested value, implying that outdoor spores could easily enter and remain indoors for a long period of time."
- "The exceeding spore infiltration rate revealed that any potential indoor spores were more likely to remain indoors than being expelled to the outdoors due to improper ventilation."

Carbon Dioxide (standard ≤600 ppm):
- "Since the carbon dioxide levels was higher than recommended, signs of microbiological growth was possible."
- "Area [X] had high levels of carbon dioxide gases, which indicated possible mold growth and might lower workers' comfort."
"""

_GUIDE_ENV_OVERALL = """
ENVIRONMENTAL OVERALL COMMENT WRITING GUIDE

Fixed intro sentence (always use one of these, do not modify):
Option A: "Mold needs suitable environmental conditions to germinate, mature, and reproduce in the factory or on the goods. Relative humidity, object moisture, air exchange, and spore accumulation are key factors that can determine whether a space becomes favorable for mold growth."
Option B: "Mold requires suitable environmental conditions, including humidity, moisture availability, ventilation-related factors, and other risk sources, to germinate, mature, and reproduce on factory goods or within the factory itself. A comprehensive evaluation of environmental data from the Raw Material Warehouse, Production Line, and Finished Goods Warehouse identified several risk factors that could lead to mold growth, potentially impacting product quality and storage conditions."
Tool rule: Temperature is only a reference parameter and is not part of the scoring standard. Do not mention temperature in generated comments.

Risk ranking sentence: "The environmental analysis showed that [Zone] had the highest environmental mold risk, with [Zone] ranking the second highest and [Zone] having the lowest amongst the three main zones. The common factors between the zones were found to be [parameters]."

Inter-parameter interaction examples:
- High humidity + moisture: "As a key factor in mold growth, humidity levels exceeded the 60% standard in [zones]. In correlation with humidity, item moisture level was the related factor in mold growth."
- Spore blow index + spore infiltration + CO2: "Carbon dioxide levels across all areas within the 600 ppm standard suggest that mold is not fully active. However, ventilation-related indexes pointed out mold spore accumulation."
- Summary: "In summary, [Zone] had the highest mold risk from an environmental perspective. Not only could this zone contain a high amount of spores in the air and on the surface of items but also could supply enough moisture for germination."
"""

_GUIDE_MICRO_SMALL = """
MICROBIOLOGY SMALL COMMENT WRITING GUIDE (per zone)

Air Contamination:
- Exceeded: "Air contamination levels in Areas [X] exceeded the standard threshold, suggesting that these areas had high spore concentration in the air. More spores would likely settle on the surface of objects, increasing surface contamination."
- Exceeded + link to surface: "Overall contamination levels were consistent across Areas [X], primarily due to air contamination. Over-standard air contamination indicating high spore concentrations increased the risk of mold spores spreading between warehouses and attaching to item surfaces."
- Compliant: "All areas complied with the air contamination standards. No immediate mold risk was detected on items."

Surface Contamination (by object type):
- Raw materials / semi-finished / finished goods: "Contamination on materials and goods could directly influence the quality of the finished goods products since mold could directly grow on the surface when environmental conditions became favorable."
- Packaging materials: "Since these items could directly come in contact with the finished goods inside, contamination could spread onto the finished goods when packed."
- Equipment / production equipment: "These equipment could directly touch materials and goods during production, thus allowing potential contamination to spread onto the goods."
- Building structures: "Mold contamination on building structures could affect the entire indoor space since spores could be gradually dispersed from these sources."
- Workers: "Potential high contamination on workers' gloves could lead to widespread cross-contamination since workers could be touching different objects in different locations."
- Ventilation / dehumidification equipment: "Contamination on ventilation equipment could end up facilitating spores to be dispersed across the entire space during operation."
"""

_GUIDE_MICRO_OVERALL = """
MICROBIOLOGY OVERALL COMMENT WRITING GUIDE

Fixed intro sentence (always use, do not modify):
"Based on the average microbiological contamination level of each zone, overall microbiological contamination during the production process can be seen. As stated in the description, the microbiological contamination level was differentiated into 0–100% according to the degree of surface and air contamination in the particular area or the particular production process."

Risk ranking: "In general, [Zone] had the highest microbiological mold risk amongst the three main zones, followed by the [Zone] and then the [Zone]."

Cross-zone analysis:
- "High air contamination levels in these zones indicated that during the production phase that took place in these zones, any materials and goods could be exposed to an environment with a high amount of mold spores."
- Conclusion: "In conclusion, the high microbiological mold risk in the [Zone] was due to the higher surface contamination found on [object types], which could pose an immediate threat to the quality of the finished goods in the long run."
"""

_GUIDE_COMPREHENSIVE = """
COMPREHENSIVE OVERALL MOLD RISK COMMENT WRITING GUIDE

Fixed intro sentence (always use, do not modify):
"Based on the factory environment and microbiological contamination analyses, the mold risk of each area of the production processes can be assessed. The mold risk of each area was graded based on its severity, as shown in the above picture. The overall mold risk of the factory was at a [risk level] level. The risk percentage of the evaluated areas fell between a range of [min to max]%."

Overall ranking: "Overall, the [Zone] had the highest mold risk due to [parameters]. This is followed by the [Zone] and then the [Zone]."

Cross-factor interactions (use the ones that apply):
- Humidity/moisture + microbiology exceeded: "High humidity and moisture could help facilitate the growth of mold, especially on materials that were detected with high surface contamination. Therefore, this zone could pose an immediate risk of having mold issues."
- Spore blow index/infiltration + microbiology exceeded: "The low mold spore blow index and high spore infiltration rate combined with the high air contamination level in this area indicated that air spores could remain indoors and accumulate, ultimately leading to more spores covering and settling on the surfaces of materials and equipment."
- Spore + no surface contamination yet: "Insufficient mold spore blow index and exceeding spore infiltration rate would continue to encourage potential spores to settle and contaminate objects, which could increase surface contamination levels in the future."

Conclusion options:
- "To conclude, [Zone] posed the highest environmental mold risk due to poor ventilation as spores could easily accumulate and settle on exposed materials."
- "In conclusion, the storage area for the packed finished goods posed the highest mold risk. Even though the finished goods were packed already, contamination could happen if the outer package was damaged."
"""


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _fmt(value: Any, digits: int = 1) -> str:
    if value is None:
        return "N/A"
    try:
        f = float(value)
        return f"{f:.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def _flags_text(m: dict[str, Any]) -> str:
    flags = []
    rh = m.get("avg_rh")
    hpr = m.get("humidity_permeability")
    co2 = m.get("avg_co2")
    wind = m.get("avg_wind")
    si = m.get("spore_infiltration")
    mfr = m.get("moisture_failed_ratio", 0)
    high_cls = m.get("high_moisture_classes", [])

    if rh and rh > 60:
        flags.append(f"Relative Humidity {_fmt(rh)}% (exceeded >60%)")
    elif rh and rh >= 55:
        flags.append(f"Relative Humidity {_fmt(rh)}% (near threshold 55–60%)")
    if hpr and hpr > 90:
        if hpr > 100:
            flags.append(
                f"Humidity Permeability Rate {_fmt(hpr)}% (exceeded >100%; indoor moisture accumulation)"
            )
        else:
            flags.append(f"Humidity Permeability Rate {_fmt(hpr)}% (exceeded >90%)")
    if co2 and co2 > 600:
        flags.append(f"CO2 {_fmt(co2, 0)} ppm (exceeded >600 ppm)")
    if wind and wind < 0.4:
        flags.append(f"Mold Spore Blow Index {_fmt(wind, 2)} m/s (below <0.4 m/s)")
    if si and si > 90:
        flags.append(f"Spore Infiltration Rate {_fmt(si)}% (exceeded >90%)")
    if mfr > 50:
        flags.append(f"Object Moisture Failed Ratio {_fmt(mfr)}% (exceeded >50%)")
    elif high_cls:
        flags.append(f"High moisture content in: {', '.join(high_cls)}")
    return "\n".join(f"  - {f}" for f in flags) if flags else "  - No parameters exceeded standard"


def build_env_zone_prompt(zone: str, metrics: dict[str, Any], env_risk_pct: float | None) -> str:
    m = metrics.get(zone, {})
    label = ZONE_LABELS[zone]
    risk_str = f"{env_risk_pct:.1f}%" if env_risk_pct is not None else "N/A (fetch from YIMS)"
    failed_objs = ", ".join(m.get("failed_objects", [])[:6]) or "none detected"
    high_rh_areas = ", ".join(m.get("high_rh_areas", [])) or "none"
    low_wind_areas = ", ".join(m.get("low_wind_areas", [])) or "none"
    high_si_areas = ", ".join(m.get("high_pm10_areas", [])) or "none"
    high_cls = ", ".join(m.get("high_moisture_classes", [])) or "none"

    return f"""Write an environmental comment paragraph for the {label} in a Smart EA mold risk audit report.

ZONE: {label}
YIMS official Environmental Mold Risk: {risk_str}

Measured parameters:
  - Avg Relative Humidity: {_fmt(m.get('avg_rh'))}%
  - Humidity Permeability Rate: {_fmt(m.get('humidity_permeability'))}%
  - Avg CO2: {_fmt(m.get('avg_co2'), 0)} ppm
  - Avg Mold Spore Blow Index: {_fmt(m.get('avg_wind'), 2)} m/s
  - Spore Infiltration Rate: {_fmt(m.get('spore_infiltration'))}%
  - Object Moisture Failed Ratio: {_fmt(m.get('moisture_failed_ratio'))}%

Exceeded parameters:
{_flags_text(m)}

Notable areas:
  - High-RH areas (>60%): {high_rh_areas}
  - Low-wind areas (<0.4 m/s): {low_wind_areas}
  - High-spore-infiltration areas (>90%): {high_si_areas}
Objects with high moisture content: {failed_objs}
High-moisture object categories: {high_cls}

Writing guide:
{_GUIDE_ENV_SMALL}

Output rules:
- One plain paragraph, 2–4 sentences, professional scientific English
- Start with the risk sources / main issue sentence
- Describe each exceeded parameter using its actual value
- Link related parameters (humidity → moisture content, low wind → spore accumulation)
- Point out the actual exceeded object categories/objects and explain why those objects matter
- Do not mention temperature; it is reference-only and not part of the scoring standard
- NO headers, NO bullet points, NO risk percentage in the text"""


def build_env_overall_prompt(metrics: dict[str, Any], risk_data: dict[str, Any]) -> str:
    env_risks = risk_data.get("env_risk", {})
    ranked = sorted(["RMW", "PL", "FGW"], key=lambda z: (env_risks.get(z) or 0), reverse=True)

    zone_lines = []
    for zone in ["RMW", "PL", "FGW"]:
        m = metrics.get(zone, {})
        r = env_risks.get(zone)
        exceeded = []
        if m.get("avg_rh") and m["avg_rh"] > 60: exceeded.append("RH")
        if m.get("humidity_permeability") and m["humidity_permeability"] > 90: exceeded.append("HPR")
        if m.get("avg_wind") and m["avg_wind"] < 0.4: exceeded.append("MSBI")
        if m.get("spore_infiltration") and m["spore_infiltration"] > 90: exceeded.append("SIR")
        if m.get("avg_co2") and m["avg_co2"] > 600: exceeded.append("CO2")
        if m.get("moisture_failed_ratio", 0) > 50: exceeded.append("Moisture")
        zone_lines.append(
            f"  - {ZONE_LABELS[zone]}: Official Risk={r or 'N/A'}%, Exceeded={', '.join(exceeded) or 'none'}"
        )

    return f"""Write an overall environmental mold risk comment for a Smart EA audit report.

Zone summary:
{chr(10).join(zone_lines)}

Risk ranking (highest to lowest): {' > '.join(ZONE_LABELS[z] for z in ranked)}

Writing guide:
{_GUIDE_ENV_OVERALL}

Output rules:
- Start with one of the two fixed intro sentences from the guide (copy exactly, no modification)
- State the risk ranking using official YIMS risk percentages
- Identify common risk parameters shared across zones
- Explain interactions between parameters
- Do not mention temperature; it is reference-only and not part of the scoring standard
- End with a concrete recommendation
- 3–5 sentences, professional scientific English
- NO headers, NO bullet points"""


def build_micro_zone_prompt(zone: str, cfu_data: list[dict], micro_risk_pct: float | None) -> str:
    label = ZONE_LABELS[zone]
    risk_str = f"{micro_risk_pct:.1f}%" if micro_risk_pct is not None else "N/A (fetch from YIMS)"

    zone_rows = [r for r in cfu_data if str(r.get("Main Zone", "")).strip() == zone]
    rows_text = []
    for r in zone_rows[:15]:
        count = r.get("Count")
        cfu = r.get("CFU/m²")
        obj = r.get("Object", "")
        cls = r.get("Classification", "")
        area = r.get("Report Area", "")
        swab = r.get("Swab", "")
        rows_text.append(
            f"  - Area {area}, {obj} ({cls}), Swab {swab}: Count={count}, CFU/m²={cfu}"
        )
    if not rows_text:
        rows_text = ["  (No CFU data available for this zone)"]

    return f"""Write a microbiology comment paragraph for the {label} in a Smart EA mold risk audit report.

ZONE: {label}
YIMS official Microbiology Mold Risk: {risk_str}

CFU sampling data:
{chr(10).join(rows_text)}

Writing guide:
{_GUIDE_MICRO_SMALL}

Output rules:
- One plain paragraph, 2–3 sentences, professional scientific English
- Describe air contamination levels (if swab data relates to air sampling)
- Describe surface contamination on detected objects/materials
- Link contaminated items to downstream mold risk (production quality, finished goods)
- NO headers, NO bullet points, NO risk percentage in the text"""


def build_micro_overall_prompt(cfu_data: list[dict], risk_data: dict[str, Any]) -> str:
    micro_risks = risk_data.get("micro_risk", {})
    ranked = sorted(["RMW", "PL", "FGW"], key=lambda z: (micro_risks.get(z) or 0), reverse=True)

    zone_lines = [
        f"  - {ZONE_LABELS[z]}: Official Microbiology Risk={micro_risks.get(z) or 'N/A'}%"
        for z in ["RMW", "PL", "FGW"]
    ]

    return f"""Write an overall microbiology mold risk comment for a Smart EA audit report.

Zone microbiology risk (from YIMS):
{chr(10).join(zone_lines)}

Risk ranking (highest to lowest): {' > '.join(ZONE_LABELS[z] for z in ranked)}

Writing guide:
{_GUIDE_MICRO_OVERALL}

Output rules:
- Start with the fixed intro sentence from the guide (copy exactly, no modification)
- State the risk ranking using official YIMS percentages
- Describe common contamination patterns across zones
- Explain cross-contamination risks between zones
- 3–4 sentences, professional scientific English
- NO headers, NO bullet points"""


def build_comprehensive_overall_prompt(
    metrics: dict[str, Any],
    cfu_data: list[dict],
    risk_data: dict[str, Any],
) -> str:
    env_risks = risk_data.get("env_risk", {})
    micro_risks = risk_data.get("micro_risk", {})
    overall_risks = risk_data.get("overall_risk", {})
    env_ranked = sorted(["RMW", "PL", "FGW"], key=lambda z: (env_risks.get(z) or 0), reverse=True)
    micro_ranked = sorted(["RMW", "PL", "FGW"], key=lambda z: (micro_risks.get(z) or 0), reverse=True)
    overall_ranked = sorted(["RMW", "PL", "FGW"], key=lambda z: (overall_risks.get(z) or 0), reverse=True)

    zone_lines = [
        (
            f"  - {ZONE_LABELS[z]}: Env={env_risks.get(z) or 'N/A'}%, "
            f"Micro={micro_risks.get(z) or 'N/A'}%, Overall={overall_risks.get(z) or 'N/A'}%"
        )
        for z in ["RMW", "PL", "FGW"]
    ]

    # Determine overall risk range
    all_risks = [v for v in overall_risks.values() if v is not None]
    if not all_risks:
        all_risks = [v for v in list(env_risks.values()) + list(micro_risks.values()) if v is not None]
    risk_range = f"{min(all_risks):.0f} to {max(all_risks):.0f}" if all_risks else "N/A"

    return f"""Write a comprehensive overall mold risk comment combining environmental and microbiology factors for a Smart EA audit report.

Zone risk summary (from YIMS official calculation):
{chr(10).join(zone_lines)}

Environmental risk ranking: {' > '.join(ZONE_LABELS[z] for z in env_ranked)}
Microbiology risk ranking: {' > '.join(ZONE_LABELS[z] for z in micro_ranked)}
Official overall risk ranking: {' > '.join(ZONE_LABELS[z] for z in overall_ranked)}
Overall risk range: {risk_range}%

Writing guide:
{_GUIDE_COMPREHENSIVE}

Output rules:
- Start with the fixed intro sentence from the guide (copy exactly, fill in risk level and range from data)
- State the overall ranking and which zone poses combined highest risk
- Analyze interaction between environmental and microbiology factors
- Reference specific parameters that compound the risk
- 4–5 sentences, professional scientific English
- NO headers, NO bullet points"""


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_comments(
    metrics: dict[str, Any],
    cfu_data: list[dict],
    risk_data: dict[str, Any],
    api_key: str | None = None,
    model: str = "gpt-4o",
) -> dict[str, str]:
    """Generate all 9 comments using ChatGPT.

    Returns dict with keys:
      RMW_env, PL_env, FGW_env, OVERALL_ENV,
      RMW_micro, PL_micro, FGW_micro, OVERALL_MICRO,
      OVERALL_COMPREHENSIVE
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise SystemExit(
            "缺少 openai 套件。請執行：pip install openai"
        )

    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError(
            "需要 OpenAI API key。請設定環境變數 OPENAI_API_KEY 或傳入 api_key 參數。"
        )

    client = OpenAI(api_key=key)

    system_prompt = (
        "You are an expert technical writer specializing in Smart Environmental Audit (Smart EA) "
        "mold risk reports. Write professional, data-driven comments in scientific English based on "
        "actual measurement data and the writing guidelines provided. "
        "Always produce exactly one plain paragraph without any headers, bullet points, or markdown."
    )

    def call_gpt(user_prompt: str) -> str:
        if hasattr(client, "responses"):
            response = client.responses.create(
                model=model,
                instructions=system_prompt,
                input=user_prompt,
                max_output_tokens=700,
            )
            output_text = getattr(response, "output_text", "")
            if output_text:
                return output_text.strip()

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_completion_tokens=700,
        )
        return response.choices[0].message.content.strip()

    env_risks = risk_data.get("env_risk", {})
    micro_risks = risk_data.get("micro_risk", {})

    comments: dict[str, str] = {}
    for zone in ["RMW", "PL", "FGW"]:
        comments[f"{zone}_env"] = call_gpt(
            build_env_zone_prompt(zone, metrics, env_risks.get(zone))
        )
        comments[f"{zone}_micro"] = call_gpt(
            build_micro_zone_prompt(zone, cfu_data, micro_risks.get(zone))
        )

    comments["OVERALL_ENV"] = call_gpt(build_env_overall_prompt(metrics, risk_data))
    comments["OVERALL_MICRO"] = call_gpt(build_micro_overall_prompt(cfu_data, risk_data))
    comments["OVERALL_COMPREHENSIVE"] = call_gpt(
        build_comprehensive_overall_prompt(metrics, cfu_data, risk_data)
    )

    return comments


def write_comments_md(comments: dict[str, str], outdir: Path, case_name: str) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    md_path = outdir / f"{case_name}_full_comments.md"

    sections = [
        ("RMW_env", "Raw Material Warehouse — Environmental Comment"),
        ("PL_env", "Production Line — Environmental Comment"),
        ("FGW_env", "Finished Goods Warehouse — Environmental Comment"),
        ("OVERALL_ENV", "Overall Environmental Comment"),
        ("RMW_micro", "Raw Material Warehouse — Microbiology Comment"),
        ("PL_micro", "Production Line — Microbiology Comment"),
        ("FGW_micro", "Finished Goods Warehouse — Microbiology Comment"),
        ("OVERALL_MICRO", "Overall Microbiology Comment"),
        ("OVERALL_COMPREHENSIVE", "Comprehensive Overall Mold Risk Comment"),
    ]

    lines = [f"# {case_name} Smart EA Full Comment Draft\n"]
    for key, title in sections:
        comment = comments.get(key, "（尚未生成）")
        lines.append(f"## {title}\n\n{comment}\n")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path
