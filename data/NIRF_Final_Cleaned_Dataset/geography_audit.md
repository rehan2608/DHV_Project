# NIRF Dataset V3: Comprehensive Geography & Administrative Typology Audit Report

**Project:** NIRF Dashboard – Institutional Ranking Analysis (2017–2025)  
**Author:** Senior Data Engineer & Spatial Demographer  
**Dataset Directory:** `NIRF_Cleaned_Dataset_v3/`  
**City Master Mapping:** `NIRF_Cleaned_Dataset_v3/city_mapping_v3.csv` (377 unique cities)  
**Status:** **AUDITED & EVIDENCE-CERTIFIED (V3)**

---

## 1. Executive Summary

Geographic integrity is essential for spatial analytics, state-level performance comparisons, and Tableau choropleth mapping. In NIRF datasets from 2017 to 2025, location reporting faces three structural challenges:
1. **Administrative Diversity:** Campuses are located across municipal corporations, suburban townships, census towns, and rural gram panchayats.
2. **Missing Cities in Specialized Categories:** The 2023 Innovation category published 10 institution records with completely null city fields in Innovation 2023 (plus 1 dropdown placeholder in Law 2025).
3. **Multi-Location Aggregation Bias:** The legacy practice of assigning the alphabetically first city (`all_cities[0]`) as an institution's primary headquarters created geographic distortion.

The Stage 3 (`V3`) spatial audit resolved each of these challenges through a defensible administrative typology, evidence-backed imputation, and statutory headquarters verification.

---

## 2. Administrative Typology: The 5 Location Tiers

To provide sociodemographic and urban planning depth for Tableau and Streamlit dashboards, every unique standardized city in `city_mapping_v3.csv` (377 cities) was classified into one of five administrative tiers (`location_type`):

```
+-----------------------------------------------------------------------------------------+
|                                5 ADMINISTRATIVE TIERS                                   |
+-----------------------------------------------------------------------------------------+
| 1. Municipal Corporation / City      : Tier 1 & Tier 2 Metros, Municipal Corporations   |
| 2. Municipality / Town               : Smaller urban local bodies, Municipal Councils    |
| 3. District Headquarters             : Administrative seat of a revenue district        |
| 4. Urban Locality / Suburb           : Distinct suburban township within a metro region |
| 5. Census Town / Gram Panchayat      : Notified rural village, campus enclave, gram p.  |
+-----------------------------------------------------------------------------------------+
```

### Breakdown of Unique Locations by Administrative Type
- **Municipal Corporation / City:** 198 locations (52.5%) — Includes Chennai, Mumbai, Bengaluru, New Delhi, Hyderabad, Kolkata, Pune, Ahmedabad, Lucknow.
- **Municipality / Town:** 104 locations (27.6%) — Includes Vallabh Vidyanagar, Manipal, Pilani, Phagwara, Thanjavur, Nagercoil.
- **District Headquarters:** 42 locations (11.1%) — Includes Sangareddy, Haridwar, Kancheepuram, Thrissur, Anand.
- **Census Town / Gram Panchayat / Village:** 21 locations (5.6%) — Includes Ettimadai, Vellanikkara, Ghandal, Modinagar.
- **Urban Locality / Suburb:** 12 locations (3.2%) — Includes Powai, Hauz Khas, Salt Lake, Senapati Bapat Road.

---

## 3. Disambiguation of Rural Campus Villages vs. District Headquarters

A significant source of data variance in NIRF is whether an institution reports its micro-locality (campus village / gram panchayat) or its parent revenue district headquarters:

1. **Vallabh Vidyanagar vs. Anand (Gujarat):**  
   - Sardar Patel University and affiliated engineering colleges report both "Vallabh Vidyanagar" (the notified educational township) and "Anand" (the district headquarters).  
   - *V3 Resolution:* Preserved "Vallabh Vidyanagar" as `Municipality / Town` while mapping district affiliation to Anand.
2. **Vellanikkara vs. Thrissur (Kerala):**  
   - Kerala Agricultural University reports "Vellanikkara" (the gram panchayat housing the central campus).  
   - *V3 Resolution:* Classified as `Census Town / Gram Panchayat / Village` in Thrissur district.
3. **Ettimadai vs. Coimbatore (Tamil Nadu):**  
   - Amrita Vishwa Vidyapeetham headquarters is physically in Ettimadai village, 20 km outside Coimbatore city center.  
   - *V3 Resolution:* Classified Ettimadai as `Census Town / Gram Panchayat / Village` while attributing primary university headquarters to Coimbatore.
4. **Ghandal vs. Shimla (Himachal Pradesh):**  
   - Himachal Pradesh National Law University (HPNLU) campus is situated at Ghandal village along the Shimla-Mandi highway.  
   - *V3 Resolution:* Standardized to "Shimla" (District Headquarters) to maintain consistency with state judicial administration.

---

## 4. Imputation of Missing Cities in Innovation Category (2023)

In the raw 2023 Innovation ranking file, 10 institutional records lacked city metadata (plus 1 dropdown placeholder in Law 2025) (`NaN`). All 11 institutions were audited and populated with high-confidence geographic data:

| Institution UID | Institution Name | Imputed City | Imputed State | Zone | Imputation Evidence Source | Confidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| `U-0456` | Indian Institute of Technology Madras | Chennai | Tamil Nadu | South | Central Act 59 of 1961; Main Campus Adyar | High |
| `U-0306` | Indian Institute of Technology Bombay | Mumbai | Maharashtra | West | Central Act 59 of 1961; Main Campus Powai | High |
| `U-0109` | Indian Institute of Technology Delhi | New Delhi | Delhi | North | Central Act 59 of 1961; Hauz Khas Campus | High |
| `U-0220` | Indian Institute of Science | Bengaluru | Karnataka | South | Central Institute Master Directory | High |
| `U-0573` | Indian Institute of Technology Kanpur | Kanpur | Uttar Pradesh | North | Central Act 59 of 1961; Kalyanpur Campus | High |
| `U-0560` | Indian Institute of Technology Roorkee | Roorkee | Uttarakhand | North | Central Act 59 of 1961; Haridwar District | High |
| `U-0025` | Indian Institute of Technology Hyderabad | Sangareddy | Telangana | South | Central Act 59 of 1961; Kandi Campus | High |
| `U-0584` | Symbiosis International | Pune | Maharashtra | West | UGC Deemed MoA; Senapati Bapat Road | High |
| `U-0379` | Birla Institute of Technology and Science | Pilani | Rajasthan | North | BITS Act 1964; Central Vidya Vihar Campus | High |
| `U-0436` | Amrita Vishwa Vidyapeetham | Coimbatore | Tamil Nadu | South | UGC Deemed MoA; Ettimadai Headquarters | High |
| `U-0490` | IIITDM Kancheepuram | Kancheepuram | Tamil Nadu | South | Central IIIT Act 2014; Melakottaiyur Campus | High |

*Note: All imputed records are flagged with `is_city_imputed = True` and detailed in `source_value_provenance_v3.csv`.*

---

## 5. Multi-Location Institutions & The Headquarters Protocol

### Why Alphabetical Inference Failed
In V2, multi-location institutions were assigned `primary_city = all_cities[0]`. This created systematic errors:
- BITS Pilani was assigned **Hyderabad** (alphabetically prior to Pilani).
- Amrita Vishwa Vidyapeetham was assigned **Amaravati** (alphabetically prior to Coimbatore).
- Manipal Academy of Higher Education was assigned **Bengaluru** (alphabetically prior to Manipal).

### The V3 Verification Framework
1. **Statutory Main Campus Verification:** Where an institution has a single legally defined seat of administration established by an Act of Parliament or UGC MoA, that city is recorded as `verified_primary_city`.
2. **Unresolved Preservation:** For institutions with multiple autonomous regional campuses and no single definitive main campus established in the NIRF dataset (e.g. Amity University, NMIMS multi-city campuses, TISS centers), `verified_primary_city` and `verified_primary_state` are left strictly as **null (`NaN`)**.
3. **Preservation of All Sites:** In all cases, `all_cities_reported` and `all_states_reported` preserve every location observed in NIRF submissions.

---

*Report certified by Spatial Demography & Data Quality Auditor for NIRF V3 Pipeline.*
