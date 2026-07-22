# da Vinci Annual Procedure Volumes — Data Sources

Worldwide da Vinci surgical procedure volumes compiled in [`data/daVinci_Annual_Procedures.csv`](../data/daVinci_Annual_Procedures.csv).

**This file is generated** by [`src/fetch_procedure_data.py`](../src/fetch_procedure_data.py), which extracts each fiscal year's total directly from Intuitive Surgical's SEC 10-K filings (EDGAR, CIK 0001035267).

## Notes

- Figures are **worldwide** da Vinci procedure counts, as Intuitive's own rounded approximations ("approximately N").
- **da Vinci only** — Ion (lung-biopsy robot) procedures, reported separately since 2023, are excluded.
- Each value is the total stated in that year's own 10-K (not a later filing's restated comparative).
- **2004–2007** are not disclosed as annual totals in Intuitive's filings; they are filled from the Alemzadeh et al. (2016, PLOS ONE) study estimates and labeled as such.

## Summary

| Year | Worldwide da Vinci procedures | YoY | Source |
|------|------------------------------:|:---:|--------|
| 2004 | 15,625 | — | Study estimate |
| 2005 | 21,052 | 35% | Study estimate |
| 2006 | 42,105 | 100% | Study estimate |
| 2007 | 71,052 | 69% | Study estimate |
| 2008 | 136,000 | 91% | [FY2008 10-K](https://www.sec.gov/Archives/edgar/data/1035267/000119312509021360/d10k.htm) |
| 2009 | 205,000 | 51% | [FY2009 10-K](https://www.sec.gov/Archives/edgar/data/1035267/000119312510016932/d10k.htm) |
| 2010 | 278,000 | 36% | [FY2010 10-K](https://www.sec.gov/Archives/edgar/data/1035267/000119312511020229/d10k.htm) |
| 2011 | 360,000 | 29% | [FY2011 10-K](https://www.sec.gov/Archives/edgar/data/1035267/000119312512039226/d263902d10k.htm) |
| 2012 | 450,000 | 25% | [FY2012 10-K](https://www.sec.gov/Archives/edgar/data/1035267/000119312513036675/d445195d10k.htm) |
| 2013 | 523,000 | 16% | [FY2013 10-K](https://www.sec.gov/Archives/edgar/data/1035267/000103526714000009/isrg-20131231x10k.htm) |
| 2014 | 570,000 | 9% | [FY2014 10-K](https://www.sec.gov/Archives/edgar/data/1035267/000103526715000014/isrg-20141231x10k.htm) |
| 2015 | 652,000 | 14% | [FY2015 10-K](https://www.sec.gov/Archives/edgar/data/1035267/000103526716000130/isrg-20151231x10k.htm) |
| 2016 | 753,000 | 15% | [FY2016 10-K](https://www.sec.gov/Archives/edgar/data/1035267/000103526717000021/isrg-20161231x10k.htm) |
| 2017 | 877,000 | 16% | [FY2017 10-K](https://www.sec.gov/Archives/edgar/data/1035267/000103526718000013/isrg-20171231x10k.htm) |
| 2018 | 1,037,000 | 18% | [FY2018 10-K](https://www.sec.gov/Archives/edgar/data/1035267/000103526719000012/isrg-20181231x10k.htm) |
| 2019 | 1,229,000 | 19% | [FY2019 10-K](https://www.sec.gov/Archives/edgar/data/1035267/000103526720000032/isrg-20191231.htm) |
| 2020 | 1,243,000 | 1% | [FY2020 10-K](https://www.sec.gov/Archives/edgar/data/1035267/000103526721000028/isrg-20201231.htm) |
| 2021 | 1,594,000 | 28% | [FY2021 10-K](https://www.sec.gov/Archives/edgar/data/1035267/000103526722000014/isrg-20211231.htm) |
| 2022 | 1,875,000 | 18% | [FY2022 10-K](https://www.sec.gov/Archives/edgar/data/1035267/000103526723000019/isrg-20221231.htm) |
| 2023 | 2,286,000 | 22% | [FY2023 10-K](https://www.sec.gov/Archives/edgar/data/1035267/000103526724000021/isrg-20231231.htm) |
| 2024 | 2,683,000 | 17% | [FY2024 10-K](https://www.sec.gov/Archives/edgar/data/1035267/000103526725000017/isrg-20241231.htm) |
| 2025 | 3,153,000 | 18% | [FY2025 10-K](https://www.sec.gov/Archives/edgar/data/1035267/000103526726000010/isrg-20251231.htm) |

## Provenance (extracted snippets)

- **2004** — H. Alemzadeh et al., "Adverse Events in Robotic Surgery," PLOS ONE, 2016 (study estimate; annual total not disclosed in Intuitive SEC filings)
- **2005** — H. Alemzadeh et al., "Adverse Events in Robotic Surgery," PLOS ONE, 2016 (study estimate; annual total not disclosed in Intuitive SEC filings)
- **2006** — H. Alemzadeh et al., "Adverse Events in Robotic Surgery," PLOS ONE, 2016 (study estimate; annual total not disclosed in Intuitive SEC filings)
- **2007** — H. Alemzadeh et al., "Adverse Events in Robotic Surgery," PLOS ONE, 2016 (study estimate; annual total not disclosed in Intuitive SEC filings)
- **2008** — SEC 10-K (FY2008), filed 2009-02-06
  - https://www.sec.gov/Archives/edgar/data/1035267/000119312509021360/d10k.htm
  - > …d successfully completed approximately 136,000 surgical procedures of various types in major hospitals throughout North America, South America, E…
- **2009** — SEC 10-K (FY2009), filed 2010-01-29
  - https://www.sec.gov/Archives/edgar/data/1035267/000119312510016932/d10k.htm
  - > …our technology completed approximately 205,000 surgical procedures of various types in major hospitals throughout the world. Out of those da Vinc…
- **2010** — SEC 10-K (FY2010), filed 2011-02-01
  - https://www.sec.gov/Archives/edgar/data/1035267/000119312511020229/d10k.htm
  - > …ded December 31, 2009. • Approximately 278,000 da Vinci procedures were performed during the year ended December 31, 2010, up approximately 35% f…
- **2011** — SEC 10-K (FY2011), filed 2012-02-06
  - https://www.sec.gov/Archives/edgar/data/1035267/000119312512039226/d263902d10k.htm
  - > …our technology completed approximately 360,000 surgical procedures of various types in major hospitals throughout the world. Of those da Vinci pr…
- **2012** — SEC 10-K (FY2012), filed 2013-02-04
  - https://www.sec.gov/Archives/edgar/data/1035267/000119312513036675/d445195d10k.htm
  - > …our technology completed approximately 450,000 surgical procedures of various types in hospitals throughout the world. Of those da Vinci procedur…
- **2013** — SEC 10-K (FY2013), filed 2014-02-03
  - https://www.sec.gov/Archives/edgar/data/1035267/000103526714000009/isrg-20131231x10k.htm
  - > …our technology completed approximately 523,000 surgical procedures of various types in hospitals throughout the world. Of those da Vinci procedur…
- **2014** — SEC 10-K (FY2014), filed 2015-02-06
  - https://www.sec.gov/Archives/edgar/data/1035267/000103526715000014/isrg-20141231x10k.htm
  - > …our technology completed approximately 570,000 surgical procedures of various types in hospitals throughout the world during the year ended Decem…
- **2015** — SEC 10-K (FY2015), filed 2016-02-02
  - https://www.sec.gov/Archives/edgar/data/1035267/000103526716000130/isrg-20151231x10k.htm
  - > …our technology completed approximately 652,000 surgical procedures of various types in hospitals throughout the world during the year ended Decem…
- **2016** — SEC 10-K (FY2016), filed 2017-02-06
  - https://www.sec.gov/Archives/edgar/data/1035267/000103526717000021/isrg-20161231x10k.htm
  - > …our technology completed approximately 753,000 surgical procedures of various types in hospitals throughout the world during the year ended Decem…
- **2017** — SEC 10-K (FY2017), filed 2018-02-02
  - https://www.sec.gov/Archives/edgar/data/1035267/000103526718000013/isrg-20171231x10k.htm
  - > …our technology completed approximately 877,000 surgical procedures of various types in hospitals throughout the world during the year ended Decem…
- **2018** — SEC 10-K (FY2018), filed 2019-02-04
  - https://www.sec.gov/Archives/edgar/data/1035267/000103526719000012/isrg-20181231x10k.htm
  - > …our technology completed approximately 1,037,000 surgical procedures of various types in hospitals throughout the world during the year ended Dec…
- **2019** — SEC 10-K (FY2019), filed 2020-02-07
  - https://www.sec.gov/Archives/edgar/data/1035267/000103526720000032/isrg-20191231.htm
  - > …our technology completed approximately 1,229,000 surgical procedures of various types in hospitals throughout the world during the year ended Dec…
- **2020** — SEC 10-K (FY2020), filed 2021-02-10
  - https://www.sec.gov/Archives/edgar/data/1035267/000103526721000028/isrg-20201231.htm
  - > …our technology completed approximately 1,243,000 surgical procedures of various types in hospitals throughout the world during the year ended Dec…
- **2021** — SEC 10-K (FY2021), filed 2022-02-03
  - https://www.sec.gov/Archives/edgar/data/1035267/000103526722000014/isrg-20211231.htm
  - > …our technology completed approximately 1,594,000 surgical procedures of various types in hospitals throughout the world during the year ended Dec…
- **2022** — SEC 10-K (FY2022), filed 2023-02-10
  - https://www.sec.gov/Archives/edgar/data/1035267/000103526723000019/isrg-20221231.htm
  - > …our technology completed approximately 1,875,000 surgical procedures of various types in hospitals throughout the world during the year ended Dec…
- **2023** — SEC 10-K (FY2023), filed 2024-01-31
  - https://www.sec.gov/Archives/edgar/data/1035267/000103526724000021/isrg-20231231.htm
  - > …our technology completed approximately 2,286,000 surgical procedures of various types in hospitals throughout the world during the year ended Dec…
- **2024** — SEC 10-K (FY2024), filed 2025-01-31
  - https://www.sec.gov/Archives/edgar/data/1035267/000103526725000017/isrg-20241231.htm
  - > …our technology completed approximately 2,683,000 surgical procedures of various types in hospitals throughout the world during the year ended Dec…
- **2025** — SEC 10-K (FY2025), filed 2026-02-03
  - https://www.sec.gov/Archives/edgar/data/1035267/000103526726000010/isrg-20251231.htm
  - > …ded December 31, 2024. • Approximately 3,153,000 da Vinci procedures were performed during the year ended December 31, 2025, an increase of 18% c…
