# Repeatability check

> **Sample size, stated plainly:** this compares **60** of the 470 programmes,
> not the whole corpus. A separate 5-programme check on 2026-08-13 (the
> browser-rendered set, re-acquired after the unit-loss fix) also returned
> byte-identical content, 5/5. Determinism across all 470 has not been measured.

- Run A: `catalogue_scraper/data/usc_undergrad_complete_catalogue_2026_2027/programs` (470 files)
- Run B: a second, independent live run of the same 60 programmes (separate output folder)
- Files compared (present in both): **60**
- **Byte-identical substantive content: 60/60**
- Differing: 0

No differences. Extraction is deterministic for unchanged source pages.

Files only in A: 061_chemical_engineering_petroleum_and_subsurface_engineering_emphasis_bs.txt, 062_chemistry_ba.txt, 063_chemistry_bs.txt, 064_chemistry_bs.txt, 065_chemistry_bs.txt, 066_chemistry_bs.txt, 067_choral_music_ba.txt, 068_choral_music_bm.txt, 069_cinema_and_media_studies_ba.txt, 070_cinematic_arts_film_and_television_production_ba.txt, 071_cinematic_arts_film_and_television_production_bfa.txt, 072_civil_engineering_bs.txt, 073_civil_engineering_building_science_emphasis_bs.txt, 074_civil_engineering_construction_engineering_and_management_emphasis_bs.txt, 075_civil_engineering_environmental_engineering_emphasis_bs.txt, 076_civil_engineering_structural_engineering_emphasis_bs.txt, 077_civil_engineering_water_resources_engineering_emphasis_bs.txt, 078_classics_ba.txt, 079_cognitive_science_ba.txt, 080_communication_ba.txt

Files only in B: none
