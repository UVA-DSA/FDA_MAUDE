# da Vinci Annual Procedure Volumes (2014–2025) — Data Sources

This document lists the sources for the worldwide da Vinci surgical procedure
volumes compiled in [`data/daVinci_Annual_Procedures_2014_2025.csv`](../data/daVinci_Annual_Procedures_2014_2025.csv).

## Summary of extracted data

| Year | Worldwide da Vinci procedures | YoY growth | Primary source |
|------|------------------------------:|:----------:|----------------|
| 2014 | ~570,000   | —          | FY2015 Q4 press release / 10-K |
| 2015 | ~652,000   | ~14%       | FY2015 Q4 press release / 10-K |
| 2016 | ~753,000   | ~15%       | FY2016 Q4 press release / 10-K |
| 2017 | ~877,000   | ~16%       | FY2017 / FY2019 Q4 press release |
| 2018 | ~1,038,000 | ~18%       | FY2018 / FY2019 Q4 press release |
| 2019 | ~1,229,000 | ~18%       | FY2019 Q4 press release |
| 2020 | ~1,243,000 | ~1% (COVID)| FY2020 Q4 press release |
| 2021 | ~1,594,000 | ~28%       | FY2021 / FY2022 Q4 press release |
| 2022 | ~1,875,000 | ~18%       | FY2022 Q4 press release |
| 2023 | ~2,286,000 | ~22%       | FY2023 / FY2024 Q4 press release |
| 2024 | ~2,683,000 | ~17%       | FY2024 Q4 press release |
| 2025 | ~3,153,000 (preliminary) | ~18% | FY2025 Q4 preliminary press release |

## Notes

- Figures are **worldwide** da Vinci procedure counts.
- Values are Intuitive Surgical's own **rounded approximations** ("approximately X"),
  not exact integer counts.
- Numbers are **da Vinci only** — since 2023 Intuitive also reports **Ion** (lung
  biopsy robot) procedures separately, which are excluded here.
- **2025 is preliminary/unaudited** (announced Jan 14, 2026); to be finalized in
  the FY2025 10-K.
- Early-year totals (2014–2017) are cross-checked against the trailing comparatives
  disclosed in later-year press releases.

## Primary sources — Intuitive Surgical Q4 / full-year press releases

- **FY2025 (preliminary, Jan 14, 2026):** https://isrg.intuitive.com/news-releases/news-release-details/intuitive-announces-preliminary-fourth-quarter-and-full-year-5
  - GlobeNewswire mirror: https://www.globenewswire.com/news-release/2026/01/14/3218745/7637/en/Intuitive-Announces-Preliminary-Fourth-Quarter-and-Full-Year-2025-Results.html
- **FY2024:** https://investor.intuitivesurgical.com/news-releases/news-release-details/intuitive-announces-preliminary-fourth-quarter-and-full-year-4
  - SEC Form 8-K (FY2024): https://www.sec.gov/Archives/edgar/data/1035267/000103526725000005/q424ex-991q4prexreleaseq4o.htm
- **FY2022:** https://isrg.intuitive.com/news-releases/news-release-details/intuitive-announces-preliminary-fourth-quarter-and-full-year-2/
  - SEC Form 8-K (FY2022): https://www.sec.gov/Archives/edgar/data/1035267/000103526722000006/a20211231ex-991.htm
- **FY2021:** https://isrg.intuitive.com/news-releases/news-release-details/intuitive-announces-preliminary-fourth-quarter-and-full-year-1/
  - SEC Form 8-K (FY2021): https://www.sec.gov/Archives/edgar/data/1035267/000103526721000008/a20201231ex-991q4prexrelea.htm
- **FY2020:** https://isrg.intuitive.com/news-releases/news-release-details/intuitive-announces-preliminary-fourth-quarter-and-full-year-0
- **FY2019 (SEC 8-K, covers 2017–2019):** https://www.sec.gov/Archives/edgar/data/1035267/000103526719000002/a20181231ex-991q4prerelease.htm
- **FY2017 (SEC 8-K):** https://www.sec.gov/Archives/edgar/data/0001035267/000103526717000004/a20161231ex-991q4prerelease.htm
- **FY2016 (SEC 8-K, covers 2014–2016):** https://www.sec.gov/Archives/edgar/data/0001035267/000103526716000119/a20151231ex-991q4prerelease.htm

## Per-specialty breakdown

Detailed per-specialty volumes are compiled in
[`data/daVinci_Procedures_By_Specialty.csv`](../data/daVinci_Procedures_By_Specialty.csv)
(long format: `year, region, specialty, procedures, source`).

**Important caveat:** Intuitive does **not** publish a complete specialty × region ×
year matrix. Each 10-K discloses absolute volumes only for that year's **largest
specialties** (typically U.S. general surgery, gynecology, urology; and OUS urology,
general surgery, gynecology), usually with 1–2 years of trailing comparatives. Other
specialties and years are given only as growth percentages or qualitative commentary.
The CSV therefore has gaps by design — it contains only figures Intuitive stated
explicitly. It is most complete for 2021–2024.

### U.S. da Vinci procedures by specialty (approximate)

| Year | General surgery | Gynecology | Urology |
|------|----------------:|-----------:|--------:|
| 2016 | ~186,000 | — | — |
| 2017 | ~246,000 | — | — |
| 2018 | ~325,000 | ~265,000 | — |
| 2019 | ~421,000 | ~282,000 | — |
| 2020 | — | ~267,000 | — |
| 2021 | ~588,000 | ~316,000 | ~153,000 |
| 2022 | ~720,000 | ~341,000 | ~162,000 |
| 2023 | ~896,000 | ~390,000 | ~173,000 |
| 2024 | ~1,063,000 | ~423,000 | ~186,000 |

### Outside-U.S. (OUS) da Vinci procedures by specialty (approximate)

| Year | Urology | General surgery | Gynecology |
|------|--------:|----------------:|-----------:|
| 2021 | ~264,000 | ~101,000 | — |
| 2022 | ~316,000 | ~133,000 | — |
| 2023 | ~381,000 | ~188,000 | ~110,000 |
| 2024 | ~435,000 | ~254,000 | ~142,000 |

Regional totals: U.S. total ~1,532,000 (2023) → ~1,757,000 (2024); OUS total is the
worldwide total minus U.S. (~754,000 in 2023 → ~926,000 in 2024).

Sources for specialty figures: Intuitive Surgical 10-K filings (FY2018–FY2024),
"Procedures" / MD&A sections. Growth notes: U.S. general surgery is consistently the
largest and fastest-growing U.S. specialty (driven by hernia repair, colorectal,
cholecystectomy, bariatric); OUS urology (prostatectomy) is the largest OUS specialty.

## 10-K filings (primary source for per-specialty volumes)

- **FY2024 10-K (SEC):** https://www.sec.gov/Archives/edgar/data/1035267/000103526725000017/isrg-20241231.htm
- **FY2023 10-K (SEC):** https://www.sec.gov/Archives/edgar/data/1035267/000103526724000021/isrg-20231231.htm
- **FY2022 10-K (SEC):** https://www.sec.gov/Archives/edgar/data/1035267/000103526723000019/isrg-20221231.htm
- **FY2021 10-K (SEC):** https://www.sec.gov/Archives/edgar/data/1035267/000103526722000014/isrg-20211231.htm
- **FY2020 10-K (SEC):** https://www.sec.gov/Archives/edgar/data/1035267/000103526721000028/isrg-20201231.htm
- **FY2019 10-K (SEC):** https://www.sec.gov/Archives/edgar/data/1035267/000103526720000032/isrg-20191231.htm
- **FY2018 10-K (SEC):** https://www.sec.gov/Archives/edgar/data/1035267/000103526719000012/isrg-20181231x10k.htm

## Annual reports (10-K / ARS)

- **FY2024 10-K (SEC):** https://www.sec.gov/Archives/edgar/data/1035267/000103526725000017/isrg-20241231.htm
- **2025 Annual Report (ARS, SEC):** https://www.sec.gov/Archives/edgar/data/1035267/000103526726000025/a2025_annualreportxv4.pdf
- **2025 Annual Report (Investor Relations):** https://isrg.intuitive.com/static-files/d01bbc25-f8cf-433b-8ebb-b5afc1926236
- **2024 Annual Report (Investor Relations):** https://isrg.intuitive.com/static-files/500ff989-ad91-4b32-a59e-f94a34d75997
- **2023 Annual Report (SEC):** https://www.sec.gov/Archives/edgar/data/1035267/000103526724000118/a2023formarsv3.pdf
- **2019 Annual Report:** https://isrg.gcs-web.com/static-files/31b5c428-1d95-4c01-9c85-a7293bac5e05
- **2016 Annual Report:** https://www.annualreports.com/HostedData/AnnualReportArchive/i/NASDAQ_ISRG_2016.pdf

## Secondary / trade-press corroboration

- The Robot Report — "Intuitive da Vinci procedures increased 17% in 2024": https://www.therobotreport.com/intuitive-da-vinci-procedures-increased-17-in-2024/
- MassDevice — "Intuitive da Vinci procedures increased 17% in 2024": https://www.massdevice.com/intuitive-da-vinci-procedures-increased-2024/

---

*Compiled 2026-07-22. Intuitive Surgical investor relations: https://isrg.intuitive.com*
