"""Post-hoc statistics and tables for the da Vinci MAUDE malfunction analysis.

Python/pandas port of src/malfunctions.R. Reads the classifier output
(produced by src/classify_malfunctions.py) and writes the paper tables back
into output/. Run from the repo root or from the src/ directory; the
output directory is located relative to either.

    python src/malfunctions.py

Produces Table1.csv (malfunction impacts) and Table3.csv (surgery classes),
writes the System_Errors and remaining-malfunctions subsets, prints the
diagnostic quantities the R script echoed to the console, and writes the Venn
combination-count tables. If ``matplotlib-venn`` is installed, the 3-set Venn
diagram is also drawn.
"""

import math
import os
from itertools import product

import pandas as pd

# Which classified dataset to summarize. Must match END_YEAR in
# src/classify_malfunctions.py (set to 2013 for the original committed dataset).
END_YEAR = 2025

# --- Locate the output directory (works from repo root or src/) ---
output_dir = os.path.join('..', 'output')
if not os.path.isdir(output_dir):
    output_dir = 'output'

CSV_IN = os.path.join(output_dir,
                      'daVinci_MDR_Malfunction_Impacts_' + str(END_YEAR) + '_PLOS_One.csv')

# Read the classified data. keep_default_na=False / na_filter=False keep the
# literal string "N/A" intact (R's read.csv does not treat "N/A" as missing),
# so the ``!= "N/A"`` presence tests below behave exactly like the R version.
all_data = pd.read_csv(CSV_IN, dtype=str, keep_default_na=False, na_filter=False)

# Column names (kept with their original spaces, unlike R's dotted names).
IMPACT = 'Patient Impact'
SYS_ERR = 'System Error'
TIP = 'Tip Cover'
RESET = 'System Reset'
CONV = 'New Converted'
RESCH = 'New Rescheduled'


def present(df, col):
    """Boolean mask of rows where a class column is not 'N/A' (i.e. present)."""
    return df[col] != 'N/A'


def n(df):
    """Number of rows (equivalent to R's dim(df)[1])."""
    return df.shape[0]


def p_confidence_interval(a, total):
    """95% CI half-width for a proportion, matching the R helper.

    CI <- round(1.96 * sqrt(a*(1-(a/n))) * (100/n), 1)
    """
    if total == 0:
        return float('nan')
    return round(1.96 * math.sqrt(a * (1 - (a / total))) * (100 / total), 1)


def pct(a, total):
    """round(a / total * 100, 1) with a guard for empty denominators."""
    if total == 0:
        return float('nan')
    return round((a / total) * 100, 1)


# Touch the output files the R script pre-creates (harmless, kept for parity).
for fname in ['Recent_Test.csv', 'Remaining_Malfunctions.csv',
              'Table1.csv', 'Table2.csv', 'Table3.csv', 'Table4.csv',
              'Table5.csv', 'Table6.csv', 'Table7.csv']:
    open(os.path.join(output_dir, fname), 'a').close()

# --- Basic subsets ---
Malfunctions = all_data[all_data[IMPACT] == 'M']
Fallen = all_data[present(all_data, 'Fallen')]
System_Errors = all_data[present(all_data, SYS_ERR)]
Moved = all_data[present(all_data, 'Moved')]
Broken = all_data[present(all_data, 'Broken')]
Arced = all_data[present(all_data, 'Arced')]
Tip_Cover = all_data[present(all_data, TIP)]
Vision = all_data[present(all_data, 'Vision')]
System_Reset = all_data[present(all_data, RESET)]
Converted = all_data[present(all_data, CONV)]
Rescheduled = all_data[present(all_data, RESCH)]

Rest_Malfunctions = all_data[
    ((all_data[IMPACT] == 'M') & (all_data[SYS_ERR] == 'N/A') &
     (all_data['Fallen'] == 'N/A') & (all_data['Arced'] == 'N/A') &
     (all_data[TIP] == 'N/A') & (all_data['Vision'] == 'N/A') &
     (all_data['Moved'] == 'N/A')) |
    (all_data['Other'] != 'N/A')]

print('--- Class counts ---')
print('Fallen:        ', n(Fallen))
print('System Errors: ', n(System_Errors))
print('Arced:         ', n(Arced))
print('Broken:        ', n(Broken))
print('Tip Cover:     ', n(Tip_Cover))
print('Vision:        ', n(Vision))
print('Moved:         ', n(Moved))
print('Total - Rest_Malfunctions:', n(all_data) - n(Rest_Malfunctions))

# --- Malfunction classes (union groups used for the tables) ---
Class = [None] * 9  # 1-based indexing mirrored below via Class[index - 1]
Class[0] = all_data[present(all_data, SYS_ERR)]
Class[1] = all_data[present(all_data, 'Fallen')]
Class[2] = all_data[present(all_data, 'Arced') | present(all_data, TIP)]
Class[3] = all_data[present(all_data, 'Moved')]
Class[4] = all_data[present(all_data, 'Vision')]
Class[5] = all_data[present(all_data, 'Broken')]
# Other Malfunctions (not the above cases but indicated as "M" or Broken)
Class[6] = all_data[present(all_data, 'Other')]
# Total malfunctions found (union of all the classes)
Class[7] = all_data[
    present(all_data, SYS_ERR) | present(all_data, 'Fallen') | present(all_data, 'Broken') |
    present(all_data, 'Arced') | present(all_data, TIP) | present(all_data, 'Vision') |
    present(all_data, 'Moved') | present(all_data, 'Other')]
Class[8] = all_data

# =====================================================================
# Table 1 in the paper - Malfunction Impacts
# =====================================================================
Malfunction_Categories = ['System Errors', '%', 'Fallen Pieces', '%', 'Arced/TipCover', '%',
                          'Unintended_Operation', '%', 'Video_Imaging', '%', 'Broken', '%',
                          'Other', '%', 'Total_Malfunc', '%', 'Total_Reports', '%']
Impacts = ['Total_Num', 'System_Reset', 'Converted', 'Rescheduled', 'Malfunction', 'Injury',
           'Death', 'Other']
table_1 = pd.DataFrame(0, index=Malfunction_Categories, columns=Impacts, dtype=object)

N_all = n(all_data)
for index in range(1, 10):                 # R: index = 1..9
    c = Class[index - 1]
    r = (index - 1) * 2                     # 0-based count row
    total = n(c)

    # Column 1: total number of reports
    table_1.iat[r, 0] = total
    table_1.iat[r + 1, 0] = pct(total, N_all)

    # Column 2: number of System Resets
    table_1.iat[r, 1] = n(c[present(c, RESET)])
    table_1.iat[r + 1, 1] = pct(n(c[present(c, RESET)]), total)

    # Column 3: number of Conversions
    table_1.iat[r, 2] = n(c[present(c, CONV)])
    table_1.iat[r + 1, 2] = pct(n(c[present(c, CONV)]), total)

    # Column 4: number of Reschedulings
    table_1.iat[r, 3] = n(c[present(c, RESCH)])
    table_1.iat[r + 1, 3] = pct(n(c[present(c, RESCH)]), total)

    # Columns 5-8: number of Malfunctions, Injuries, Deaths, and Other events reported
    table_1.iat[r, 4] = n(c[c[IMPACT] == 'M'])
    table_1.iat[r, 5] = n(c[c[IMPACT] == 'IN'])
    table_1.iat[r, 6] = n(c[c[IMPACT] == 'D'])
    table_1.iat[r, 7] = n(c[c[IMPACT] == 'O'])

print('\n--- Table 1: Malfunction Impacts ---')
print(table_1)
table_1.to_csv(os.path.join(output_dir, 'Table1.csv'), index_label='')

# --- Interruptions ---
interrupted = all_data[present(all_data, RESET) | present(all_data, CONV) | present(all_data, RESCH)]
print('\n--- Interruptions ---')
print('interrupted:', n(interrupted))
print('interrupted %:', pct(n(interrupted), N_all))
reset_convert = all_data[present(all_data, RESET) & present(all_data, CONV)]
print('reset & convert:', n(reset_convert))
reset_res = all_data[present(all_data, RESET) & present(all_data, RESCH)]
print('reset & reschedule:', n(reset_res))

# --- Errors and Imaging ---
error_imaging = all_data[present(all_data, SYS_ERR) | present(all_data, 'Vision')]
print('\n--- Errors and Imaging ---')
print('error_imaging:', n(error_imaging))
print('error_imaging / all:', n(error_imaging) / N_all)
print('  with System_Reset:', n(error_imaging[present(error_imaging, RESET)]))
print('  / all System_Reset:', n(error_imaging[present(error_imaging, RESET)]) / n(System_Reset))
print('  with Converted:', n(error_imaging[present(error_imaging, CONV)]))
print('  / all Converted:', n(error_imaging[present(error_imaging, CONV)]) / n(Converted))
print('  with Rescheduled:', n(error_imaging[present(error_imaging, RESCH)]))
print('  / all Rescheduled:', n(error_imaging[present(error_imaging, RESCH)]) / n(Rescheduled))
print('  Patient Impact O:', n(error_imaging[error_imaging[IMPACT] == 'O']))
print('  O / error_imaging:', n(error_imaging[error_imaging[IMPACT] == 'O']) / n(error_imaging))

# =====================================================================
# Table 3 in the JAMA paper - Surgery Classes
# =====================================================================
Surgery_Class = [None] * 7
Surgery_Class[0] = all_data[all_data['Surgery_Class'] == 'Gynecologic']
Surgery_Class[1] = all_data[all_data['Surgery_Class'] == 'Urologic']
Surgery_Class[2] = all_data[all_data['Surgery_Class'] == 'Cardiothoracic']
Surgery_Class[3] = all_data[all_data['Surgery_Class'] == 'Head and Neck']
Surgery_Class[4] = all_data[all_data['Surgery_Class'] == 'General']
Surgery_Class[5] = all_data[all_data['Surgery_Class'] == 'Colorectal']
# Class of Other (Surgery_Class = "N/A")
Surgery_Class[6] = all_data[all_data['Surgery_Class'] == 'N/A']

Surgery_Names = ['Gynecologic', '%', 'CI-', 'CI+', 'Urologic', '%', 'CI-', 'CI+',
                 'Cardiothoracic', '%', 'CI-', 'CI+', 'Head and Neck', '%', 'CI-', 'CI+',
                 'General', '%', 'CI-', 'CI+', 'Colorectal', '%', 'CI-', 'CI+',
                 'Other', '%', 'CI-', 'CI+']
Field_Names = ['Total', 'Deaths', 'Injuries', 'Malfunctions', 'Other', 'System Errors',
               'Fallen', 'Arced', 'Moved', 'Vision', 'Converted', 'Reschedulued']
table_3 = pd.DataFrame(0, index=Surgery_Names, columns=Field_Names, dtype=object)


def fill_block(col0, count, denom, over_all=False):
    """Fill a 4-row block (count, %, CI-, CI+) for one column of table_3.

    Percentages/CIs are taken over ``denom``; ``over_all`` uses the overall N.
    """
    p = pct(count, denom)
    ci = p_confidence_interval(count, denom)
    table_3.iat[r, col0] = count
    table_3.iat[r + 1, col0] = p
    table_3.iat[r + 2, col0] = round(p - ci, 1)
    table_3.iat[r + 3, col0] = round(p + ci, 1)


for index in range(1, 8):                  # R: index = 1..7
    sc = Surgery_Class[index - 1]
    r = (index - 1) * 4                     # 0-based block start
    total_class = n(sc)

    # Column 1: total number of reports (percentages over ALL adverse events)
    fill_block(0, total_class, N_all)

    # Columns 2-5: Deaths, Injuries, Malfunctions, Other (percentages within class)
    fill_block(1, n(sc[sc[IMPACT] == 'D']), total_class)
    fill_block(2, n(sc[sc[IMPACT] == 'IN']), total_class)
    fill_block(3, n(sc[sc[IMPACT] == 'M']), total_class)
    fill_block(4, n(sc[sc[IMPACT] == 'O']), total_class)

    # Columns 6-10: the different malfunction types
    fill_block(5, n(sc[present(sc, SYS_ERR)]), total_class)

    # Column 7: Fallen | Broken.  NOTE: faithfully reproduces an R quirk where
    # the "%" cell was computed from the System-Errors count (col 6), not col 7.
    fallen_broken = n(sc[present(sc, 'Fallen') | present(sc, 'Broken')])
    sys_err_count = n(sc[present(sc, SYS_ERR)])
    ci7 = p_confidence_interval(fallen_broken, total_class)
    table_3.iat[r, 6] = fallen_broken
    table_3.iat[r + 1, 6] = pct(sys_err_count, total_class)     # R bug preserved
    table_3.iat[r + 2, 6] = pct(fallen_broken, total_class) - ci7
    table_3.iat[r + 3, 6] = pct(fallen_broken, total_class) + ci7

    fill_block(7, n(sc[present(sc, 'Arced') | present(sc, TIP)]), total_class)
    fill_block(8, n(sc[present(sc, 'Moved')]), total_class)
    fill_block(9, n(sc[present(sc, 'Vision')]), total_class)

    # Columns 11-12: Conversions and Reschedulings
    fill_block(10, n(sc[present(sc, CONV)]), total_class)
    fill_block(11, n(sc[present(sc, RESCH)]), total_class)

print('\n--- Table 3: Surgery Classes ---')
print(table_3)
table_3.to_csv(os.path.join(output_dir, 'Table3.csv'), index_label='')

# --- Subset exports ---
System_Errors.to_csv(os.path.join(output_dir, 'Recent_Test.csv'))
Rest_Malfunctions.to_csv(os.path.join(output_dir, 'Remaining_Malfunctions.csv'))


# =====================================================================
# Venn diagram counts (limma::vennCounts equivalent)
# =====================================================================
def venn_counts(bool_df):
    """Count rows for every combination of the boolean set columns.

    Mirrors limma::vennCounts: returns a table with one row per 0/1 combination
    of the sets plus a Counts column.
    """
    sets = list(bool_df.columns)
    rows = []
    for combo in product([0, 1], repeat=len(sets)):
        mask = pd.Series(True, index=bool_df.index)
        for col, bit in zip(sets, combo):
            mask &= (bool_df[col] == bool(bit))
        rows.append(list(combo) + [int(mask.sum())])
    return pd.DataFrame(rows, columns=sets + ['Counts'])


c1 = pd.DataFrame({
    'System_Reset': present(all_data, RESET),
    'Converted': present(all_data, CONV),
    'Rescheduled': present(all_data, RESCH),
})
a1 = venn_counts(c1)
print('\n--- Venn counts: interruptions ---')
print(a1.to_string(index=False))
a1.to_csv(os.path.join(output_dir, 'Venn_Interruptions.csv'), index=False)

c2 = pd.DataFrame({
    'System_Error_Imaging': present(all_data, 'Vision') | present(all_data, SYS_ERR),
    'Fallen': present(all_data, 'Fallen'),
    'Arcing_Instruments': present(all_data, 'Arced') | present(all_data, TIP),
    'Other': present(all_data, 'Other'),
    'Unintended_Operation': present(all_data, 'Moved'),
})
a2 = venn_counts(c2)
print('\n--- Venn counts: malfunction classes ---')
print(a2.to_string(index=False))
a2.to_csv(os.path.join(output_dir, 'Venn_Malfunctions.csv'), index=False)

# Optional 3-set Venn diagram (limma vennDiagram equivalent) if the package is
# available. The 5-set case is exported as the count table above.
try:
    from matplotlib_venn import venn3
    import matplotlib.pyplot as plt

    def _c(sr, cv, rs):
        m = pd.Series(True, index=all_data.index)
        for flag, col in [(sr, RESET), (cv, CONV), (rs, RESCH)]:
            mask = present(all_data, col)
            m &= mask if flag else ~mask
        return int(m.sum())

    subsets = (_c(1, 0, 0), _c(0, 1, 0), _c(1, 1, 0),
               _c(0, 0, 1), _c(1, 0, 1), _c(0, 1, 1), _c(1, 1, 1))
    plt.figure()
    venn3(subsets=subsets, set_labels=('System Reset', 'Converted', 'Rescheduled'))
    plt.savefig(os.path.join(output_dir, 'Venn_Interruptions.png'), dpi=200)
    print('\nSaved Venn_Interruptions.png')
except ImportError:
    print('\n(matplotlib-venn not installed; skipped Venn diagram, wrote count tables instead)')

# =====================================================================
# Broken cross-tabulation and interruption/impact summaries
# =====================================================================
print('\n--- Not classified into any malfunction type ---')
any_malfunc = all_data[
    present(all_data, SYS_ERR) | present(all_data, 'Fallen') | present(all_data, 'Broken') |
    present(all_data, 'Arced') | present(all_data, TIP) | present(all_data, 'Vision') |
    present(all_data, 'Moved')]
print(n(all_data) - n(any_malfunc))

Broken = all_data[present(all_data, 'Broken')]
Broken_System_Error = Broken[present(Broken, SYS_ERR)]
Broken_Fallen = Broken[present(Broken, 'Fallen')]
Broken_Arced = Broken[present(Broken, 'Arced') | present(Broken, TIP)]
Broken_Moved = Broken[present(Broken, 'Moved')]
Broken_Vision = Broken[present(Broken, 'Vision')]
Broken_Other = Broken[present(Broken, 'Other')]

print('\n--- Broken overlap with each class ---')
print('Broken & System Error:', n(Broken_System_Error))
print('Broken & Fallen:      ', n(Broken_Fallen))
print('Broken & Arced/Tip:   ', n(Broken_Arced))
print('Broken & Moved:       ', n(Broken_Moved))
print('Broken & Vision:      ', n(Broken_Vision))
print('Broken & Other:       ', n(Broken_Other))

print('\n--- Broken overlap as % of each class ---')
print('% of System Error:', pct(n(Broken_System_Error), n(Class[0])))
print('% of Fallen:      ', pct(n(Broken_Fallen), n(Class[1])))
print('% of Arced/Tip:   ', pct(n(Broken_Arced), n(Class[2])))
print('% of Moved:       ', pct(n(Broken_Moved), n(Class[3])))
print('% of Vision:      ', pct(n(Broken_Vision), n(Class[4])))
print('% of Other:       ', pct(n(Broken_Other), n(Class[6])))

impacted = all_data[
    present(all_data, RESET) | present(all_data, CONV) | present(all_data, RESCH) |
    (all_data[IMPACT] == 'IN') | (all_data[IMPACT] == 'D')]
interrupted = all_data[present(all_data, RESET) | present(all_data, CONV) | present(all_data, RESCH)]
sys_interrupted_errors = interrupted[present(interrupted, SYS_ERR)]
sys_errors = all_data[present(all_data, SYS_ERR)]
sys_error_rescheduled = sys_errors[present(sys_errors, RESCH)]

print('\n--- Interrupted / impacted summary ---')
print('sys_interrupted_errors / interrupted:', n(sys_interrupted_errors) / n(interrupted))
print('sys_error_rescheduled / sys_errors:  ', n(sys_error_rescheduled) / n(sys_errors))
print('interrupted:', n(interrupted))
print('impacted:   ', n(impacted))
print('impacted %: ', pct(n(impacted), N_all))
