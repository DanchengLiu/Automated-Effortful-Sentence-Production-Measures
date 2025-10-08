# CHI Transcript Metrics (WPM, Stall Rate, Revision Rate)

## Effortful sentence production measures

**Background**

This program automates the computation stall rate, revision rate, and words per minute. Stall rate and revision rate are adapted from Rispoli and colleague’s theoretical framework for studying sentence disruptions.
Stalls are disruption types that consist of repetitions, silent pauses, and utterance-internal filled pauses. Stalls signal a glitch or breakdown in the steady progression of incremental sentence production.
In contrast, revisions reflect a speaker’s active self-monitoring of their articulated output relative to their intended message. When the two do not align, the speaker must revise.  See Rispoli, 2003; Rispoli et al., 2008; Rispoli, 2018 for theoretical motivation for stall and revision taxonomy.
These measures have been used to examine the longitudinal association between stalls and revisions and simple sentence development (Rispoli, 2003; Rispoli et al., 2008; Rispoli, 2018), disruption patterns in school-age children with Attention Deficit Hyperactivity Disorder (ADHD; Bangert & Finestack, 2020), and disruptions in preschool-aged children with and without stuttering (Garbarino & Bernstein Ratner, 2023).

**Intended use- Redmond Sentence Recall Application**

This program automates  the analysis of sentence disruptions using a stall vs. revision taxonomy. It was initially developed to examine stall rate, revision rate, non disrupted rate and words per minute between school-age children with developmental language disorder (DLD) and typical language (Preza et al., 2025), when scored off the Redmond Sentence Recall Task (Redmond et al., 2019).
To successfully implement this program, transcripts should be in the Child Analysis of Transcripts (CHAT) or .cha format (MacWhinney, 2000). All utterances should be aligned to the audio and all disruptions should be transcribed following the CHAT manual and Preza et al. (2025).  For use on the Redmond Sentence Recall Task, all 16 child responses should be marked with a [+ #] post code.

**Measures**
This program computes the following measures:
Stall Rate: Percent of responses with a repetition, silent pause, and/or utterance internal filled pause and NO revision.
Non-disrupted rate: Percent of responses with no stall or revision.
Words per minute : # of non-disrupted words / total time to produce all responses.
Revision Rate: Percent of responses with a change in word(s) or morphosyntactic structure; may also contain a stall.

**References**
- Bangert, K. J., & Finestack, L. H. (2020). Linguistic maze production by children and adolescents with attention-deficit/hyperactivity disorder. *Journal of Speech, Language, and Hearing Research, 63*(1), 274–285. [https://doi.org/10.1044/2019_JSLHR-19-00187](https://doi.org/10.1044/2019_JSLHR-19-00187)
- Garbarino, J., & Bernstein Ratner, N. (2023). Stalling for time: stall, revision, and stuttering-like disfluencies reflect language factors in the speech of young children. *Journal of Speech, Language, and Hearing Research, 66*(6), 2018–2034. [https://doi.org/10.1044/2023_JSLHR-22-00595](https://doi.org/10.1044/2023_JSLHR-22-00595)
- MacWhinney, B. (2000). *The CHILDES Project: Tools for Analyzing Talk.* 3rd Edition. Mahwah, NJ: Lawrence Erlbaum Associates.
- Redmond, S. M., Ash, A. C., Christopulos, T. T., & Pfaff, T. (2019). Diagnostic accuracy of sentence recall and past tense measures for identifying children’s language impairments. *Journal of Speech, Language, and Hearing Research, 62*(7), 2438–2454.
- Rispoli, M. (2003). Changes in the nature of sentence production during the period of grammatical development. *Journal of Speech, Language, and Hearing Research, 46*(4), 818–830. [https://doi.org/10.1044/1092-4388(2003/064)](https://doi.org/10.1044/1092-4388%282003/064%29)
- Rispoli, M. (2018). Changing the subject: The place of revisions in grammatical development. *Journal of Speech, Language, and Hearing Research, 61*(2), 360–372. [https://doi.org/10.1044/2017_JSLHR-L-17-0216](https://doi.org/10.1044/2017_JSLHR-L-17-0216)
- Rispoli, M., Hadley, P., & Holt, J. (2008). Stalls and revisions: A developmental perspective on sentence production. *Journal of Speech, Language, and Hearing Research, 51*(4), 953–966. [https://doi.org/10.1044/1092-4388(2008/070)](https://doi.org/10.1044/1092-4388%282008/070%29)

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

## ⚙️ Classification rules used by this implementation

* **Revision** if the text contains `"[//]"`.
* Else **Stall** if any of the following are present:

  * `[/]`
  * `&-`
  * A **silent pause** `(X)` with `X ≥ 1.0`, e.g., `(1.2)`
* Otherwise labeled `n/a` (applied to **target** utterances only).

> Words are counted after removing timestamps and bracketed content `()`, `[]`, `{}`, `<>`; tokens beginning with `&` are ignored.

---

## 🧩 Using as a library

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

## 🧪 Minimal example

```
test_folder/
└── child_sample.cex

output_details/
```

Run:

```bash
python csv_all.py
```

You should get:

* `summary_TD.csv`
* `output_details/child_sample_details.csv` (if `detailed=True`)

---

