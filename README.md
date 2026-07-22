# FDA MAUDE — Safety Analysis of Robotic Surgical Systems

Automated collection of adverse-event reports related to robotic surgical
systems from the **FDA MAUDE** database, and extraction of safety-related
information from the free-text event narratives.

This code accompanies the following publications:

- H. Alemzadeh, J. Raman, N. Leveson, R. K. Iyer, *"Safety Implications of
  Robotic Surgery: A Study of 13 Years of FDA Data on da Vinci Surgical
  Systems,"* CSL Technical Report, Nov. 2013.
  <http://web.engr.illinois.edu/~alemzad1/papers/UILU-ENG-13-2208.pdf>
- J. Maxwell Chamberlain Memorial Paper in Adult Cardiac Surgery, 50th Annual
  Meeting of the Society of Thoracic Surgeons (STS), Jan. 2014.
- H. Alemzadeh, R. K. Iyer, Z. T. Kalbarczyk, N. Leveson, J. Raman, *"Adverse
  Events in Robotic Surgery: A Retrospective Study of 14 Years of FDA Data,"*
  PLOS ONE.
  <http://journals.plos.org/plosone/article?id=10.1371/journal.pone.0151470>

> **Note on the port.** The analysis code was originally written for **Python 2**
> (2013–2015). It has been ported to **Python 3** and reorganized. The logic is
> preserved; deprecated libraries (`urllib2`, `cookielib`, old `BeautifulSoup`,
> `xlrd`/`xlwt` cell APIs, `DataFrame.ix`/`.sort`, `scipy.polyfit`) were replaced
> with their modern equivalents. Because the pipeline depends on large FDA data
> downloads, NLTK models, and network access, please re-run and validate the
> outputs against the published tables before relying on them.

## Repository layout

```
FDA_MAUDE/
├── README.md
├── LICENSE                     # GPL-3.0
├── requirements.txt
├── src/                        # Python 3 pipeline
│   ├── download_maude_openfda.py# 1. pull da Vinci reports via the openFDA API (recommended)
│   ├── download_maude_data.py  #  1-alt. bulk-dump + per-report HTML scraping (legacy)
│   ├── classify_malfunctions.py#  2. classify malfunctions & impacts from text
│   ├── event_arrival_times.py  #  3. reliability / time-between-failure analysis
│   ├── fetch_procedure_data.py #     scrape annual da Vinci procedure counts (SEC EDGAR)
│   ├── malfunctions.py         #  4. statistics, paper tables, Venn counts (pandas)
│   ├── malfunctions.R          #     original R version of step 4
│   └── negex.py                #     NegEx negation-detection helper
├── data/                       # merged MAUDE data + classified spreadsheets
│   ├── daVinci_MAUDE_Data_2013.csv / .xls
│   ├── daVinci_MAUDE_Classified_2000_2013.xls
│   ├── Pre_daVinci_Impacts_2013.csv
│   └── Injuries_Malfunctions.csv
├── dictionaries/               # lookup tables used by the classifier
│   ├── Surgery_Class_Dictionary.csv
│   ├── MDR_Key_Surgery_Class_Dictionary.csv
│   └── negex_triggers.txt      # NegEx negation trigger rules
└── output/                     # generated tables, figures, intermediates (git-ignored)
```

## Setup

```bash
# 1. Create an environment (Python 3.9+ recommended) and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Download the NLTK tokenizer used by the classifier
python -m nltk.downloader punkt
```

### NegEx negation detection

`classify_malfunctions.py` loads NegEx trigger rules from
`dictionaries/negex_triggers.txt` (included) and uses them as a **supplementary
negation check** on top of its hand-written `negation_check` heuristic: a
keyword mention is treated as negated if either the heuristic *or* NegEx flags
it. Set `USE_NEGEX = False` at the top of the script to fall back to the
heuristic alone. If the trigger file is absent, the classifier still runs on
the heuristic only.

## Pipeline

All scripts resolve their input/output paths relative to the repository root,
so they can be run from anywhere. Run them in order:

| Step | Command | Purpose |
|------|---------|---------|
| 1 | `python src/download_maude_openfda.py` | **Recommended.** Pull every Intuitive/da Vinci adverse-event report (with narratives) from the openFDA `device/event` API and write `data/daVinci_MAUDE_Data_<END_YEAR>.csv` + `daVinci_MAUDE_Times_<END_YEAR>.csv`. ~99k reports for 2014–2025 in minutes. By default it **also downloads the DEVICE/MDRFOI bulk dumps** (several GB on first run) to fill the two dates the API lacks (`Manufacture Year`/`Time_to_Event` and the real `DATE_REPORT_TO_MANUFACTURER`) and to **cross-verify** every other date and name field against the local files (agreement summary printed per run); `--skip-local` restores the pure-API behavior. `--scope=davinci` keeps only reports whose device names mention da Vinci; the default `--scope=all` also keeps Intuitive's instrument/accessory brands (EndoWrist etc. — ~5× more reports in instrument-heavy years). Neither scope exactly reproduces the committed 2000–2013 selection; see the script docstring for the validated 2013 comparison. `--require-intuitive` additionally drops the small tail of reports without an Intuitive manufacturer on file (voluntary reports, OEM accessories); by default they are kept and itemized in the run summary. |
| 1 (alt) | `python src/download_maude_data.py` | Bulk-dump route with the **same interface and outputs** as the openFDA script (`--scope`, `--require-intuitive`, Data + Times CSVs; also a legacy `.xls`, capped at 65,536 rows): downloads the FDA DEVICE/MDRFOI dumps (~5 GB), keeps all Intuitive reports **including instrument/accessory events**, then scrapes each report's narrative from the MAUDE website (~0.5 s/report — many hours at 2014–2025 volumes). Its Times CSV includes the real `DEVICE_DATE_OF_MANUFACTURE`, which openFDA does not expose. |
| 2 | `python src/classify_malfunctions.py` | Classify each report's malfunction type and impact from its Event/Narrative text; write `output/daVinci_MDR_Malfunction_Impacts_<END_YEAR>_PLOS_One.csv` and `data/daVinci_MAUDE_Classified_<END_YEAR>.xls`. |
| 3 | `python src/event_arrival_times.py` | Compute time-between-failure, mean inter-arrival time, and the Laplace trend test; render the cumulative-malfunction figures into `output/`. |
| 4 | `python src/malfunctions.py` | Produce the paper's summary tables (`output/Table1.csv`, `Table3.csv`), the malfunction subsets, and the Venn combination-count tables. A pandas port of the R script below — this is the recommended option. |
| 4 (alt) | `Rscript src/malfunctions.R` | Original R version of step 4. Produces the same tables plus Venn diagrams; requires the R package `limma`. |

### Choosing the analysis window (2014–2025 vs. the original 2000–2013)

The pipeline is currently configured for **2014–2025**. Each step reads a
`START_YEAR` / `END_YEAR` (or `end_year`) constant near the top of its file, and
the filenames are derived from it, so the four steps stay in sync as long as the
years match:

- `src/download_maude_data.py` → `START_YEAR = 2014`, `END_YEAR = 2025`, `CURRENT_YEAR = 2026`
- `src/classify_malfunctions.py` → `END_YEAR = 2025`
- `src/event_arrival_times.py` → `START_YEAR = 2014`, `END_YEAR = 2025`
- `src/malfunctions.py` and `src/malfunctions.R` → `END_YEAR = 2025`

To reproduce the original study on the committed dataset instead, set these back
to `START_YEAR = 2000` / `END_YEAR = 2013`.

> ⚠️ **Verify before a 2014–2025 run — FDA field numbers.** The FDA changed the
> DEVICE/MDRFOI column order around 2009. `download_maude_data.py` ships both the
> pre-2009 and the current layouts (`*_PRE2009` vs `*_CURRENT`) and uses the
> current one; confirm the field numbers still match the files you download (the
> FDA MAUDE download page documents the current layout).
>
> **Procedure counts (`event_arrival_times.py`).** Per-procedure normalization
> loads the real annual da Vinci volumes from
> `data/daVinci_Annual_Procedures.csv` whenever they cover the analysis window,
> falling back to the built-in 2004–2013 table otherwise. That CSV and its
> `docs/daVinci_Annual_Procedures_Sources.md` are **generated** by
> `python src/fetch_procedure_data.py`, which scrapes each fiscal year's total
> straight from Intuitive Surgical's SEC 10-K filings (EDGAR). Re-run it to
> refresh the data (2008–present come from the filings; 2004–2007 fall back to
> the original study's estimates, which Intuitive never disclosed). The
> hand-placed figure annotations were positioned for the 2004–2013 data and may
> need nudging for a different window (they are index-clamped so they never
> crash).

> The Python analysis (`malfunctions.py`) can optionally draw the 3-set Venn
> diagram if `matplotlib-venn` is installed (`pip install matplotlib-venn`);
> otherwise it writes the Venn combination counts as CSV.

> **Step 1 fetches live data from the FDA website.** The download call is
> commented out by default in `download_maude_data.py`; enable
> `MAUDE_Download(...)` when you want to re-fetch the raw `foidev*`/`mdrfoi*`
> text files into `data/`. Be considerate of the FDA servers (the scraper
> already rate-limits itself).

## Data files

The committed `data/` and `dictionaries/` files are the merged/classified
artifacts and lookup tables from the original study. The large raw FDA dumps
(`foidev*.txt`, `mdrfoi*.txt`) are **not** committed and are re-created by
step 1; they are covered by `.gitignore`.

## License

GPL-3.0 — see [LICENSE](LICENSE).
