"""Fetch annual worldwide da Vinci procedure volumes from Intuitive Surgical.

Pulls the authoritative annual procedure totals straight from Intuitive
Surgical's SEC 10-K filings (EDGAR, CIK 0001035267) and writes:

  * data/daVinci_Annual_Procedures.csv          (consumed by event_arrival_times.py)
  * docs/daVinci_Annual_Procedures_Sources.md   (per-year source URLs + snippets)

Each 10-K authoritatively states its own fiscal-year total as
"... approximately N da Vinci / surgical procedures ...". We extract that
figure (ignoring "compared to" prior-year comparatives and Ion/biopsy
sub-totals) and tie it to the filing's period-of-report year.

Intuitive began disclosing an annual procedure total in its FY2008 10-K; the
earlier years (2004-2007) are not in the filings, so they are filled from the
original Alemzadeh et al. (2016, PLOS ONE) study estimates and clearly labeled
as such.

SEC asks automated clients to send a descriptive User-Agent with contact info
and to stay under 10 requests/second. Override the User-Agent with the EDGAR_UA
environment variable.

    python src/fetch_procedure_data.py
"""

import csv
import html
import os
import re
import time

import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DOCS_DIR = os.path.join(BASE_DIR, 'docs')

CSV_OUT = os.path.join(DATA_DIR, 'daVinci_Annual_Procedures.csv')
DOCS_OUT = os.path.join(DOCS_DIR, 'daVinci_Annual_Procedures_Sources.md')

# --- Configuration ---
START_YEAR = 2004
END_YEAR = 2025

CIK = '0001035267'  # Intuitive Surgical, Inc.
EDGAR_UA = os.environ.get('EDGAR_UA', 'FDA_MAUDE research script (contact: homa.alem@gmail.com)')
HEADERS = {'User-Agent': EDGAR_UA}
REQUEST_PAUSE = 0.2  # seconds between EDGAR requests (SEC fair-access etiquette)

# Original-study estimates for the years Intuitive did not disclose (2004-2007).
# Source: H. Alemzadeh et al., "Adverse Events in Robotic Surgery: A Retrospective
# Study of 14 Years of FDA Data," PLOS ONE, 2016.
STUDY_ESTIMATES = {2004: 15625, 2005: 21052, 2006: 42105, 2007: 71052}
STUDY_SOURCE = ('H. Alemzadeh et al., "Adverse Events in Robotic Surgery," PLOS ONE, 2016 '
                '(study estimate; annual total not disclosed in Intuitive SEC filings)')

# One "approximately N da Vinci/surgical procedures" mention.
CANDIDATE = re.compile(
    r'approximately\s+([\d,]{5,})\s*(?:(?:da Vinci|surgical)\s+)+procedures', re.I)


def _clean(raw_html):
    """Decode HTML entities and strip tags to a single normalized text line."""
    text = html.unescape(raw_html)
    text = re.sub(r'<[^>]+>', ' ', text)
    return re.sub(r'\s+', ' ', text)


def get_10k_filings():
    """Return a sorted list of (fiscal_year, url, filing_date) for every 10-K."""
    filings = []

    def collect(recent):
        for i in range(len(recent['form'])):
            if recent['form'][i] == '10-K':
                fy = int(recent['reportDate'][i][:4])
                acc = recent['accessionNumber'][i].replace('-', '')
                doc = recent['primaryDocument'][i]
                url = 'https://www.sec.gov/Archives/edgar/data/1035267/%s/%s' % (acc, doc)
                filings.append((fy, url, recent['filingDate'][i]))

    subs = requests.get('https://data.sec.gov/submissions/CIK%s.json' % CIK,
                        headers=HEADERS, timeout=30).json()
    collect(subs['filings']['recent'])
    # Older filings overflow into separate JSON files.
    for extra in subs['filings'].get('files', []):
        time.sleep(REQUEST_PAUSE)
        older = requests.get('https://data.sec.gov/submissions/' + extra['name'],
                             headers=HEADERS, timeout=30).json()
        collect(older)

    filings.sort()
    return filings


def extract_fy_total(text, fy):
    """Return (count, snippet) for fiscal year `fy`, or (None, None).

    Picks the first "approximately N ... procedures" that is (a) not a
    "compared to/with" prior-year comparative and (b) sits near the fiscal year.
    """
    for m in CANDIDATE.finditer(text):
        start = m.start()
        before = text[max(0, start - 30):start]
        if re.search(r'compared\s+(?:to|with)', before, re.I):
            continue
        window = text[max(0, start - 45):start + 230]
        if str(fy) not in window:
            continue
        count = int(m.group(1).replace(',', ''))
        snippet = re.sub(r'\s+', ' ', text[max(0, start - 25):start + 120]).strip()
        return count, snippet
    return None, None


def scrape():
    """Return {year: dict(procedures, source, snippet, note)} for START..END."""
    data = {}
    for fy, url, filing_date in get_10k_filings():
        if fy < START_YEAR or fy > END_YEAR or fy in data:
            continue
        time.sleep(REQUEST_PAUSE)
        try:
            text = _clean(requests.get(url, headers=HEADERS, timeout=60).text)
        except requests.RequestException as exc:
            print('  ! FY%d fetch failed: %s' % (fy, exc))
            continue
        count, snippet = extract_fy_total(text, fy)
        if count is None:
            print('  - FY%d: no annual total found in %s' % (fy, url))
            continue
        print('  + FY%d: %s procedures' % (fy, format(count, ',')))
        data[fy] = {'procedures': count, 'source': url, 'snippet': snippet,
                    'note': 'SEC 10-K (FY%d), filed %s' % (fy, filing_date)}

    # Fill years Intuitive did not disclose with the labeled study estimates.
    for year, count in STUDY_ESTIMATES.items():
        if START_YEAR <= year <= END_YEAR and year not in data:
            data[year] = {'procedures': count, 'source': STUDY_SOURCE, 'snippet': '',
                          'note': 'study estimate (not in Intuitive filings)'}
    return data


def write_csv(data):
    years = sorted(data)
    with open(CSV_OUT, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['year', 'worldwide_davinci_procedures', 'yoy_growth_pct', 'source', 'note'])
        prev = None
        for y in years:
            n = data[y]['procedures']
            yoy = '' if prev is None else round((n - prev) / prev * 100)
            w.writerow([y, n, yoy, data[y]['source'], data[y]['note']])
            prev = n
    print('Wrote %s (%d years: %d-%d)' % (CSV_OUT, len(years), years[0], years[-1]))


def write_sources(data):
    years = sorted(data)
    lines = []
    lines.append('# da Vinci Annual Procedure Volumes — Data Sources')
    lines.append('')
    lines.append('Worldwide da Vinci surgical procedure volumes compiled in '
                 '[`data/daVinci_Annual_Procedures.csv`](../data/daVinci_Annual_Procedures.csv).')
    lines.append('')
    lines.append('**This file is generated** by [`src/fetch_procedure_data.py`]'
                 '(../src/fetch_procedure_data.py), which extracts each fiscal year\'s total '
                 'directly from Intuitive Surgical\'s SEC 10-K filings (EDGAR, CIK ' + CIK + ').')
    lines.append('')
    lines.append('## Notes')
    lines.append('')
    lines.append('- Figures are **worldwide** da Vinci procedure counts, as Intuitive\'s own '
                 'rounded approximations ("approximately N").')
    lines.append('- **da Vinci only** — Ion (lung-biopsy robot) procedures, reported separately '
                 'since 2023, are excluded.')
    lines.append('- Each value is the total stated in that year\'s own 10-K (not a later '
                 'filing\'s restated comparative).')
    lines.append('- **2004–2007** are not disclosed as annual totals in Intuitive\'s filings; '
                 'they are filled from the Alemzadeh et al. (2016, PLOS ONE) study estimates and '
                 'labeled as such.')
    lines.append('')
    lines.append('## Summary')
    lines.append('')
    lines.append('| Year | Worldwide da Vinci procedures | YoY | Source |')
    lines.append('|------|------------------------------:|:---:|--------|')
    prev = None
    for y in years:
        n = data[y]['procedures']
        yoy = '—' if prev is None else '%d%%' % round((n - prev) / prev * 100)
        is_filing = data[y]['source'].startswith('http')
        src = '[FY%d 10-K](%s)' % (y, data[y]['source']) if is_filing else 'Study estimate'
        lines.append('| %d | %s | %s | %s |' % (y, format(n, ','), yoy, src))
        prev = n
    lines.append('')
    lines.append('## Provenance (extracted snippets)')
    lines.append('')
    for y in years:
        d = data[y]
        if d['source'].startswith('http'):
            lines.append('- **%d** — %s' % (y, d['note']))
            lines.append('  - %s' % d['source'])
            if d['snippet']:
                lines.append('  - > …%s…' % d['snippet'])
        else:
            lines.append('- **%d** — %s' % (y, d['source']))
    lines.append('')
    with open(DOCS_OUT, 'w') as f:
        f.write('\n'.join(lines))
    print('Wrote %s' % DOCS_OUT)


def main():
    print('Fetching Intuitive Surgical 10-K filings from SEC EDGAR...')
    data = scrape()
    if not data:
        raise SystemExit('No procedure data extracted; aborting (check network / EDGAR access).')
    write_csv(data)
    write_sources(data)


if __name__ == '__main__':
    main()
