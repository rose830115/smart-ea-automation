# PYS Case Comment Reference

建立日期：2026-05-13  
用途：保存 PYS 正式報告中的案件數字與評論寫法，作為日後 LLM 生成評論時的實際參考案例。  
來源：`outputs/PYS_official_report_text.txt`

## Overall Environmental Summary

| Parameter | Standard | Raw Material Warehouse | Production Line | Finished Goods Warehouse |
| --- | --- | ---: | ---: | ---: |
| Relative Humidity | <= 60% | 68.2 | 69.9 | 71.3 |
| Humidity Permeability Rate | <= 90% | 100.9 | 103.2 | 106.6 |
| Carbon Dioxide Gas | <= 600 ppm | 485.0 | 439.3 | 554.2 |
| Mold Spore Blow Index | >= 0.4 m/s | 0.7 | 0.3 | 0.3 |
| Spore Infiltration Rate | <= 90% | 94.2 | 221.9 | 189.1 |
| Failed Ratio of Object Moisture | <= 50% | 62.5 | 45.8 | 58.4 |
| Environmental Mold Risk | <= 50% | 61.1 | 60.0 | 75.0 |

Environmental ranking in report: Finished Goods Warehouse highest, Raw Material Warehouse and Production Line lower.

## Raw Material Warehouse - Environmental

### Spatial Parameters

| Area | RH | HPR | CO2 | MSBI | SIR |
| --- | ---: | ---: | ---: | ---: | ---: |
| Area 1 | 64.5 | 95.4 | 443.0 | 1.3 | 68.5 |
| Area 2 | 66.4 | 98.2 | 613.0 | 0.2 | 78.3 |
| Area 3 | 73.7 | 109.0 | 399.0 | 0.8 | 135.9 |

Temperature exists in the report but is reference-only and should not be used in comments.

### Object Moisture

| Item | Average | Maximum | Failed Ratio |
| --- | ---: | ---: | ---: |
| Raw Material | 7.6 | 10.2 | 5.6 |
| Outer packaging | 10.3 | 11.0 | 66.7 |
| Equipment | 13.2 | 14.5 | 100.0 |

### Official Comment Pattern

Risk sources: relative humidity, humidity permeability rate, spore infiltration rate, moisture content.

Key writing points:

- All areas exceeded RH 60%; Area 3 highest at 73.7%.
- High humidity may increase moisture content of leathers, carton boxes, and wooden equipment.
- HPR was high, meaning indoor RH was affected by outdoor RH.
- Area 2 had high CO2, suggesting possible microbiological growth.
- Area 2 had low MSBI, increasing the chance of spores landing on carton boxes.
- Area 3 had high SIR, meaning spores could be carried into the room and increase contamination risk by object contact.

## Production Line - Environmental

### Spatial Parameters

| Area | RH | HPR | CO2 | MSBI | SIR |
| --- | ---: | ---: | ---: | ---: | ---: |
| Area 4 | 75.9 | 112.3 | 503.0 | 0.1 | 63.0 |
| Area 5 | 64.2 | 95.0 | 388.0 | 0.1 | 190.2 |
| Area 6 | 67.6 | 100.0 | 415.3 | 0.4 | 171.7 |
| Area 7 | 68.2 | 100.9 | 423.0 | 0.4 | 435.9 |
| Area 8 | 72.9 | 107.8 | 466.3 | 0.3 | 248.9 |

Temperature exists in the report but is reference-only and should not be used in comments.

### Object Moisture

| Item | Average | Maximum | Failed Ratio |
| --- | ---: | ---: | ---: |
| Raw Material | 8.2 | 13.9 | 33.3 |
| Semi-finished Product | 8.1 | 16.6 | 11.1 |
| Finished Goods | 6.9 | 8.6 | 0.0 |
| Outer packaging | 10.8 | 12.8 | 57.1 |
| Equipment | 13.8 | 19.5 | 100.0 |

### Official Comment Pattern

Main issues: relative humidity, humidity permeability rate, MSBI, SIR. Object moisture content is also a potential source.

Key writing points:

- RH exceeded standard and may increase object moisture.
- Actual objects noted: carton boxes and wooden equipment had failed ratio over 50%; leathers and semi-finished goods also posed high-moisture risk.
- HPR exceeded 90%, meaning outdoor RH had a large effect on indoor RH.
- Areas 4, 5, and 8 had low MSBI, causing spores to accumulate on object surfaces due to insufficient wind.
- Areas 5, 6, and 8 had SIR >90%; Area 7 reached 435.9%.
- Explanation used: wind direction may not carry trapped indoor spores back outside, allowing spores to remain and accumulate indoors.

## Finished Goods Warehouse - Environmental

### Spatial Parameters

| Area | RH | HPR | CO2 | MSBI | SIR |
| --- | ---: | ---: | ---: | ---: | ---: |
| Area 9 | 68.7 | 101.6 | 482.5 | 0.7 | 132.6 |
| Area 10 | 69.1 | 102.2 | 403.0 | 0.2 | 285.9 |
| Area 11 | 71.1 | 105.2 | 693.5 | 0.1 | 181.5 |
| Area 12 | 79.3 | 117.3 | 570.0 | 0.1 | 156.5 |

Temperature exists in the report but is reference-only and should not be used in comments.

### Object Moisture

| Item | Average | Maximum | Failed Ratio |
| --- | ---: | ---: | ---: |
| Finished Goods | 8.2 | 13.1 | 16.7 |
| Outer packaging | 11.7 | 12.2 | 100.0 |
| Equipment | 11.0 | 11.5 | 100.0 |

### Official Comment Pattern

Issues: RH, HPR, MSBI, SIR, moisture content.

Key writing points:

- RH exceeded 60%; Area 12 highest at 79.3%.
- HPR was high, meaning indoor RH was affected by outdoor RH. Since all HPR values exceeded 100%, future comments should also state indoor moisture accumulation.
- Carton boxes, inner boxes, and equipment were over 10% moisture with more than 60% failed ratio.
- High moisture could let mold grow easily; moldy objects can become contamination sources and expose goods to mold risk.
- Finished goods had moisture content above 10%, so product quality risk should be mentioned.
- Area 11 had high CO2, indicating possible mold growth and lower worker comfort.
- All areas had SIR >90%, meaning spores could enter and remain indoors for a long period.
- Low MSBI indicated insufficient ventilation and spore accumulation.

## Overall Environmental Comment Pattern

Official structure:

1. Intro: mold requires suitable environmental conditions.
2. Ranking: FGW highest environmental mold risk; RMW and PL lower.
3. Common factors: RH, HPR, SIR.
4. Moisture explanation: local climate and high humidity caused objects that absorb moisture, such as leather, finished goods, wooden equipment, and carton boxes, to have excessive moisture content.
5. Ventilation explanation: high SIR suggests poor air exchange and potential spore saturation.
6. Product risk: unpacked materials and goods may be exposed to high-spore environments, increasing contamination risk.
7. Conclusion: FGW highest because multiple environmental standards failed; sufficient humidity could support spore germination and eventually affect finished goods quality.

## Microbiological Standards

Air contamination:

- Standard: `< 10,000 cts/m3`

Surface contamination:

- Low: `< 25,000 CFU/m2`
- Moderate: `25,000-125,000 CFU/m2`
- High: `> 125,000 CFU/m2`

## Raw Material Warehouse - Microbiological

### Air Contamination

| Area | Air Contamination |
| --- | ---: |
| Area 1 | 1,323 |
| Area 2 | 1,512 |
| Area 3 | 2,625 |

All areas complied with air contamination standards.

### Surface Contamination

| Area | Object | CFU/m2 | Level |
| --- | --- | ---: | --- |
| Area 1 | Raw material | 10,000 | Low |
| Area 1 | Operating Equipment | 20,000 | Low |
| Area 2 | Outer packaging | 56,667 | Moderate |
| Area 3 | Ventilation and Dehumidification Equipment | 160,000 | High |

### Official Comment Pattern

- Air contamination complied with standards.
- Dehumidifier filters had high surface contamination.
- Contamination on dehumidifier filters may contaminate nearby items with mold spores.
- Carton boxes had moderate contamination.
- Mold spores on carton boxes could be carried to Production Line by adhering to the cardboard surface, indirectly increasing Production Line contamination risk.

## Production Line - Microbiological

### Air Contamination

| Area | Air Contamination |
| --- | ---: |
| Area 4 | 1,218 |
| Area 5 | 3,675 |
| Area 6 | 3,318 |
| Area 7 | 8,421 |
| Area 8 | 4,809 |

All areas complied with air contamination standards.

### Surface Contamination

| Area | Object | CFU/m2 | Level |
| --- | --- | ---: | --- |
| Area 4 | Building structure | 56,667 | Moderate |
| Area 5 | Operating Equipment | 106,667 | Moderate |
| Area 6 | Raw material | 3,333 | Low |
| Area 6 | Outer packaging | 103,333 | Moderate |
| Area 6 | Equipment | 2,076,667 | High |
| Area 6 | Building structure | 1,533,333 | High |
| Area 6 | Operating Equipment | 310,000 | High |
| Area 7 | Semi-finished Goods | 10,000 | Low |
| Area 7 | Equipment | 1,456,667 | High |
| Area 7 | Operating Equipment | 6,667 | Low |
| Area 8 | Semi-finished Goods | 3,333 | Low |
| Area 8 | Finished Goods | 210,000 | High |
| Area 8 | Workers | 33,333 | Moderate |
| Area 8 | Operating Equipment | 180,000 | High |

### Official Comment Pattern

- Air contamination met standards.
- Most objects had moderate to high surface contamination.
- Areas 6 and 7 had the highest surface contamination on walls, lace bags, and racks.
- Area 8 had high contamination on shoes and stitching templates.
- Workers' gloves had mold spores and may be an overlooked issue.
- If raw materials or semi-finished goods contact contaminated equipment during production, spores can attach and increase finished product mold risk.

## Finished Goods Warehouse - Microbiological

### Air Contamination

| Area | Air Contamination |
| --- | ---: |
| Area 9 | 2,562 |
| Area 10 | 5,523 |
| Area 11 | 3,507 |
| Area 12 | 3,024 |

All areas complied with air contamination standards.

### Surface Contamination

| Area | Object | CFU/m2 | Level |
| --- | --- | ---: | --- |
| Area 9 | Finished Goods | 28,350 | Moderate |
| Area 10 | Outer packaging | 33 | Low |
| Area 11 | Workers | 3,333 | Low |
| Area 11 | Others | 256,667 | High |
| Area 12 | Ventilation and Dehumidification Equipment | 153,333 | High |

### Official Comment Pattern

- Air contamination met standards.
- Areas 11 and 12 still had mold contamination index 100% because high surface contamination was detected on charcoal and ventilation/dehumidification equipment such as fans.
- Ventilation and dehumidification equipment can draw in and release surrounding air, dispersing spores across the space during operation.
- Charcoal is often overlooked; if not replaced regularly, absorbed moisture plus nutrients may let spores grow and cross-contaminate finished goods.
- Finished goods in Area 9 had moderate surface contamination.
- Even when air contamination is low, spores on object surfaces can increase mold growth risk during storage.

## Overall Microbiological Comment Pattern

Official structure:

1. Intro: average microbiological contamination shows overall contamination during production.
2. Ranking: Production Line highest, followed by Finished Goods Warehouse, then Raw Material Warehouse.
3. Air contamination: all zones were within standard.
4. Surface contamination: equipment, operating equipment, ventilation and dehumidification equipment were mostly moderate/high risk.
5. Cross-contamination: contaminated equipment surfaces can contaminate raw materials and finished goods during production.
6. Ventilation/dehumidification equipment can spread surface spores into the air.
7. Conclusion: Production Line high risk came from equipment, operating equipment, building structures, and finished goods such as chillers, lace bags, walls, and shoes.

## Overall Mold Risk Comment Pattern

Official values:

- Overall risk range in report: `62.4 to 83.3%`
- Factory overall level: moderate-high

Official structure:

1. Overall mold risk combines environmental and microbiological contamination analysis.
2. Overall risk resulted equally from environmental and microbiological factors.
3. High humidity and moisture can facilitate mold growth, especially on materials with high surface contamination.
4. Finished products made from highly contaminated raw materials can become moldy.
5. Low MSBI and high SIR encourage spores to settle and contaminate objects, potentially increasing future surface contamination.
6. Production Line and Finished Goods Warehouse presented high risks.
7. Mold found on finished shoes indicates contamination can occur during production and be carried into storage, affecting finished product quality.

