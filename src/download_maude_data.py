"""Download and merge FDA MAUDE adverse-event reports for the da Vinci system.

Downloads all the MAUDE (FOIDEV/DEVICE and MDRFOI) files from the FDA website,
searches for the records related to a specific device, merges the DEVICE and
MDRFOI files into one spreadsheet, then walks each MDR key and opens the online
MDR report to grab the Patient Outcome, Event Description / Narrative, and
Number of Devices.

Ported from Python 2 to Python 3, and updated to process the 2014-2025 data
(the field-number layouts, retry/resume logic, and incremental saving were
brought over from the June-2019 MedSafe_MAUDE update). Requires: requests,
beautifulsoup4, xlwt.

Interface parity with download_maude_openfda.py: downloads ALL Intuitive
reports including the EndoWrist instrument/accessory events (the DEVICE-line
keyword match covers the manufacturer field), supports the same
--scope=all|davinci and --require-intuitive flags, writes the same
daVinci_MAUDE_Data_<END_YEAR><suffix>.csv + daVinci_MAUDE_Times_... outputs
(plus the legacy .xls, capped at 65,536 rows), and prints the same run summary.
Unlike the openFDA route, the times CSV here includes the real
DEVICE_DATE_OF_MANUFACTURE.

    python src/download_maude_data.py [--scope=all|davinci] [--require-intuitive]

NOTE ON FDA FILE LAYOUTS: the FDA changed the column order of the DEVICE and
MDRFOI files around 2009. The 1-based field numbers below must match the layout
of the files you actually download; verify them against the current field
definitions published on the FDA MAUDE download page before a fresh run.
"""

import csv
import os
import time
import zipfile
from zipfile import ZipFile

import requests
from bs4 import BeautifulSoup
import xlwt
from dateutil import parser

# Resolve paths relative to the repository root so the script runs from anywhere.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# A shared HTTP session (replaces the urllib2 cookie-jar opener). The FDA server
# returns an error page to the default python-requests User-Agent, so send a
# browser-like one.
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (FDA MAUDE research pipeline)'})

# =====================================================================
# Configuration
# =====================================================================
# Analysis window: reports RECEIVED within [START_YEAR, END_YEAR] are processed.
START_YEAR = 2014
END_YEAR = 2025
# One past END_YEAR; used only to enumerate the yearly foidev<YYYY> files.
CURRENT_YEAR = 2026

# Field-number schemas (1-based column positions in the FDA pipe-delimited files).
# The downstream code selects DEVICE columns positionally (Brand=idx2, Generic=idx3,
# Manufacturer=idx4, Product_Code=idx6) and MDRFOI columns by NAME, so each list
# below must keep that DEVICE ordering and must include every MDRFOI column the
# code looks up by name (MDR_REPORT_KEY, EVENT_TYPE, the date fields, ...).
#
# Pre-2009 FOIDEV/MDRFOI layout (used for the original 2000-2013 study):
FOIDEV_FIELDS_PRE2009 = [1, 2, 7, 8, 9, 19, 26, 27, 29, 30, 31, 34, 36, 44]
MDRFOI_FIELDS_PRE2009 = [1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 14, 16, 17, 25, 26, 27, 28, 30, 31,
                         32, 68, 69, 70, 72, 75]
# Current DEVICE file layout (device<YYYY>.zip, 34 cols) verified against the FDA
# files, Jul 2026: MDR_REPORT_KEY=1, DATE_RECEIVED=9, BRAND_NAME=10,
# GENERIC_NAME=11, MANUFACTURER_D_NAME=12, DEVICE_REPORT_PRODUCT_CODE=29.
FOIDEV_FIELDS_CURRENT = [1, 2, 10, 11, 12, 9, 29]
# Current MDRFOI file layout (mdrfoi*.zip, 86 cols) verified Jul 2026:
# MDR_REPORT_KEY=1, NUMBER_DEVICES=6, NUMBER_PATIENTS=7, DATE_RECEIVED=8,
# DATE_REPORT=11, DATE_OF_EVENT=12, DATE_REPORT_TO_MANUFACTURER=22,
# DEVICE_DATE_OF_MANUFACTURE=52, EVENT_TYPE=57, MANUFACTURER_NAME=66.
MDRFOI_FIELDS_CURRENT = [1, 3, 4, 6, 7, 8, 11, 12, 22, 52, 57, 66]

# Select the layout to use for this run.
FOIDEV_Field_Numbers = FOIDEV_FIELDS_CURRENT
MDRFOI_Field_Numbers = MDRFOI_FIELDS_CURRENT

# Device of interest and the keywords used to find its DEVICE records.
# Matching is case-insensitive substring matching, so the base tokens
# "da vinci" / "davinci" already cover every model variant (S, Si, X, Xi, SP,
# and da Vinci 5). The extra entries catch alternate spacing/hyphenation and
# common misspellings. "intuitive surgical" also matches the manufacturer's
# other robots (e.g. the Ion system); filter those downstream if unwanted.
device_name = ['daVinci', 'pacemaker', 'patient_monitor']
device_keywords = [['da vinci', 'davinci', 'da-vinci', 'da vinchi', 'davinchi',
                    'da vinci xi', 'da vinci sp', 'de vinci', 'devinci',
                    'davency', 'davincy', 'da vinci si', 'da vinci s',
                    'intuitive surgical', 'intuitivesurgical',
                    'intuitive surgical operations', 'endowrist'], ['pacemaker']]
data_dir = DATA_DIR

# --- Scope / filtering, mirroring download_maude_openfda.py ---
# The DEVICE-line keyword match above already captures ALL Intuitive reports,
# including the EndoWrist instruments/accessories reported under their own
# brand names ("intuitive surgical" matches the manufacturer field of every
# instrument record). SCOPE controls which of those are kept at merge time:
#   * 'all'     -- every Intuitive/da Vinci report (default).
#   * 'davinci' -- only reports whose brand/generic/manufacturer mentions
#                  da Vinci; output filenames get a _daVinci_brand suffix.
# Overridable on the command line with --scope=all|davinci.
SCOPE = 'all'

# If True (or --require-intuitive), keep only records whose manufacturer name
# mentions Intuitive. Off by default (same rationale as the openFDA script:
# the strict rule drops genuine voluntary reports and OEM da Vinci accessories);
# every run itemizes the kept non-Intuitive manufacturers.
REQUIRE_INTUITIVE = False

# Substrings identifying a da Vinci-brand record for scope='davinci' (same list
# as download_maude_openfda.py). 'vinci' covers "da vinci"/"davinci"/
# "da-vinci"/"de vinci"/"devinci".
DAVINCI_KEYWORDS = ['vinci', 'vinchi', 'davency', 'davincy']


def output_paths(scope, end_year, device):
    """Return (data_csv, times_csv, xls) output paths for the given scope."""
    suffix = '' if scope == 'all' else '_daVinci_brand'
    base = os.path.join(DATA_DIR, '%s_MAUDE_Data_%d%s' % (device, end_year, suffix))
    times = os.path.join(DATA_DIR, '%s_MAUDE_Times_%d%s.csv' % (device, end_year, suffix))
    return base + '.csv', times, base + '.xls'


def record_in_scope(foidev_fields, scope):
    """True if a DEVICE record (brand idx2 / generic idx3 / manufacturer idx4)
    belongs in the requested scope."""
    if scope == 'all':
        return True
    text = ' '.join(foidev_fields[2:5]).lower()
    return any(k in text for k in DAVINCI_KEYWORDS)


def record_has_intuitive_mfr(foidev_fields):
    """True if the DEVICE record names Intuitive as its manufacturer."""
    return 'intuitive' in foidev_fields[4].lower()

# FDA source filenames (downloaded/extracted into data/). The FDA renamed the
# yearly DEVICE files from "foidev<YYYY>" to "device<YYYY>" (the old foidev<YYYY>
# files stop after ~2018); "device" (current partial year) and "devicechange"
# carry the latest updates.
FOIDEV_files = ['device' + str(y) for y in range(START_YEAR, CURRENT_YEAR)] + \
    ['devicechange', 'device']
# The cumulative "thru" file plus the current partial-year files. Adjust the
# exact names to whatever the FDA FTP area currently publishes.
MDRFOI_files = ['mdrfoithru' + str(END_YEAR), 'mdrfoi', 'mdrfoichange']


#### Extract the fields from each record
def FieldExtract(line, field_numbers):
    fields = line.split('|')
    extracted = []
    for f in field_numbers:
        extracted.append(fields[f - 1].strip())
    return extracted


###### Download the data files from MAUDE database and save it
def MAUDE_Download(FOIDEV_files, MDRFOI_files, data_dir):
    MAUDE_url = 'https://www.accessdata.fda.gov/MAUDE/ftparea/'
    # Download all FOIDEV and MDRFOI files
    for filename in FOIDEV_files + MDRFOI_files:
        zip_path = os.path.join(data_dir, filename + '.zip')
        # Download the Zip file (stream to disk; these are up to ~700 MB each)
        resp = session.get(MAUDE_url + filename + '.zip', timeout=600, stream=True)
        resp.raise_for_status()
        with open(zip_path, 'wb') as zfile:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                zfile.write(chunk)
        # Sanity-check that we actually got a zip (not an HTML error page)
        if not zipfile.is_zipfile(zip_path):
            os.remove(zip_path)
            raise RuntimeError('Not a zip (server error?) for %s.zip' % filename)
        # Extract the Zip file
        ZipFile(zip_path, 'r').extractall(data_dir)
        # Clean up the folder by deleting the Zip file
        os.remove(zip_path)
        print(filename + ' downloaded.')


#### Extract the relevant DEVICE (FOIDEV) records and append them to the file
def FOIDEVExtract(FOIDEV_files, FOIDEV_Field_Numbers, device_name, device_keywords, data_dir):
    foidev_count = 0

    print('Starting to extract da Vinci related records..')
    # Extract those related to the device
    for filename in FOIDEV_files:
        # If the first file, first get the titles
        if filename == FOIDEV_files[0]:
            with open(os.path.join(data_dir, filename + '.txt'), 'r',
                      encoding='latin-1') as foidev_file:
                title = next(foidev_file)

                # Create the Hash Table of FOIDEV records
                FOIDEV_Titles = FieldExtract(title, FOIDEV_Field_Numbers)
                device_MDR_Hash = {'MDR_Key': FOIDEV_Titles}

                # Write the titles
                with open(os.path.join(data_dir, device_name + '_FOIDEV.txt'), 'w') as myfile:
                    myfile.write('|'.join(FOIDEV_Titles) + '\n')

        print(filename)
        # Extract only those FOIDEV records related to the Device
        # => Write in the Hash Table and in 'device_FOIDEV.txt'
        with open(os.path.join(data_dir, filename + '.txt'), 'r',
                  encoding='latin-1') as foidev_file:
            for line in foidev_file:
                for k in device_keywords:
                    if line.lower().find(k) > -1:
                        MDR_Key = line.split('|')[0]
                        if MDR_Key not in device_MDR_Hash:
                            FOIDEV_Fields = FieldExtract(line, FOIDEV_Field_Numbers)
                            device_MDR_Hash[MDR_Key] = FOIDEV_Fields
                            foidev_count = foidev_count + 1
                            # Write FOIDEV Columns
                            with open(os.path.join(data_dir, device_name + '_FOIDEV.txt'),
                                      'a') as myfile:
                                myfile.write('|'.join(FOIDEV_Fields) + '\n')
                            break

    print(str(foidev_count) + ' FOIDEV records extracted and added to the table.')
    return device_MDR_Hash


#### Extract the DEVICE (FOIDEV) records by product code and append them to the file
def FOIDEVExtract2(FOIDEV_files, FOIDEV_Field_Numbers, device_name, device_codes, data_dir):
    foidev_count = 0

    # Extract those related to the device
    for filename in FOIDEV_files:
        # If the first file, first get the titles
        if filename == FOIDEV_files[0]:
            with open(os.path.join(data_dir, filename + '.txt'), 'r',
                      encoding='latin-1') as foidev_file:
                title = next(foidev_file)

                # Create the Hash Table of FOIDEV records
                FOIDEV_Titles = FieldExtract(title, FOIDEV_Field_Numbers)
                device_MDR_Hash = {'MDR_Key': FOIDEV_Titles}

                # Write the titles
                with open(os.path.join(data_dir, device_name + '_FOIDEV.txt'), 'w') as myfile:
                    myfile.write('|'.join(FOIDEV_Titles) + '\n')

        # Extract only those FOIDEV records related to the Device
        # => Write in the Hash Table and in 'device_FOIDEV.txt'
        with open(os.path.join(data_dir, filename + '.txt'), 'r',
                  encoding='latin-1') as foidev_file:
            for line in foidev_file:
                for k in device_codes:
                    if line.find(k) > -1:
                        MDR_Key = line.split('|')[0]
                        if MDR_Key not in device_MDR_Hash:
                            FOIDEV_Fields = FieldExtract(line, FOIDEV_Field_Numbers)
                            device_MDR_Hash[MDR_Key] = FOIDEV_Fields
                            foidev_count = foidev_count + 1
                            # Write FOIDEV Columns
                            with open(os.path.join(data_dir, device_name + '_FOIDEV.txt'),
                                      'a') as myfile:
                                myfile.write('|'.join(FOIDEV_Fields) + '\n')
                            break

    print(str(foidev_count) + ' FOIDEV records extracted and added to the table.')
    return device_MDR_Hash


def _clean(text):
    """Strip non-ASCII characters (bs4 returns str in Python 3)."""
    return text.encode('ascii', 'ignore').decode('ascii')


def Get_Other_Fields(MDR_Link, max_retries=3):
    # Open each MDR Link, retrying with backoff on transient network errors.
    time.sleep(0.5)
    result = None
    for attempt in range(max_retries):
        try:
            result = session.get(MDR_Link, timeout=30)
            break
        except Exception:
            time.sleep(2 * (attempt + 1))
    if result is None:
        print('===> Tried accessing ' + MDR_Link + ' %d times..' % max_retries + '\n')
        return ['N/A', 'N/A', 'N/A']

    soup = BeautifulSoup(result.text, 'html.parser')

    ##### Patient Outcome, Event Description, and Manufacturer Narrative.
    # The MAUDE detail page was redesigned since the original 2013 study: the
    # narrative labels are now "Event or Problem Description" and
    # "(Additional) Manufacturer Narrative", and the text lives in the next
    # <div> rather than a <p>. Take whichever block element follows the label
    # first, which also handles the old layout.
    Patient_Outcome = 'N/A'
    Event = ''
    Narrative = ''

    def _block_text(st):
        block = st.find_next(['div', 'p'])
        if block is None:
            return ''
        return _clean(' '.join(block.get_text().split()))

    for st in soup.find_all('strong'):
        label = ' '.join(st.get_text().split())
        if not label:
            continue
        # Patient Outcome (old layout only; the current page no longer has it)
        if 'Patient Outcome' in label:
            raw = st.next.next if st.next is not None else ''
            if raw:
                Patient_Outcome = _clean(' '.join(str(raw).split())).replace('&nbsp;', '')
        # Event Description (old) / Event or Problem Description (current)
        elif ('Event Description' in label) or ('Event or Problem Description' in label):
            text = _block_text(st)
            if text and text not in Event:
                Event = Event + text + ' '
        # Manufacturer Narrative / Additional Manufacturer Narrative
        elif 'Manufacturer Narrative' in label:
            text = _block_text(st)
            if text and text not in Narrative:
                Narrative = Narrative + text + ' '
    # If not found any narrative or event description
    Event = Event.strip() or 'N/A'
    Narrative = Narrative.strip() or 'N/A'
    return [Patient_Outcome, Event, Narrative]


def MAUDE_Merge_Tables(start_year, end_year, FOIDEV_files, MDRFOI_files, FOIDEV_Field_Numbers,
                       MDRFOI_Field_Numbers, device_name, data_dir,
                       scope='all', require_intuitive=False):
    MAUDE_Keys = []
    AllCounts = [0, 0, 0]
    # Parity counters with download_maude_openfda.py
    skipped_scope = 0
    skipped_mfr = 0
    non_intuitive_kept = {}
    impact_counts = {'D': 0, 'IN': 0, 'M': 0, 'O': 0}

    # Optimized MAUDE Data Output
    newbook = xlwt.Workbook("iso-8859-2")
    newsheet = newbook.add_sheet('Maude_Data', cell_overwrite_ok=True)

    CSV_file, Times_file, Excel_file = output_paths(scope, end_year, device_name)
    f1 = open(CSV_file, 'w', newline='')
    csv_wr = csv.writer(f1, dialect='excel', delimiter=',')
    # Full dates for the reliability analysis (event_arrival_times.py); same
    # format as the openFDA route, but here DEVICE_DATE_OF_MANUFACTURE is real.
    ft = open(Times_file, 'w', newline='')
    times_wr = csv.writer(ft)
    times_wr.writerow(['MDR_REPORT_KEY', 'DATE_OF_EVENT', 'DATE_REPORT',
                       'DATE_REPORT_TO_MANUFACTURER', 'DATE_RECEIVED',
                       'DEVICE_DATE_OF_MANUFACTURE'])

    # Extract the Titles of Fields of Interest
    # FOIDEV_Titles
    with open(os.path.join(data_dir, FOIDEV_files[0] + '.txt'), 'r',
              encoding='latin-1') as foidev_file:
        title = next(foidev_file)
        FOIDEV_titles = FieldExtract(title, FOIDEV_Field_Numbers)
    print(FOIDEV_titles)

    # MDRFOI_titles
    with open(os.path.join(data_dir, MDRFOI_files[0] + '.txt'), 'r',
              encoding='latin-1') as mdrfoi_file:
        title = next(mdrfoi_file)
        MDRFOI_titles = FieldExtract(title, MDRFOI_Field_Numbers)
    print(MDRFOI_titles)

    # Create prevMDR_Hash of records already processed in a previous run, so a
    # resumed run can skip them. Optional: only used if a *_pre.csv exists.
    prevMDR_Hash = {}
    prev_CSV_file = os.path.join(data_dir, device_name + '_MAUDE_Data_' + str(end_year) + '_pre.csv')
    if os.path.exists(prev_CSV_file):
        with open(prev_CSV_file, 'r', newline='', encoding='latin-1') as prevMDR_file:
            next(prevMDR_file)  # skip the title
            for fields in csv.reader(prevMDR_file):
                if len(fields) > 1:
                    prevMDR_Hash[fields[1].strip()] = fields
        print('Number of previously processed records = ' + str(len(prevMDR_Hash)))

    # Create device_MDR_Hash from the extracted DEVICE records
    device_MDR_Hash = {'MDR_Key': FOIDEV_titles}
    with open(os.path.join(data_dir, device_name + '_FOIDEV.txt'), 'r') as foidev_file:
        # Skip the title
        title = next(foidev_file)
        for line in foidev_file:
            FOIDEV_Fields = line.split('|')
            MDR_Key = FOIDEV_Fields[0].strip()
            device_MDR_Hash[MDR_Key] = FOIDEV_Fields
    print('Number of relevant FIODEV records = ' + str(len(device_MDR_Hash)) + '\n')

    # Cross-match MDRFOI files to FOIDEV file
    curr_row = 0
    for filename in MDRFOI_files:
        with open(os.path.join(data_dir, filename + '.txt'), 'r',
                  encoding='latin-1') as mdrfoi_file:
            # Skip the title
            title = next(mdrfoi_file)

            # If first time, write the titles
            if filename == MDRFOI_files[0]:
                newsheet.write(curr_row, 0, 'MDR_Link')
                newsheet.write(curr_row, 1, 'Patient_Outcome')
                newsheet.write(curr_row, 2, 'Event')
                newsheet.write(curr_row, 3, 'Narrative')
                newsheet.write(curr_row, 4, 'Manufacture Year')
                newsheet.write(curr_row, 5, 'Event Year')
                newsheet.write(curr_row, 6, 'Report Year')
                newsheet.write(curr_row, 7, 'Time to Event')
                newsheet.write(curr_row, 8, 'Time to Report')
                curr_col = 9
                # Write MDRFOI Titles
                for i in range(0, len(MDRFOI_titles)):
                    newsheet.write(curr_row, curr_col + i, MDRFOI_titles[i])
                # Write FOIDEV Titles
                for i in range(0, len(FOIDEV_titles)):
                    newsheet.write(curr_row, curr_col + len(MDRFOI_titles) + i, FOIDEV_titles[i])
                # Goto the next row
                curr_col = 0
                curr_row = 1

                csv_wr.writerow(['MDR_Link', 'MDR_Key', 'Event', 'Narrative', 'Event_Type',
                                 'Patient_Outcome', 'Manufacture Year', 'Event_Year',
                                 'Report_to_Manufacture_Year', 'Report_to_FDA', 'Report_Year',
                                 'Time_to_Event', 'Time_to_Report', 'Manufacturer', 'Brand_Name',
                                 'Generic_Name', 'Product_Code'])

            print(filename)
            # For each file, read each line and cross-match it to FOIDEV
            for line in mdrfoi_file:
                try:
                    MDRFOI_fields = FieldExtract(line, MDRFOI_Field_Numbers)
                except Exception as e:
                    print(e)
                    print(line)
                    continue
                MDR_Key = MDRFOI_fields[0]
                Event_Type = MDRFOI_fields[MDRFOI_titles.index('EVENT_TYPE')]
                if MAUDE_Keys.count(MDR_Key) == 0:
                    MAUDE_Keys.append(MDR_Key)
                    AllCounts[0] = AllCounts[0] + 1
                    if Event_Type == 'D':
                        AllCounts[1] = AllCounts[1] + 1
                    elif Event_Type == 'IN':
                        AllCounts[2] = AllCounts[2] + 1

                # Relevant record we have not already processed in a prior run
                if (MDR_Key in device_MDR_Hash) and (MDR_Key not in prevMDR_Hash):
                    dev_fields = device_MDR_Hash[MDR_Key]
                    # Scope / manufacturer filters (before the expensive per-report
                    # scraping) -- parity with download_maude_openfda.py
                    if not record_in_scope(dev_fields, scope):
                        skipped_scope += 1
                        continue
                    if not record_has_intuitive_mfr(dev_fields):
                        if require_intuitive:
                            skipped_mfr += 1
                            continue
                        mfr = dev_fields[4].strip() or '(blank)'
                        non_intuitive_kept[mfr] = non_intuitive_kept.get(mfr, 0) + 1
                    # Get the report year
                    if MDRFOI_fields[MDRFOI_titles.index('DATE_RECEIVED')] != '':
                        Report_DateStr = MDRFOI_fields[MDRFOI_titles.index('DATE_RECEIVED')]
                        Report_Date = parser.parse(Report_DateStr)
                        Report_Year = str(Report_Date.year)
                    else:
                        Report_Date = 'N/A'
                        Report_Year = 'N/A'

                    # Only if the report year falls within the analysis window
                    if (Report_Year != 'N/A') and (start_year <= int(Report_Year) <= end_year):
                        # Get the rest of the fields from online records
                        MDR_Link = ('http://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfMAUDE/'
                                    'Detail.cfm?MDRFOI__ID=' + MDR_Key)
                        print('Current Row, MDR_Key = ' + str(curr_row) + ', ' + MDR_Key)
                        [Patient_Outcome, Event, Narrative] = Get_Other_Fields(MDR_Link)
                        MDR_HLink = 'HYPERLINK("' + MDR_Link + '";"' + MDR_Link + '")'

                        # Correct the EVENT Type
                        Event_Type = MDRFOI_fields[MDRFOI_titles.index('EVENT_TYPE')]
                        if (Event_Type == '*') or (Event_Type == ''):
                            Event_Type = 'O'

                        # Extract all the time fields
                        if MDRFOI_fields[MDRFOI_titles.index('DEVICE_DATE_OF_MANUFACTURE')] != '':
                            Manufacture_DateStr = MDRFOI_fields[
                                MDRFOI_titles.index('DEVICE_DATE_OF_MANUFACTURE')].strip()
                            Manufacture_Date = parser.parse(Manufacture_DateStr)
                            Manufacture_Year = str(Manufacture_Date.year)
                        else:
                            Manufacture_Date = 'N/A'
                            Manufacture_Year = 'N/A'

                        if MDRFOI_fields[MDRFOI_titles.index('DATE_OF_EVENT')] != '':
                            Event_DateStr = MDRFOI_fields[MDRFOI_titles.index('DATE_OF_EVENT')]
                            Event_Date = parser.parse(Event_DateStr)
                            Event_Year = str(Event_Date.year)
                        else:
                            Event_Date = 'N/A'
                            Event_Year = 'N/A'

                        if MDRFOI_fields[MDRFOI_titles.index('DATE_REPORT')] != '':
                            ReportMade_DateStr = MDRFOI_fields[MDRFOI_titles.index('DATE_REPORT')]
                            ReportMade_Date = parser.parse(ReportMade_DateStr)
                            ReportMade_Year = str(ReportMade_Date.year)
                        else:
                            ReportMade_Date = 'N/A'
                            ReportMade_Year = 'N/A'

                        if MDRFOI_fields[MDRFOI_titles.index('DATE_REPORT_TO_MANUFACTURER')] != '':
                            ReportMan_DateStr = MDRFOI_fields[
                                MDRFOI_titles.index('DATE_REPORT_TO_MANUFACTURER')]
                            ReportMan_Date = parser.parse(ReportMan_DateStr)
                            ReportMan_Year = str(ReportMan_Date.year)
                        else:
                            ReportMan_Date = 'N/A'
                            ReportMan_Year = 'N/A'

                        if (Manufacture_Date != 'N/A' and Event_Date != 'N/A'
                                and Event_Date > Manufacture_Date):
                            Time_to_Event = str((Event_Date - Manufacture_Date).days)
                        else:
                            Time_to_Event = 'N/A'
                        if (Event_Date != 'N/A' and Report_Date != 'N/A'
                                and Report_Date > Event_Date):
                            Time_to_Report = str((Report_Date - Event_Date).days)
                        else:
                            Time_to_Report = 'N/A'

                        # Write the extracted MDRFOI Columns from online records.
                        # (.xls caps at 65,536 rows; the CSVs always have all rows.)
                        if curr_row <= 65535:
                            newsheet.write(curr_row, 0, xlwt.Formula(MDR_HLink))
                            newsheet.write(curr_row, 1, Patient_Outcome)
                            newsheet.write(curr_row, 2, Event)
                            newsheet.write(curr_row, 3, Narrative)
                            newsheet.write(curr_row, 4, Manufacture_Year)
                            newsheet.write(curr_row, 5, Event_Year)
                            newsheet.write(curr_row, 6, Report_Year)
                            newsheet.write(curr_row, 7, Time_to_Event)
                            newsheet.write(curr_row, 8, Time_to_Report)
                            curr_col = 9

                            # Write the rest of MDRFOI Columns
                            for i in range(0, len(MDRFOI_titles)):
                                if MDRFOI_titles[i].find('EVENT_TYPE') > -1:
                                    newsheet.write(curr_row, curr_col + i, Event_Type)
                                else:
                                    newsheet.write(curr_row, curr_col + i, MDRFOI_fields[i])
                            # Write FOIDEV Columns
                            for i in range(0, len(FOIDEV_titles)):
                                newsheet.write(curr_row, curr_col + len(MDRFOI_titles) + i,
                                               device_MDR_Hash[MDR_Key][i])
                        elif curr_row == 65536:
                            print('Warning: .xls row limit reached; remaining rows are in '
                                  'the CSVs only.')

                        # Write selected columns to CSV file
                        Manufacturer = device_MDR_Hash[MDR_Key][4]
                        Brand_Name = device_MDR_Hash[MDR_Key][2]
                        Generic_Name = device_MDR_Hash[MDR_Key][3]
                        Product_Code = device_MDR_Hash[MDR_Key][6]
                        csv_wr.writerow([MDR_Link, MDR_Key, Event, Narrative, Event_Type,
                                         Patient_Outcome, Manufacture_Year, Event_Year,
                                         ReportMan_Year, ReportMade_Year, Report_Year,
                                         Time_to_Event, Time_to_Report, Manufacturer, Brand_Name,
                                         Generic_Name, Product_Code])
                        # Full dates for the reliability analysis
                        times_wr.writerow([
                            MDR_Key,
                            MDRFOI_fields[MDRFOI_titles.index('DATE_OF_EVENT')],
                            MDRFOI_fields[MDRFOI_titles.index('DATE_REPORT')],
                            MDRFOI_fields[MDRFOI_titles.index('DATE_REPORT_TO_MANUFACTURER')],
                            MDRFOI_fields[MDRFOI_titles.index('DATE_RECEIVED')],
                            MDRFOI_fields[MDRFOI_titles.index('DEVICE_DATE_OF_MANUFACTURE')]])
                        if Event_Type in impact_counts:
                            impact_counts[Event_Type] += 1
                        else:
                            impact_counts[Event_Type] = 1

                        # Remove the record from the hash to avoid duplicate records
                        device_MDR_Hash.pop(MDR_Key)

                        # Goto the next row
                        curr_row = curr_row + 1

                        # Incremental checkpoint: flush CSVs and save the XLS every
                        # 50 records so a long run can survive an interruption.
                        if curr_row % 50 == 0:
                            f1.flush()
                            ft.flush()
                            newbook.save(Excel_file)

    f1.close()
    ft.close()
    print(str(curr_row) + ' MDRFOI records cross-matched with FOIDEV records.')
    newbook.save(Excel_file)

    # --- Summary (parity with download_maude_openfda.py) ---
    print('\nWrote %s' % CSV_file)
    print('Wrote %s' % Times_file)
    print('Wrote %s' % Excel_file)
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
    print('Total reports: %d  (Malfunction=%d, Injury=%d, Death=%d, Other=%d)'
          % (sum(impact_counts.values()), impact_counts.get('M', 0),
             impact_counts.get('IN', 0), impact_counts.get('D', 0),
             impact_counts.get('O', 0)))
    return AllCounts, CSV_file, Excel_file


if __name__ == '__main__':
    import sys

    # Same flags as download_maude_openfda.py
    scope = SCOPE
    for arg in sys.argv[1:]:
        if arg.startswith('--scope='):
            scope = arg.split('=', 1)[1]
    if scope not in ('all', 'davinci'):
        raise SystemExit("Unknown scope %r (use --scope=all or --scope=davinci)" % scope)
    require_intuitive = REQUIRE_INTUITIVE or '--require-intuitive' in sys.argv[1:]
    print('Scope: %s%s' % (scope, ' (Intuitive manufacturer required)'
                           if require_intuitive else ''))

    ####### Download Maude Data (uncomment to fetch the raw FDA files into data/)
    # MAUDE_Download(FOIDEV_files, MDRFOI_files, data_dir)

    ####### Extract FOIDEV files for the device of interest (all Intuitive
    ####### reports, including instrument/accessory events; scope filtering
    ####### happens at merge time so both scopes share one extraction pass)
    FOIDEVExtract(FOIDEV_files, FOIDEV_Field_Numbers, device_name[0], device_keywords[0], data_dir)
    # FOIDEVExtract2(FOIDEV_files, FOIDEV_Field_Numbers, device_name[2], ['MHX'], data_dir)

    ####### Cross-match the MDRFOI and FOIDEV records
    AllCounts, CSV_file, Excel_file = MAUDE_Merge_Tables(
        START_YEAR, END_YEAR, FOIDEV_files, MDRFOI_files, FOIDEV_Field_Numbers,
        MDRFOI_Field_Numbers, device_name[0], data_dir,
        scope=scope, require_intuitive=require_intuitive)
