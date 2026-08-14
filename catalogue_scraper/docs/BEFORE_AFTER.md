# Before / after comparison

> **Historical — measured 2026-07-31.** This document records the corpus either
> side of the 2026-07-30 contamination fix. Its PASS/REVIEW/FAIL figures are a
> snapshot of that moment and are **not** the current status.
>
> Two things changed afterwards: the 2026-08-13 unit-loss fix (see the README),
> and the audit tool's advisory rules, which stopped flagging resolved WAF
> challenges and short-but-complete programmes as REVIEW. Current status is
> **470 PASS / 0 REVIEW / 0 FAIL** — reproduce it with `tools/audit_corpus.py`.

| Metric | Before (delivered) | After (corrected) | Change |
|---|---|---|---|
| Files produced | 470 | 470 | +0 |
| PASS | 276 | 462 | +186 |
| REVIEW | 36 | 8 | -28 |
| FAIL | 158 | 0 | -158 |
| html contaminated | 158 | 0 | -158 |
| no title heading | 158 | 0 | -158 |
| zero course codes | 99 | 3 | -96 |
| title mismatch | 0 | 0 | +0 |
| duplicate bodies | 0 | 0 | +0 |
| min chars | 951 | 230 | — |
| median chars | 4633.0 | 2745.5 | — |
| mean chars | 5325.9 | 3377.7 | — |
| max chars | 28230 | 19595 | — |
| stdev chars | 3352.4 | 2505.0 | — |

- Files in baseline but not in corrected set: **0**
- Files in corrected set but not in baseline: **0**

## Materially changed files: 187

- **Repaired** (FAIL → clean): 158
- **Regressed** (clean → FAIL): 0  ✓ none
- Other content changes (both clean; USC edits / renderer detail): 29

### Repaired files — reason each was corrected

| file | before chars / codes | after chars / codes | reason it was wrong |
|---|---|---|---|
| 025_astronomy_ba.txt | 3840 / 48 | 1114 / 22 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 026_astronomy_bs.txt | 3624 / 48 | 1272 / 25 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 062_chemistry_ba.txt | 4040 / 0 | 1751 / 24 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 099_earth_sciences_ba.txt | 4088 / 24 | 794 / 10 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 100_east_asian_area_studies_ba.txt | 6264 / 32 | 642 / 4 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 102_economics_ba.txt | 6210 / 112 | 732 / 14 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 103_economics_and_data_science_bs.txt | 5234 / 40 | 1799 / 26 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 105_english_ba.txt | 9506 / 40 | 1156 / 5 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 107_environmental_science_and_health_ba.txt | 4614 / 0 | 1745 / 19 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 112_fine_arts_bfa.txt | 18902 / 0 | 2912 / 10 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 116_gender_and_sexuality_studies_ba.txt | 20388 / 48 | 3139 / 15 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 119_global_geodesign_bs.txt | 11014 / 0 | 2405 / 18 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 121_global_studies_ba.txt | 18814 / 0 | 3162 / 9 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 127_human_development_and_aging_bs.txt | 23116 / 24 | 4005 / 19 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 134_interdisciplinary_studies_ba.txt | 15822 / 0 | 1978 / 0 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 138_italian_ba.txt | 8412 / 16 | 2555 / 28 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 141_journalism_ba.txt | 7414 / 0 | 2270 / 26 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 146_lifespan_health_bs.txt | 18362 / 104 | 2902 / 25 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 147_linguistics_ba.txt | 8190 / 24 | 1476 / 8 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 148_mathematics_ba.txt | 3642 / 8 | 1235 / 16 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 149_mathematics_bs.txt | 7070 / 8 | 1887 / 20 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 176_physical_sciences_bs.txt | 5088 / 32 | 1315 / 13 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 177_physics_ba.txt | 3576 / 32 | 1433 / 23 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 178_physics_bs.txt | 6558 / 56 | 1784 / 26 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 179_physics_computer_science_bs.txt | 4802 / 8 | 1601 / 21 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 180_political_economy_ba.txt | 5054 / 0 | 1418 / 9 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 182_psychology_ba.txt | 8492 / 48 | 2041 / 25 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 184_public_relations_and_advertising_ba.txt | 7638 / 0 | 1546 / 7 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 186_real_estate_development_bs.txt | 24418 / 80 | 3946 / 26 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 189_russian_ba.txt | 1102 / 0 | 660 / 10 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 190_social_sciences_with_an_emphasis_in_economics_ba.txt | 4456 / 64 | 519 / 8 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 191_social_sciences_with_an_emphasis_in_psychology_ba.txt | 3572 / 56 | 412 / 7 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 192_social_work_bsw.txt | 28230 / 0 | 5447 / 13 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 195_spanish_ba.txt | 5258 / 8 | 928 / 3 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 203_economics_mathematics_bs.txt | 7870 / 216 | 927 / 27 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 206_linguistics_and_philosophy_ba.txt | 10112 / 32 | 2320 / 27 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 210_3_dimensional_design_minor.txt | 6920 / 0 | 1423 / 16 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 213_advertising_minor.txt | 9456 / 0 | 1604 / 9 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 215_american_studies_and_ethnicity_minor.txt | 7416 / 0 | 971 / 2 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 217_applied_analytics_minor.txt | 7848 / 8 | 1603 / 17 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 218_arabic_minor.txt | 12984 / 88 | 1749 / 17 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 220_archaeology_of_california_minor.txt | 5848 / 0 | 872 / 5 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 221_architecture_minor.txt | 8432 / 0 | 1113 / 3 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 222_art_history_minor.txt | 6672 / 0 | 1499 / 13 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 223_artificial_intelligence_applications_minor.txt | 10616 / 16 | 1771 / 12 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 226_astronomy_minor.txt | 2960 / 0 | 793 / 10 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 227_behavioral_economics_minor.txt | 6480 / 0 | 1098 / 9 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 229_biology_of_human_movement_minor.txt | 5912 / 0 | 1345 / 13 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 232_blockchain_minor.txt | 6688 / 0 | 972 / 8 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 235_business_law_minor.txt | 9608 / 0 | 1441 / 6 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 237_business_technology_fusion_minor.txt | 3728 / 0 | 989 / 10 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 238_ceramics_minor.txt | 10256 / 0 | 1493 / 9 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 239_chemistry_minor.txt | 5472 / 24 | 1057 / 14 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 240_chinese_for_the_professions_minor.txt | 8944 / 40 | 1669 / 17 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 242_cinema_television_for_the_health_professions_minor.txt | 7072 / 0 | 1652 / 17 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 244_classical_greek_minor.txt | 3136 / 8 | 253 / 1 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 246_classics_minor.txt | 4928 / 0 | 966 / 9 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 248_comedy_performance_minor.txt | 6296 / 0 | 1776 / 24 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 253_comparative_literature_minor.txt | 4856 / 0 | 941 / 4 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 260_consumer_behavior_interdisciplinary_minor.txt | 4704 / 0 | 447 / 0 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 267_cultural_anthropology_minor.txt | 10142 / 0 | 1674 / 6 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 284_drawing_minor.txt | 7982 / 0 | 1445 / 10 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 287_east_asian_area_studies_minor.txt | 6140 / 16 | 738 / 2 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 289_economics_minor.txt | 13328 / 192 | 1630 / 24 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 290_education_and_society_minor.txt | 7774 / 0 | 1198 / 4 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 291_education_policy_minor.txt | 7966 / 0 | 1386 / 7 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 294_english_minor.txt | 4970 / 16 | 505 / 2 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 298_environmental_chemistry_and_sustainability_minor.txt | 5696 / 0 | 1256 / 12 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 299_environmental_health_minor.txt | 5506 / 0 | 893 / 5 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 300_environmental_studies_minor.txt | 2218 / 0 | 607 / 6 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 301_evolutionary_health_and_medicine_minor.txt | 6194 / 0 | 1063 / 7 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 306_food_journalism_and_public_relations_minor.txt | 7090 / 0 | 1605 / 15 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 309_foundations_of_data_science_minor.txt | 6592 / 0 | 1503 / 14 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 317_gender_and_sexuality_studies_minor.txt | 10122 / 72 | 1625 / 16 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 318_gender_and_social_justice_minor.txt | 6586 / 0 | 1340 / 14 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 320_geodesign_minor.txt | 11064 / 0 | 1670 / 7 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 322_german_studies_minor.txt | 3802 / 8 | 1613 / 24 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 326_global_health_minor.txt | 6482 / 0 | 1033 / 7 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 327_health_administration_minor.txt | 4072 / 0 | 1086 / 11 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 329_health_communication_minor.txt | 5736 / 0 | 1726 / 22 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 331_health_policy_minor.txt | 4296 / 0 | 1081 / 12 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 334_history_minor.txt | 9504 / 8 | 1048 / 1 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 335_human_disease_minor.txt | 7184 / 0 | 1403 / 12 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 336_human_performance_and_ai_in_sports_analytics_minor.txt | 6602 / 0 | 1126 / 7 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 337_human_resource_management_minor.txt | 6154 / 0 | 1079 / 7 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 341_individuals_societies_and_aging_minor.txt | 5114 / 0 | 1042 / 9 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 342_intermedia_arts_minor.txt | 6322 / 0 | 1250 / 9 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 345_international_relations_minor.txt | 5074 / 16 | 518 / 2 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 346_internet_of_things_engineering_minor.txt | 7258 / 16 | 1204 / 9 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 349_jazz_studies_minor.txt | 4706 / 0 | 991 / 10 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 352_jewish_studies_minor.txt | 4266 / 16 | 418 / 2 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 353_judaic_studies_minor.txt | 7706 / 80 | 848 / 10 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 355_korean_studies_minor.txt | 7402 / 24 | 1795 / 21 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 356_landscape_architecture_minor.txt | 9944 / 0 | 1786 / 11 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 358_latin_minor.txt | 2754 / 8 | 230 / 1 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 360_law_and_biopharmaceutical_sciences_minor.txt | 7464 / 0 | 1759 / 16 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 361_law_and_government_minor.txt | 5064 / 0 | 1545 / 21 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 362_law_and_innovation_minor.txt | 5448 / 0 | 1822 / 21 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 364_law_and_public_health_minor.txt | 9392 / 0 | 1826 / 15 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 365_law_and_public_policy_minor.txt | 7680 / 8 | 1464 / 17 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 366_law_and_regulation_of_artificial_intelligence_minor.txt | 5864 / 0 | 1434 / 15 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 369_law_and_technology_minor.txt | 4928 / 0 | 1148 / 11 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 370_law_advocacy_and_persuasive_performance_minor.txt | 5688 / 0 | 1608 / 20 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 372_lgbtq_studies_minor.txt | 5512 / 40 | 1339 / 19 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 373_linguistics_minor.txt | 3010 / 0 | 761 / 9 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 376_management_consulting_minor.txt | 5216 / 0 | 1211 / 13 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 379_marketing_minor.txt | 8168 / 8 | 883 / 1 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 380_materials_science_minor.txt | 6944 / 16 | 1233 / 10 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 383_mathematics_minor.txt | 4034 / 0 | 1178 / 15 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 392_music_production_minor.txt | 8218 / 24 | 1959 / 21 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 393_music_recording_minor.txt | 9762 / 40 | 1872 / 19 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 394_musical_studies_minor.txt | 3818 / 0 | 623 / 4 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 395_musical_theatre_minor.txt | 6600 / 16 | 1432 / 17 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 396_nanotechnology_minor.txt | 7208 / 0 | 1701 / 17 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 398_native_american_studies_minor.txt | 5968 / 0 | 1220 / 10 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 399_natural_science_minor.txt | 6722 / 0 | 1445 / 11 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 401_news_media_and_society_minor.txt | 8192 / 0 | 1571 / 11 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 402_nonprofits_philanthropy_and_volunteerism_interdisciplinary_minor.txt | 3408 / 0 | 285 / 0 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 403_nonprofits_philanthropy_and_volunteerism_minor.txt | 10824 / 0 | 1792 / 9 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 404_nutrition_and_health_promotion_minor.txt | 7544 / 0 | 1388 / 11 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 406_operations_and_supply_chain_management_minor.txt | 4962 / 0 | 1519 / 15 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 407_organizational_leadership_and_management_minor.txt | 5342 / 0 | 1339 / 13 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 408_painting_minor.txt | 8080 / 0 | 1304 / 9 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 409_paleontology_minor.txt | 8794 / 0 | 1640 / 10 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 413_performing_social_change_minor.txt | 4906 / 0 | 1311 / 15 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 414_petroleum_engineering_minor.txt | 5042 / 0 | 1158 / 11 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 418_photography_minor.txt | 7000 / 0 | 1343 / 10 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 419_physics_minor.txt | 2858 / 0 | 881 / 11 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 420_plastics_sustainability_minor.txt | 7936 / 16 | 1479 / 13 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 421_podcasting_minor.txt | 7568 / 0 | 1746 / 17 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 423_political_science_minor.txt | 13544 / 40 | 1555 / 5 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 424_popular_music_studies_minor.txt | 4018 / 0 | 1104 / 12 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 427_professional_and_managerial_communication_minor.txt | 7688 / 0 | 1655 / 15 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 428_psychiatry_and_behavioral_sciences_minor.txt | 5162 / 0 | 1039 / 8 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 429_psychology_and_law_minor.txt | 9746 / 32 | 1945 / 22 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 430_psychology_minor.txt | 3682 / 16 | 537 / 3 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 431_public_health_minor.txt | 7448 / 0 | 1592 / 15 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 432_public_relations_minor.txt | 5864 / 8 | 840 / 4 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 434_real_estate_development_minor.txt | 4594 / 0 | 1434 / 18 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 436_religion_minor.txt | 4370 / 8 | 432 / 1 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 440_russian_minor.txt | 5202 / 128 | 535 / 16 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 442_science_health_and_aging_minor.txt | 5314 / 16 | 1122 / 12 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 444_sculpture_minor.txt | 7248 / 0 | 1078 / 8 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 446_social_work_and_juvenile_justice_minor.txt | 6610 / 0 | 1046 / 5 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 449_south_asian_studies_minor.txt | 6250 / 0 | 1936 / 24 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 450_southeast_asia_and_its_people_minor.txt | 7562 / 0 | 1660 / 16 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 451_spanish_minor.txt | 5290 / 8 | 748 / 3 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 455_sports_law_minor.txt | 4408 / 0 | 1052 / 13 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 457_sports_media_studies_minor.txt | 6842 / 0 | 1335 / 12 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 459_stem_cell_biology_and_regenerative_medicine_minor.txt | 8818 / 0 | 1631 / 10 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 460_substance_abuse_prevention_minor.txt | 5690 / 0 | 1089 / 8 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 462_technical_game_art_minor.txt | 5512 / 0 | 993 / 8 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 464_technology_entrepreneurship_minor.txt | 9496 / 0 | 1746 / 12 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 465_theatre_minor.txt | 5986 / 0 | 1223 / 12 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 468_two_dimensional_studies_minor.txt | 6962 / 0 | 1441 / 14 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 469_urban_sustainable_planning_minor.txt | 9722 / 0 | 1711 / 11 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 471_video_game_production_minor.txt | 4290 / 0 | 1702 / 23 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |
| 475_web_development_minor.txt | 6410 / 0 | 1067 / 8 | skip_to_navigation,table_row_label,usc_header_cell,responsive_markers, |

### Other changed files (sample)

| file | before chars | after chars | before status | after status |
|---|---|---|---|---|
| 055_business_of_innovation_bs.txt | 9480 | 9480 | PASS | PASS |
| 056_central_european_studies_ba.txt | 3865 | 4178 | REVIEW | PASS |
| 110_environmental_studies_bs.txt | 10734 | 10969 | REVIEW | PASS |
| 158_narrative_studies_ba.txt | 10014 | 10731 | PASS | PASS |
| 159_neuroscience_ba.txt | 4963 | 6464 | PASS | PASS |
| 212_addiction_science_minor.txt | 3286 | 3136 | PASS | REVIEW |
| 261_consumer_behavior_minor.txt | 4737 | 5134 | REVIEW | PASS |
| 262_contemplative_studies_minor.txt | 2046 | 2244 | REVIEW | PASS |
| 263_craniofacial_and_dental_technology_minor.txt | 2345 | 2491 | REVIEW | PASS |
| 264_creating_dramatic_writing_content_minor.txt | 1003 | 1111 | REVIEW | PASS |
| 265_creative_leadership_minor.txt | 1224 | 1407 | PASS | PASS |
| 266_creator_arts_minor.txt | 1287 | 1386 | REVIEW | PASS |
| 268_cultural_competence_in_medicine_minor.txt | 1342 | 1459 | PASS | PASS |
| 269_cultural_diplomacy_minor.txt | 2334 | 2559 | REVIEW | PASS |
| 270_culture_media_and_entertainment_minor.txt | 2577 | 2802 | PASS | PASS |
| 271_cultures_and_politics_of_the_pacific_rim_minor.txt | 3708 | 4207 | REVIEW | PASS |
| 272_customer_analytics_minor.txt | 2822 | 3013 | REVIEW | PASS |
| 273_cyber_governance_minor.txt | 951 | 1041 | REVIEW | PASS |
| 274_cybersecurity_minor.txt | 1125 | 1233 | PASS | PASS |
| 276_dance_minor.txt | 3007 | 3709 | REVIEW | PASS |
| 277_designing_for_digital_experiences_minor.txt | 1572 | 1689 | PASS | PASS |
| 278_designing_products_minor.txt | 1892 | 1964 | PASS | PASS |
| 279_digital_forensics_minor.txt | 1086 | 1158 | PASS | PASS |
| 280_digital_studies_minor.txt | 3549 | 3907 | REVIEW | PASS |
| 281_directing_minor.txt | 1187 | 1313 | PASS | PASS |
| 282_disruptive_innovation_minor.txt | 2259 | 2385 | PASS | PASS |
| 283_documentary_minor.txt | 971 | 1043 | PASS | PASS |
| 285_dynamics_in_workplace_communication_minor.txt | 2287 | 2411 | REVIEW | PASS |
| 288_east_asian_languages_and_cultures_minor.txt | 4652 | 5117 | PASS | PASS |

## Five smallest / largest, after correction

Smallest: 358_latin_minor.txt (230, REVIEW), 244_classical_greek_minor.txt (253, REVIEW), 402_nonprofits_philanthropy_and_volunteerism_interdisciplinary_minor.txt (285, REVIEW), 191_social_sciences_with_an_emphasis_in_psychology_ba.txt (412, PASS), 352_jewish_studies_minor.txt (418, PASS)

Largest: 124_history_ba.txt (19595, PASS), 169_performance_violin_viola_violoncello_double_bass_or_bm.txt (15370, PASS), 023_arts_technology_and_the_business_of_innovation_bs.txt (14192, PASS), 079_cognitive_science_ba.txt (13770, PASS), 135_international_relations_ba.txt (12246, PASS)
