# Smart EA Parameter Definitions for Comment Generation

建立日期：2026-05-13  
用途：作為評論生成 prompt 的資料索引，取代直接餵入完整正式報告文字，降低 token 浪費。

## Reference Sources

- Official report text extracted from `outputs/PYS_official_report_text.txt`
- YIMS print data API: `/api/orders/print/data?orders_id={order_id}&service_id={service_id}`
- Current comment guide text extracted into `comment_generator.py`

## Environmental Parameters

### Temperature

- Role: reference only.
- Scoring: not part of the scoring standard.
- Comment rule: do not mention temperature in generated comments unless Rose explicitly asks for it.

### Relative Humidity

- Standard: `RH <= 60%`
- Meaning: water vapor level in the space.
- Risk logic: high RH makes materials, products, storage equipment, and building structures absorb moisture. Higher moisture makes the space and objects more favorable for mold growth.
- Comment logic: connect high RH to high object moisture and mold growth conditions.

### Humidity Permeability Rate

- Standard: `<= 90%`
- Meaning: whether the room can isolate or exclude outdoor moisture.
- Formula confirmed by Rose: `indoor average RH / outdoor average RH * 100`
- Risk logic:
  - `>90%`: outdoor humidity strongly affects indoor humidity; indoor humidity control is insufficient.
  - `>100%`: indoor humidity is already higher than outdoor humidity, meaning moisture has clearly accumulated indoors and is not easily exhausted.
- Comment logic: do not only say "outdoor influence" when the value is above 100%; also mention indoor moisture accumulation.

### Object Moisture Content

- Object standard: `<= 10%`
- Area/category failed-ratio standard: `<= 50%`
- Meaning: water content inside or on objects.
- Risk logic: mold requires water to grow. Objects above 10% moisture content can provide enough water for mold growth. If a category has a failed ratio above 50%, that object category is an important risk source.
- Comment logic: point out the actual failed object category or object, then explain why it matters.

Examples of object impact:

- Raw material / semi-finished goods / finished goods: directly affect finished product quality.
- Outer packaging / carton box / inner box: high moisture provides a favorable environment for mold growth. Because paper-based packaging can contact raw materials, semi-finished goods, or finished goods, mold growth or spores on these packages may affect material or product quality.
- Wooden rack / wooden pallet / wooden equipment: wooden materials provide nutrients required for mold growth. When moisture content is high, they create a more suitable environment for mold growth; because they can contact raw materials or semi-finished goods, they may affect material quality.
- Equipment / operating equipment: can transfer spores during production by direct contact.
- Building structure: can become a long-term source of spores in the indoor space.
- Ventilation or dehumidification equipment: can disperse spores during operation.
- Workers' gloves: can cause cross-contamination between objects and areas.

### Carbon Dioxide

- Standard: `<= 600 ppm`
- Meaning: indicator of mold growth possibility and working air quality.
- Risk logic: high CO2 may indicate biological activity or poor air exchange. It should be treated as supporting evidence, not a standalone proof of mold growth.
- Comment logic: connect CO2 to ventilation and microbial growth only when supported by other data.

### Mold Spore Blow Index

- Standard: `>= 0.4 m/s`
- Meaning: wind speed index for removing or dislodging mold spores.
- Risk logic: when wind force is insufficient, spores are more likely to remain indoors and settle on object surfaces.
- Comment logic: low value should be connected to spore accumulation and surface contamination risk.

### Spore Infiltration Rate

- Standard: `<= 90%`
- Meaning: whether spores in the space can be transported outside effectively.
- Formula confirmed by Rose: `indoor average PM10 / outdoor average PM10 * 100`
- Risk logic: high value means spores can remain indoors and accumulate over time.
- Comment logic: combine with low Mold Spore Blow Index when both are abnormal.

### Air Pollution Level / PM10 Proxy

- Formula confirmed by Rose: `PM10 average * 210`
- Meaning: tool/YIMS proxy used to estimate air contamination or spore-related pollution.
- Risk logic: high airborne spores increase the chance of spores settling on object surfaces.

## Microbiological Parameters

### Air Contamination

- Standard: `< 10,000 cts/m3`
- Reported basis: Baxter et al., JOEH 2005, as cited in the Smart EA report text.
- Meaning: estimated mold spore concentration in the air.
- Risk logic: high air contamination increases the chance of spores settling on materials, equipment, packages, and building structures.

### Surface Contamination / CFU

- Unit: `CFU/m2`
- Reported basis: Australian Mould Guidelines AMG-2010-1, as cited in the Smart EA report text.
- Standard levels:
  - Low: `< 25,000 CFU/m2`
  - Moderate: `25,000-125,000 CFU/m2`
  - High: `> 125,000 CFU/m2`
- Meaning: viable mold contamination on a sampled surface.
- Risk logic: high CFU means the sampled object or surface may be a contamination source requiring more attention.

### Mold Contamination Index

- Standard levels:
  - `0-25%`: Low
  - `26-50%`: Medium
  - `51-75%`: Moderate-high
  - `76-100%`: High
- Meaning: YIMS/Smart EA index derived from microbiological parameters on air and objects.
- Comment rule: use YIMS API value; do not recalculate manually.

### Isolate Mold Species

- Current rule: there is no internal high-risk species list or comment rule.
- Comment rule: do not infer risk severity from species names unless Rose later provides a rule table.
- Use case: species can be recorded as factual supplementary information, but should not drive risk ranking.

## Risk Indices

### Environmental Mold Risk

- Standard levels:
  - `0-25%`: Low
  - `26-50%`: Medium
  - `51-75%`: Moderate-high
  - `76-100%`: High
- Meaning: evaluates whether environmental conditions are suitable for mold growth.
- Comment rule: use YIMS API value; do not recalculate manually.

### Overall Mold Risk

- Standard levels:
  - `0-20`: Low Risk
  - `21-40`: Moderate-Low Risk
  - `41-60`: Moderate
  - `61-80`: Moderate-High Risk
  - `81-100`: High Risk
- Meaning: combined risk from environmental, microbiological, and visibility risk analyses.
- Comment rule: use YIMS API value; if visibility risk is not configured, avoid over-explaining visibility factors.

## Interaction Logic

### RH -> Object Moisture -> Mold Growth

High RH increases object moisture. High object moisture provides water for mold growth. If contaminated surfaces are also detected, this chain indicates more immediate risk.

### Outdoor RH + Humidity Permeability -> Indoor RH

High humidity permeability means outdoor humidity strongly affects indoor humidity. When the value is above 100%, indoor moisture has accumulated beyond the outdoor humidity level and is not being removed effectively.

### Low Mold Spore Blow Index + High Spore Infiltration Rate

Low wind force means spores are not removed from surfaces effectively. High spore infiltration means spores remain or accumulate indoors. Together, they increase the chance of spores settling on objects.

### Air Contamination -> Surface Contamination

Airborne spores are the transport path. Surface CFU is evidence that spores have settled or that a surface is already contaminated.

### Surface Contamination + Object Moisture

Surface contamination plus high moisture is higher priority than either alone, because both the contamination source and growth condition are present.

### Environmental Risk + Microbiological Risk

- High environmental + high microbiological risk: contamination exists and conditions support growth. Treat as immediate/high-priority risk.
- High environmental + low microbiological risk: conditions are favorable but contamination is not yet high. Emphasize prevention and monitoring.
- Low environmental + high microbiological risk: contamination source exists but growth conditions may not be favorable. Emphasize cleaning, source removal, and cross-contamination control.

## Overall Comment Rules

- Overall Environmental Comment should synthesize cross-zone common patterns, not repeat the per-zone object lists. It should describe shared abnormal parameters, common moisture/spore-retention mechanisms, and how materials, packages, equipment, and goods may connect Raw Material Warehouse, Production Line, and Finished Goods Warehouse.
- Overall Microbiology Comment should synthesize common microbiological patterns, not repeat all sampled objects and CFU values from the small comments. It should distinguish airborne versus surface contamination, identify recurring contaminated surface types, and explain potential cross-zone transfer through storage, handling, air movement, and product-contact surfaces.
