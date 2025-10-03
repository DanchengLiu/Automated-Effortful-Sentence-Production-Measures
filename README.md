# CHI Transcript Metrics (WPM, Stall Rate, Revision Rate)

Compute **words-per-minute**, **stall rate**, and **revision rate** from CHAT/CEx-style transcript files in a folder.

This tool scans a directory of transcripts (e.g., `.cex` files), extracts child utterances (default `*CHI`), and produces:

* A **summary CSV** with per-file metrics.
* Optional **per-utterance detail CSVs** (one per input file) labeling each target utterance as `stall`, `revision`, or `n/a`.

---

## ✨ What it measures

For each file:

* **WPM (All)** — Words per minute over **all** child utterances (including non-target ones).
* **WPM (Target)** — Words per minute over **target** utterances only (those marked with `[...]` as described below).
* **Stall Rate** — Fraction of **target** utterances that contain stalls.
* **Revision Rate** — Fraction of **target** utterances that contain revisions.

### How utterances are detected

* Lines beginning with a speaker code (e.g., `*CHI:`, `%...`) start a new block. Continuation lines are appended.
* Only utterances from the `identifier` speaker (default `*CHI`) are analyzed.

### What counts as a **target** utterance

An utterance is a **target** if its (timestamp-stripped) text **ends with** the pattern `"[+ xx]"`, e.g., `"[+ 23]"`.
This is used as an inclusion flag for per-utterance metrics.

### How words are counted

* Timestamps and bracketed content are removed: `(...)`, `[...]`, `{...}`, `<...>`, and any `\x15start_end\x15` timecodes.
* Tokens starting with `&` are ignored.
* A word is an ASCII alpha token `[A-Za-z]+` optionally ending with a dot (e.g., `Dr.`).

### How time is computed

* The script collects all timecode pairs in an utterance that look like `\x15<start>_<end>\x15` (milliseconds).
* Total utterance duration = sum over all `(end - start)` within that utterance.
* WPM = `(total words / total seconds) * 60`. Computed separately for **all** utterances and **target** utterances.

### Stall vs. Revision (applied only to **target** utterances)

* **Revision** if the text contains `"[//]"`.
* Else **Stall** if any of the following are present:

  * `[/]`
  * `&-`
  * A **silent pause** `(X)` with `X ≥ 1.0`, e.g., `(1.2)`
* Otherwise labeled `n/a`.

---

## 📁 Input format (CE/CHAT-style)

* Files should contain speaker tiers like `*CHI:` and may include continuation lines.
* Timestamps must appear inline as `\x15<start>_<end>\x15` (milliseconds), possibly multiple per utterance.
* Target utterances must end with `"[+ xx]"` (any integer).

**Example snippet**

```text
*CHI: I want to go to the park \x15 123_256 \x15 (1.1) [/]. [+ 12]
%com: child hesitates before 'park' \x15 300_420 \x15
*CHI: I went there yesterday. \x15 500_820 \x15 [+ 5]
```

---

## 🔧 Requirements

* Python **3.8+**
* Standard library only (no external dependencies)

---

## 🚀 Quick start

1. **Clone** the repository and ensure your transcripts are in a folder (e.g., `./test_folder/`) with the correct extension (default: `.cex`).

2. **Create an output folder** for per-utterance detail CSVs if you enable `detailed=True` (e.g., `./output_details/`).

3. **Run**:

```bash
python csv_all.py
```

By default, the script uses the following in `__main__`:

```python
file_extension = '.cex'
detailed       = True
details_path   = '_details.csv'
detailed_folder= './output_details/'
folder_to_process = './test_folder/'
summary_csv    = 'summary_TD.csv'
```

> Make sure `folder_to_process` and `detailed_folder` **exist** and that the folder contains only the files you want to process with the chosen `file_extension`.

---

## 📄 Outputs

### 1) Summary CSV (per run)

Written to the path in `summary_csv` (default `summary_TD.csv`) with columns:

| Column          | Description                                       |
| --------------- | ------------------------------------------------- |
| Filename        | Input file name                                   |
| TimeAll_sec     | Total time (s) across all child utterances        |
| TimeUtt_sec     | Total time (s) across **target** utterances       |
| WordCountAll    | Words across all child utterances                 |
| WordCountUtt    | Words across **target** utterances                |
| WPM_All         | WPM over all child utterances                     |
| WPM_Utt         | WPM over **target** utterances                    |
| StallCount      | Count of **target** utterances labeled `stall`    |
| RevisionCount   | Count of **target** utterances labeled `revision` |
| TotalUtterances | Number of **target** utterances                   |
| StallRate       | `StallCount / TotalUtterances`                    |
| RevisionRate    | `RevisionCount / TotalUtterances`                 |

### 2) Detail CSVs (optional; one per input)

If `detailed=True`, a CSV is written to `detailed_folder` with name `<input_basename><details_path>` (e.g., `sample_details.csv`) containing:

* `Utterance` — The cleaned (timestamp-stripped) utterance text.
* `Classification` — One of `stall`, `revision`, or `n/a` (for target utterances only).

---

## ⚙️ Configuration (main script)

Update these variables in the `__main__` block as needed:

| Variable            | Purpose                                    | Example               |
| ------------------- | ------------------------------------------ | --------------------- |
| `file_extension`    | Input transcript extension                 | `'.cex'`              |
| `detailed`          | Write per-utterance detail CSVs            | `True`                |
| `details_path`      | Suffix for detail CSV file names           | `'_details.csv'`      |
| `detailed_folder`   | Output folder for detail CSVs (must exist) | `'./output_details/'` |
| `folder_to_process` | Folder containing input transcripts        | `'./test_folder/'`    |
| `summary_csv`       | Output path for summary CSV                | `'summary_TD.csv'`    |

Advanced (inside functions):

* `identifier='*CHI'` — Change to a different speaker code if needed.

---

## 🧩 Using as a library

You can import and call the parser directly:

```python
from csv_all import parse_chat_file, parse_all_chat_files_in_folder

# Single file → metrics dict
metrics = parse_chat_file('path/to/file.cex', 'details.csv', detailed=True, identifier='*CHI')
print(metrics['wpm_all'], metrics['plus_stall_rate'])

# Folder → writes summary + optional detail CSVs
parse_all_chat_files_in_folder(
    folder_path='./test_folder/',
    summary_csv_path='summary_TD.csv',
    file_extension='.cex',
    detailed=True,
    details_path='_details.csv',
    details_folder='./output_details/'
)
```

---

## ✅ Best practices & caveats

* Ensure **only** the files you want to analyze share the chosen `file_extension` in the input folder.
* The script assumes **ASCII alphabetic** words for counting; non-ASCII words and numerals are ignored by design.
* Timestamps **must** be present as `\x15start_end\x15` (ms). Missing or malformed timecodes will lead to zero duration for those segments, affecting WPM.
* The inclusion flag `"[+ xx]"` must appear **at the end** of a target utterance **after** timestamps and other brackets.

---


