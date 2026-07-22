"""Download da Vinci MAUDE reports via the openFDA device/event API.

A fast, structured alternative to the HTML-scraping ``download_maude_data.py``.
It pulls every Intuitive Surgical / da Vinci adverse-event report for the
analysis window -- including the event narratives -- from
``api.fda.gov/device/event`` and writes the classifier's input CSV
``data/daVinci_MAUDE_Data_<END_YEAR>.csv`` (same 17-column format that
``classify_malfunctions.py`` expects).

Why the API instead of the raw files + per-report HTML scraping:
  * ~99k da Vinci reports for 2014-2025 come back as structured JSON with the
    narratives attached, in ~a few hundred requests / a few minutes, instead of
    ~131k individual page scrapes over many hours.

openFDA's skip-based paging caps at 26,000 records per query, and some single
years exceed that, so the query is chunked by month. Requests without an API
key are limited to 240/min and 1,000/day (plenty here); set OPENFDA_KEY to
raise the limits.

Scope. The query matches all Intuitive Surgical reports, which includes the
EndoWrist instruments/accessories reported under their own brand names (e.g.
"PROGRASP FORCEPS INSTRUMENT") -- roughly 5x more reports than the da Vinci
system brand alone in the years when instrument-malfunction reporting surged.
The SCOPE setting controls which are kept:

  * 'all'     -- every Intuitive/da Vinci report (default).
  * 'davinci' -- only reports whose brand, generic, or manufacturer name
                 mentions da Vinci; output gets a _daVinci_brand filename
                 suffix so the two scopes never overwrite each other.

Neither scope exactly reproduces the committed 2000-2013 study dataset.
Validated against 2013: openFDA has 6,233 reports received that year;
scope='davinci' keeps 1,037 of them; the committed CSV holds 1,274, of which
~500 are Intuitive instrument reports with no da Vinci mention in any device
-name field (they reflect what the FDA bulk files contained at the study's
download time -- thousands of instrument MDRs were added to MAUDE later,
during Intuitive's 2013-2014 retrospective filing wave). The overlapping
reports agree with openFDA almost perfectly (narratives identical, event
types 1,269/1,270).

Manufacturer check. A small tail of matched reports has no Intuitive
manufacturer on file: voluntary/user-facility reports with a blank or odd
manufacturer name, and OEM-made da Vinci accessories (e.g. Teleflex-built
obturators). They are kept by default and itemized in the run summary;
pass --require-intuitive (or set REQUIRE_INTUITIVE) to drop them.

Local enrichment + verification. The API does not expose
DEVICE_DATE_OF_MANUFACTURE or DATE_REPORT_TO_MANUFACTURER. By default the
script therefore also downloads the DEVICE/MDRFOI bulk dumps (reusing
download_maude_data.py's downloader and filenames; several GB on first run),
fills Manufacture Year / Time_to_Event / Report_to_Manufacture_Year and the
times-CSV date columns from them, and cross-verifies every other date and
name field against the local files, printing an agreement summary. Pass
--skip-local for the previous API-only behavior (those fields stay N/A and
no bulk files are downloaded).

    python src/download_maude_openfda.py [--scope=all|davinci] [--require-intuitive] [--skip-local]
"""

import calendar
import csv
import os
import sys
import time

import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# --- Configuration ---
START_YEAR = 2014
END_YEAR = 2025

API = 'https://api.fda.gov/device/event.json'
API_KEY = os.environ.get('OPENFDA_KEY')  # optional; raises rate limits
# Match by manufacturer OR brand. The no-space "davinci" variants catch the
# handful of voluntary/user-facility reports filed under brands like "DAVINCI
# ROBOT" or manufacturer "DAVINCI ROBOTIC", which the exact-phrase "da vinci"
# query misses (verified against the committed 2013 dataset).
SEARCH = ('(device.manufacturer_d_name:"intuitive+surgical"'
          '+OR+device.brand_name:"da+vinci"'
          '+OR+device.brand_name:davinci'
          '+OR+device.manufacturer_d_name:davinci)')
HEADERS = {'User-Agent': 'FDA_MAUDE research pipeline'}
PAGE = 500             # results per request (limit=1000 requires an API key)
REQUEST_PAUSE = 0.25   # seconds between requests

# Which reports to keep (see module docstring): 'all' or 'davinci'.
# Overridable on the command line with --scope=all|davinci.
SCOPE = 'all'

# If True (or --require-intuitive), keep only reports where some device's
# manufacturer name mentions Intuitive. Off by default because the strict rule
# drops genuine da Vinci reports (measured on the full openFDA result set):
#   * ~80 voluntary/user-facility reports with a blank/"UNK"/odd manufacturer
#     (real clinical events, including injuries and deaths), and
#   * ~25 OEM da Vinci accessories, e.g. "ISI DA VINCI S 8MM OBTURATOR"
#     reported under manufacturer TELEFLEX MEDICAL.
# Every run prints how many kept reports lack an Intuitive manufacturer, so
# the tail stays visible either way.
REQUIRE_INTUITIVE = False

# Substrings identifying a da Vinci-brand report for scope='davinci' (checked
# against the lowercased brand and generic names; mirrors the keyword list in
# download_maude_data.py minus the manufacturer-name entries). 'vinci' covers
# "da vinci"/"davinci"/"da-vinci"/"de vinci"/"devinci"; the rest are the
# misspellings seen in voluntary reports.
DAVINCI_KEYWORDS = ['vinci', 'vinchi', 'davency', 'davincy']


def output_paths(scope):
    """Return (data_csv, times_csv) paths for the given scope.

    The times CSV carries the full event/report dates for the reliability
    analysis (event_arrival_times.py). The legacy pipeline stored those in a
    .xls, but xls caps at 65,536 rows, so the openFDA route writes CSVs.
    """
    suffix = '' if scope == 'all' else '_daVinci_brand'
    data_csv = os.path.join(DATA_DIR, 'daVinci_MAUDE_Data_%d%s.csv' % (END_YEAR, suffix))
    times_csv = os.path.join(DATA_DIR, 'daVinci_MAUDE_Times_%d%s.csv' % (END_YEAR, suffix))
    return data_csv, times_csv


def in_scope(event, scope):
    """True if the report belongs in the requested scope.

    'davinci' keeps only reports where some device's brand, generic, or
    manufacturer name mentions da Vinci (the legacy pipeline keyword-matched
    the whole DEVICE line, manufacturer field included), approximating the
    original study's selection; 'all' keeps every Intuitive/da Vinci report.
    """
    if scope == 'all':
        return True
    for d in event.get('device') or []:
        text = ' '.join((d.get('brand_name') or '', d.get('generic_name') or '',
                         d.get('manufacturer_d_name') or '')).lower()
        if any(k in text for k in DAVINCI_KEYWORDS):
            return True
    return False


def has_intuitive_mfr(event):
    """True if some device on the report names Intuitive as its manufacturer."""
    for d in event.get('device') or []:
        if 'intuitive' in (d.get('manufacturer_d_name') or '').lower():
            return True
    return False

# openFDA event_type text -> the single-letter impact codes the classifier uses.
EVENT_TYPE_MAP = {'Death': 'D', 'Injury': 'IN', 'Malfunction': 'M',
                  'Other': 'O', 'No answer provided': 'O'}
# Priority when a report carries several event types.
EVENT_TYPE_PRIORITY = ['Death', 'Injury', 'Malfunction', 'Other']

CSV_HEADER = ['MDR_Link', 'MDR_Key', 'Event', 'Narrative', 'Event_Type', 'Patient_Outcome',
              'Manufacture Year', 'Event_Year', 'Report_to_Manufacture_Year', 'Report_to_FDA',
              'Report_Year', 'Time_to_Event', 'Time_to_Report', 'Manufacturer', 'Brand_Name',
              'Generic_Name', 'Product_Code']


def _year(yyyymmdd):
    s = (yyyymmdd or '')[:4]
    return s if s.isdigit() else 'N/A'


def _days_between(later, earlier):
    """Whole days between two YYYYMMDD strings (later - earlier), or 'N/A'."""
    if not (later and earlier and later.isdigit() and earlier.isdigit()
            and len(later) == 8 and len(earlier) == 8):
        return 'N/A'
    from datetime import date
    try:
        d1 = date(int(later[:4]), int(later[4:6]), int(later[6:8]))
        d0 = date(int(earlier[:4]), int(earlier[4:6]), int(earlier[6:8]))
    except ValueError:
        return 'N/A'
    return str((d1 - d0).days) if d1 > d0 else 'N/A'


def _map_event_type(event_type):
    if isinstance(event_type, list):
        for kind in EVENT_TYPE_PRIORITY:
            if kind in event_type:
                return EVENT_TYPE_MAP[kind]
        return 'O'
    return EVENT_TYPE_MAP.get(event_type, 'O')


def _pick_device(event):
    """Return the Intuitive/da Vinci device dict from a report (else the first)."""
    devices = event.get('device') or [{}]
    for d in devices:
        mfr = (d.get('manufacturer_d_name') or '').lower()
        brand = (d.get('brand_name') or '').lower()
        if 'intuitive' in mfr or 'vinci' in brand:
            return d
    return devices[0]


def extract_row(event):
    key = event.get('mdr_report_key', '')
    dev = _pick_device(event)

    texts = event.get('mdr_text') or []
    event_desc = ' '.join(t.get('text', '') for t in texts
                          if 'Description of Event' in (t.get('text_type_code') or '')).strip()
    narrative = ' '.join(t.get('text', '') for t in texts
                         if 'Manufacturer Narrative' in (t.get('text_type_code') or '')).strip()

    outcomes = set()
    for p in event.get('patient', []) or []:
        for o in (p.get('sequence_number_outcome') or []):
            if o and o.strip():
                outcomes.add(o.strip())

    date_event = event.get('date_of_event', '')
    date_received = event.get('date_received', '')
    date_report = event.get('date_report', '')
    date_mfr = event.get('date_manufacturer_received', '')
    link = ('http://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfMAUDE/'
            'Detail.cfm?MDRFOI__ID=' + str(key))

    return [
        link,
        key,
        event_desc or 'N/A',
        narrative or 'N/A',
        _map_event_type(event.get('event_type')),
        ', '.join(sorted(outcomes)) or 'N/A',
        'N/A',                                  # Manufacture Year (not exposed by openFDA)
        _year(date_event),                      # Event_Year
        _year(date_mfr),                        # Report_to_Manufacture_Year
        _year(date_report),                     # Report_to_FDA
        _year(date_received),                   # Report_Year
        'N/A',                                  # Time_to_Event (needs device mfr date)
        _days_between(date_received, date_event),  # Time_to_Report
        dev.get('manufacturer_d_name') or 'N/A',
        dev.get('brand_name') or 'N/A',
        dev.get('generic_name') or 'N/A',
        dev.get('device_report_product_code') or 'N/A',
    ]


# =====================================================================
# Local bulk-file enrichment + verification
# =====================================================================
# The API does not expose DEVICE_DATE_OF_MANUFACTURE or
# DATE_REPORT_TO_MANUFACTURER. When local enrichment is enabled (default),
# the DEVICE/MDRFOI bulk files are downloaded (reusing the legacy script's
# machinery and filenames) and those dates are read from them; all other
# dates and names are cross-verified against the local files.

def ensure_local_files():
    """Download any missing DEVICE/MDRFOI bulk files into data/.

    Reuses download_maude_data's file lists and downloader so both scripts
    always agree on filenames. Returns (FOIDEV_files, MDRFOI_files).
    """
    import download_maude_data as legacy
    missing_dev = [n for n in legacy.FOIDEV_files
                   if not os.path.exists(os.path.join(DATA_DIR, n + '.txt'))]
    missing_mdr = [n for n in legacy.MDRFOI_files
                   if not os.path.exists(os.path.join(DATA_DIR, n + '.txt'))]
    if missing_dev or missing_mdr:
        print('Downloading %d missing bulk files (this can take a few minutes '
              'and several GB of disk): %s'
              % (len(missing_dev) + len(missing_mdr), missing_dev + missing_mdr))
        legacy.MAUDE_Download(missing_dev, missing_mdr, DATA_DIR)
    return legacy.FOIDEV_files, legacy.MDRFOI_files


def _scan_files(filenames, keys, wanted_cols):
    """First-hit-per-key scan of pipe-delimited bulk files by header name.

    Returns {mdr_key: {col: value}} for keys found; files are scanned in the
    given order and the first record per key wins (same convention as the
    legacy merge).
    """
    found = {}
    for name in filenames:
        path = os.path.join(DATA_DIR, name + '.txt')
        if not os.path.exists(path):
            continue
        with open(path, 'r', encoding='latin-1') as f:
            header = next(f).rstrip('\n').split('|')
            try:
                idx = {c: header.index(c) for c in wanted_cols}
            except ValueError:
                continue  # file lacks the wanted columns (old layout)
            for line in f:
                k = line.split('|', 1)[0]
                if k in keys and k not in found:
                    fields = line.rstrip('\n').split('|')
                    if len(fields) > max(idx.values()):
                        found[k] = {c: fields[i].strip() for c, i in idx.items()}
        if len(found) == len(keys):
            break
    return found


MDRFOI_COLS = ['DATE_RECEIVED', 'DATE_REPORT', 'DATE_OF_EVENT',
               'DATE_REPORT_TO_MANUFACTURER', 'DEVICE_DATE_OF_MANUFACTURE', 'EVENT_TYPE']
DEVICE_COLS = ['BRAND_NAME', 'GENERIC_NAME', 'MANUFACTURER_D_NAME',
               'DEVICE_REPORT_PRODUCT_CODE']


def _norm_date(s):
    """Normalize MM/DD/YYYY or YYYYMMDD to YYYYMMDD ('' if unparseable/empty)."""
    s = (s or '').strip()
    if len(s) == 8 and s.isdigit():
        return s
    parts = s.split('/')
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        return '%04d%02d%02d' % (int(parts[2]), int(parts[0]), int(parts[1]))
    return ''


def _norm_name(s):
    """Case/punctuation-insensitive name normalization for verification."""
    out = []
    for ch in (s or '').upper():
        out.append(ch if (ch.isalnum() or ch == ' ') else ' ')
    return ' '.join(''.join(out).split())


def enrich_and_verify(rows, times_rows, mdr_local, dev_local):
    """Fill the missing date fields from the local files and verify the rest.

    rows/times_rows are {key: list} as produced by the fetch phase. Returns a
    stats dict: per-field verification counts + local-coverage numbers.
    """
    stats = {f: {'agree': 0, 'differ': 0} for f in
             ['date_received', 'date_report', 'date_of_event', 'event_type',
              'brand', 'generic', 'manufacturer', 'product_code']}
    examples = []
    no_mdr = no_dev = 0

    for key, row in rows.items():
        trow = times_rows[key]
        m = mdr_local.get(key)
        d = dev_local.get(key)

        # --- Enrichment: the two dates openFDA does not expose ---
        if m:
            mfg = _norm_date(m['DEVICE_DATE_OF_MANUFACTURE'])
            to_mfr = _norm_date(m['DATE_REPORT_TO_MANUFACTURER'])
            row[6] = mfg[:4] if mfg else 'N/A'                     # Manufacture Year
            row[8] = to_mfr[:4] if to_mfr else 'N/A'               # Report_to_Manufacture_Year
            row[11] = _days_between(_norm_date(m['DATE_OF_EVENT']), mfg)  # Time_to_Event
            trow[3] = to_mfr                                       # DATE_REPORT_TO_MANUFACTURER
            trow[5] = mfg                                          # DEVICE_DATE_OF_MANUFACTURE
        else:
            no_mdr += 1
            row[8] = 'N/A'   # without local coverage there is no real value
            trow[3] = ''

        # --- Verification: API values vs local bulk values ---
        if m:
            # times row layout: [key, DATE_OF_EVENT, DATE_REPORT,
            #                    DATE_REPORT_TO_MANUFACTURER, DATE_RECEIVED, MFG]
            for field, api_val, loc_val in [
                    ('date_received', trow[4], _norm_date(m['DATE_RECEIVED'])),
                    ('date_report', trow[2], _norm_date(m['DATE_REPORT'])),
                    ('date_of_event', trow[1], _norm_date(m['DATE_OF_EVENT'])),
                    ('event_type', row[4],
                     m['EVENT_TYPE'] if m['EVENT_TYPE'] not in ('', '*') else 'O')]:
                ok = _norm_date(api_val) == loc_val if field.startswith('date') \
                    else api_val == loc_val
                stats[field]['agree' if ok else 'differ'] += 1
                if not ok and len(examples) < 10:
                    examples.append((key, field, api_val, loc_val))
        if d:
            for field, api_val, loc_val in [
                    ('brand', row[14], d['BRAND_NAME']),
                    ('generic', row[15], d['GENERIC_NAME']),
                    ('manufacturer', row[13], d['MANUFACTURER_D_NAME']),
                    ('product_code', row[16], d['DEVICE_REPORT_PRODUCT_CODE'])]:
                ok = _norm_name(api_val) == _norm_name(loc_val)
                stats[field]['agree' if ok else 'differ'] += 1
                if not ok and len(examples) < 10:
                    examples.append((key, field, api_val, loc_val))
        else:
            no_dev += 1

    stats['_no_mdr'] = no_mdr
    stats['_no_dev'] = no_dev
    stats['_examples'] = examples
    return stats


def _get(url, max_retries=5):
    """GET with backoff on rate-limit / transient errors. None => zero results."""
    for attempt in range(max_retries):
        resp = requests.get(url, headers=HEADERS, timeout=90)
        if resp.status_code == 404:
            return None  # openFDA returns 404 for a zero-result query
        if resp.status_code in (403, 429, 500, 502, 503):
            time.sleep(2 * (attempt + 1))
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError('openFDA kept returning %d for %s' % (resp.status_code, url))


def fetch_range(date_range):
    """Yield all report dicts whose date_received falls in date_range."""
    skip = 0
    while True:
        url = '%s?search=%s+AND+date_received:%s&limit=%d&skip=%d' % (
            API, SEARCH, date_range, PAGE, skip)
        if API_KEY:
            url += '&api_key=' + API_KEY
        body = _get(url)
        if body is None:
            return
        results = body.get('results', [])
        if not results:
            return
        for ev in results:
            yield ev
        skip += len(results)
        total = body.get('meta', {}).get('results', {}).get('total', 0)
        if skip >= total or len(results) < PAGE:
            return
        time.sleep(REQUEST_PAUSE)


def main():
    scope = SCOPE
    for arg in sys.argv[1:]:
        if arg.startswith('--scope='):
            scope = arg.split('=', 1)[1]
    if scope not in ('all', 'davinci'):
        raise SystemExit("Unknown scope %r (use --scope=all or --scope=davinci)" % scope)
    require_intuitive = REQUIRE_INTUITIVE or '--require-intuitive' in sys.argv[1:]
    skip_local = '--skip-local' in sys.argv[1:]
    csv_out, times_out = output_paths(scope)
    print('Scope: %s%s%s' % (scope,
                             ' (Intuitive manufacturer required)' if require_intuitive else '',
                             ' (local enrichment skipped)' if skip_local else ''))

    os.makedirs(DATA_DIR, exist_ok=True)

    # --- Phase 1: fetch everything from the API into memory ---
    seen = set()
    rows = {}         # key -> data-CSV row
    times_rows = {}   # key -> times-CSV row
    skipped_scope = 0
    skipped_mfr = 0
    non_intuitive_kept = {}   # manufacturer name -> count, for the run summary
    counts = {'D': 0, 'IN': 0, 'M': 0, 'O': 0}
    for year in range(START_YEAR, END_YEAR + 1):
        year_n = 0
        for month in range(1, 13):
            last = calendar.monthrange(year, month)[1]
            rng = '[%d-%02d-01+TO+%d-%02d-%02d]' % (year, month, year, month, last)
            for ev in fetch_range(rng):
                key = ev.get('mdr_report_key')
                if key in seen:
                    continue
                seen.add(key)
                if not in_scope(ev, scope):
                    skipped_scope += 1
                    continue
                if not has_intuitive_mfr(ev):
                    if require_intuitive:
                        skipped_mfr += 1
                        continue
                    mfr = (_pick_device(ev).get('manufacturer_d_name')
                           or '(blank)').strip() or '(blank)'
                    non_intuitive_kept[mfr] = non_intuitive_kept.get(mfr, 0) + 1
                row = extract_row(ev)
                rows[key] = row
                # DATE_REPORT_TO_MANUFACTURER + DEVICE_DATE_OF_MANUFACTURE come
                # from the local bulk files in phase 2 (not exposed by the API).
                times_rows[key] = [key, ev.get('date_of_event', ''),
                                   ev.get('date_report', ''), '',
                                   ev.get('date_received', ''), '']
                counts[row[4]] = counts.get(row[4], 0) + 1
                year_n += 1
            time.sleep(REQUEST_PAUSE)
        print('  %d: %d reports (running total %d)' % (year, year_n, len(rows)), flush=True)

    # --- Phase 2: local bulk files -> missing dates + cross-verification ---
    stats = None
    if not skip_local:
        foidev_files, mdrfoi_files = ensure_local_files()
        keys = set(rows)
        print('Scanning local MDRFOI files for %d keys...' % len(keys), flush=True)
        mdr_local = _scan_files(mdrfoi_files, keys, MDRFOI_COLS)
        print('  found %d/%d in MDRFOI files' % (len(mdr_local), len(keys)), flush=True)
        print('Scanning local DEVICE files...', flush=True)
        dev_local = _scan_files(foidev_files, keys, DEVICE_COLS)
        print('  found %d/%d in DEVICE files' % (len(dev_local), len(keys)), flush=True)
        stats = enrich_and_verify(rows, times_rows, mdr_local, dev_local)

    # --- Phase 3: write the CSVs ---
    with open(csv_out, 'w', newline='') as f, open(times_out, 'w', newline='') as ft:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        times_writer = csv.writer(ft)
        times_writer.writerow(['MDR_REPORT_KEY', 'DATE_OF_EVENT', 'DATE_REPORT',
                               'DATE_REPORT_TO_MANUFACTURER', 'DATE_RECEIVED',
                               'DEVICE_DATE_OF_MANUFACTURE'])
        for key in rows:
            writer.writerow(rows[key])
            times_writer.writerow(times_rows[key])

    # --- Summary ---
    print('\nWrote %s' % csv_out)
    print('Wrote %s' % times_out)
    if skipped_scope:
        print('Skipped %d reports outside scope %r.' % (skipped_scope, scope))
    if skipped_mfr:
        print('Skipped %d reports without an Intuitive manufacturer '
              '(--require-intuitive).' % skipped_mfr)
    if non_intuitive_kept:
        total = sum(non_intuitive_kept.values())
        print('Kept %d reports without an Intuitive manufacturer '
              '(voluntary reports / OEM accessories; rerun with '
              '--require-intuitive to drop them):' % total)
        for mfr, n in sorted(non_intuitive_kept.items(), key=lambda kv: -kv[1]):
            print('  %5d  %s' % (n, mfr))
    if stats is not None:
        print('\n--- Verification vs local bulk files ---')
        print('No local MDRFOI record: %d, no local DEVICE record: %d '
              '(recent reports may not be in the bulk dumps yet)'
              % (stats['_no_mdr'], stats['_no_dev']))
        for field in ['date_received', 'date_report', 'date_of_event', 'event_type',
                      'brand', 'generic', 'manufacturer', 'product_code']:
            s = stats[field]
            print('  %-14s agree=%d differ=%d' % (field, s['agree'], s['differ']))
        for key, field, api_val, loc_val in stats['_examples']:
            print('  e.g. [%s] %s: api=%r local=%r' % (key, field, api_val, loc_val))
    print('Total reports: %d  (Malfunction=%d, Injury=%d, Death=%d, Other=%d)'
          % (len(rows), counts['M'], counts['IN'], counts['D'], counts['O']))


if __name__ == '__main__':
    main()
