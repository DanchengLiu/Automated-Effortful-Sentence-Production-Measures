import os
import re
import csv

# YAML support (graceful fallback to defaults if not installed or file missing)
try:
    import yaml
except ImportError:
    yaml = None


def parse_chat_file(filepath, csv_output_path, detailed=False, identifier='*CHI', filter_predicate=None):
    # --- REGEX patterns (unchanged) ---
    remove_timestamps_regex = re.compile(r'\x15.*?\x15')
    silent_pause_pattern = re.compile(r'\(\s*(\d+(\.\d+)?)\s*\)')
    ends_with_plus_number = re.compile(r'\[\+\s*\d+\]')  # used as fallback only

    # For word count (ignore bracketed content, and ignore words starting with '&')
    remove_brackets_pattern = re.compile(r'\([^)]*\)|\[[^\]]*\]|\{[^}]*\}|<[^>]*>')
    word_pattern = re.compile(r'(?<!\S)(?!&)[A-Za-z]+\.?(?=\s|$)')

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    utterances = []
    current_utterance = None

    speaker_re = re.compile(r'^[*%]')  # lines starting with '*' or '%'
    timecode_re = re.compile(r'\x15(\d+)_(\d+)\x15')  # e.g. \x15 123_456 \x15

    def append_current_utterance():
        if current_utterance and current_utterance['text'].strip():
            utterances.append(current_utterance)

    for line in lines:
        line_stripped = line.rstrip('\n')

        # If new speaker line:
        if speaker_re.match(line_stripped):
            # Finish previous CHI utterance if any:
            append_current_utterance()
            current_utterance = None

            if line_stripped.startswith(identifier):
                current_utterance = {
                    'text': line_stripped,
                    'timestamps': timecode_re.findall(line_stripped)
                }
        else:
            # continuation line
            if current_utterance:
                current_utterance['text'] += " " + line_stripped
                current_utterance['timestamps'].extend(timecode_re.findall(line_stripped))

    # End of file
    append_current_utterance()

    # Compute times and word counts
    def total_time_in_utterance(utt_dict):
        total_ms = 0
        for (a_str, b_str) in utt_dict['timestamps']:
            a, b = int(a_str), int(b_str)
            total_ms += (b - a)
        return total_ms

    # Clean the utterance text for word counting
    def count_words_in_text(raw_text):
        tmp = remove_timestamps_regex.sub('', raw_text)
        tmp = remove_brackets_pattern.sub('', tmp)
        words = word_pattern.findall(tmp)
        return len(words)

    # Fallback predicate matches the original is_plus (= has [+ number] anywhere)
    def fallback_is_filtered(clean_text):
        return bool(ends_with_plus_number.search(clean_text))

    is_filtered = filter_predicate if filter_predicate is not None else fallback_is_filtered

    all_time_ms = 0
    all_word_count = 0

    filtered_time_ms = 0
    filtered_word_count = 0

    filtered_stall_count = 0
    filtered_revision_count = 0
    filtered_total_utt = 0

    # Classification helpers (unchanged)
    def has_revision(clean_text):
        return '[//' in clean_text

    def has_stall(clean_text):
        # If not revision, check stall markers
        if '[/]' in clean_text:
            return True
        if '&-' in clean_text:
            return True
        # Check silent pause >= 1.0
        for match in silent_pause_pattern.finditer(clean_text):
            if float(match.group(1)) >= 1.0:
                return True
        return False

    # [utterance_text, classification_str]
    detail_rows = []

    for utt_dict in utterances:
        raw_text = utt_dict['text']
        # Accumulate time (ms) for all sets
        utt_time_ms = total_time_in_utterance(utt_dict)
        all_time_ms += utt_time_ms

        # Word count for all sets
        num_words = count_words_in_text(raw_text)
        all_word_count += num_words

        # Prepare cleaned text (remove timestamps only, as before)
        cleaned_no_ts = re.sub(r'\x15.*?\x15', '', raw_text).strip()

        if is_filtered(cleaned_no_ts):
            filtered_time_ms += utt_time_ms
            filtered_word_count += num_words
            filtered_total_utt += 1

            if has_revision(cleaned_no_ts):
                cls = 'revision'
                filtered_revision_count += 1
            elif has_stall(cleaned_no_ts):
                cls = 'stall'
                filtered_stall_count += 1
            else:
                cls = 'n/a'
            # record only filtered utterances (same behavior as before with "plus")
            if detailed:
                detail_rows.append([cleaned_no_ts, cls])

    all_time_s = all_time_ms / 1000.0
    filtered_time_s = filtered_time_ms / 1000.0

    wpm_all = (all_word_count / all_time_s) * 60 if all_time_s > 0 else 0.0
    wpm_filtered = (filtered_word_count / filtered_time_s) * 60 if filtered_time_s > 0 else 0.0

    filtered_stall_rate = filtered_stall_count / filtered_total_utt if filtered_total_utt else 0.0
    filtered_revision_rate = filtered_revision_count / filtered_total_utt if filtered_total_utt else 0.0

    # Write the detail CSV (header renamed to reflect "filtered")
    if detailed:
        with open(csv_output_path, 'w', newline='', encoding='utf-8') as out_csv:
            writer = csv.writer(out_csv)
            writer.writerow(["Utterance", "Classification"])
            writer.writerows(detail_rows)

    return {
        'time_all': all_time_s,
        'time_filtered': filtered_time_s,
        'word_count_all': all_word_count,
        'word_count_filtered': filtered_word_count,
        'wpm_all': wpm_all,
        'wpm_filtered': wpm_filtered,

        'filtered_stall_count': filtered_stall_count,
        'filtered_revision_count': filtered_revision_count,
        'filtered_total_utterances': filtered_total_utt,
        'filtered_stall_rate': filtered_stall_rate,
        'filtered_revision_rate': filtered_revision_rate
    }


def parse_all_chat_files_in_folder(folder_path, summary_csv_path,
                                   file_extension='.cex', detailed=False,
                                   details_path="_details.csv", details_folder='./',
                                   filter_predicate=None):
    if not os.path.isdir(folder_path):
        print(f"Folder not found: {folder_path}")
        return

    summary_rows = []

    for root, dirs, files in os.walk(folder_path):
        for fname in files:
            if fname.lower().endswith(file_extension):
                full_path = os.path.join(root, fname)
                detail_csv_name = os.path.splitext(fname)[0] + details_path
                detail_csv_path = os.path.join(details_folder, detail_csv_name)

                metrics = parse_chat_file(full_path, detail_csv_path, detailed, filter_predicate=filter_predicate)

                summary_rows.append([
                    fname,
                    f"{metrics['time_all']:.2f}",
                    f"{metrics['time_filtered']:.2f}",
                    metrics['word_count_all'],
                    metrics['word_count_filtered'],
                    f"{metrics['wpm_all']:.2f}",
                    f"{metrics['wpm_filtered']:.2f}",
                    metrics['filtered_stall_count'],
                    metrics['filtered_revision_count'],
                    metrics['filtered_total_utterances'],
                    f"{metrics['filtered_stall_rate']:.4f}",
                    f"{metrics['filtered_revision_rate']:.4f}",
                ])

    # Write summary CSV (headers use "Filtered")
    with open(summary_csv_path, 'w', newline='', encoding='utf-8') as sf:
        writer = csv.writer(sf)
        writer.writerow([
            "Filename",
            "TimeAll_sec", "TimeFiltered_sec",
            "WordCountAll", "WordCountFiltered",
            "WPM_All", "WPM_Filtered",
            "StallCount_Filtered", "RevisionCount_Filtered",
            "TotalUtterances_Filtered", "StallRate_Filtered", "RevisionRate_Filtered"
        ])
        writer.writerows(summary_rows)


# ------------------------------
# Config + Filter construction
# ------------------------------
def load_config(yaml_path="config.yaml"):
    defaults = {
        "file_extension": ".cex",
        "detailed": True,
        "details_path": "_details.csv",
        "details_folder": "./output_details/",
        "folder_to_process": "./test_folder/",
        "summary_csv": "summary_TD.csv",
        # New: filter conditions (if omitted, we fallback to the old [+ number] rule)
        "conditions": None
    }

    if yaml is None:
        print("Warning: PyYAML not installed; using default parameters and default filter.")
        return defaults

    if not os.path.isfile(yaml_path):
        print(f"Warning: YAML config not found at {yaml_path}; using default parameters and default filter.")
        return defaults

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return {**defaults, **data}


def build_filter_predicate(conditions):
    """
    Build a predicate function text -> bool from YAML 'conditions'.

    Expected shape:
    conditions:
      filtered:
        any:
          - include: "<regex 1>"
          - include: "<regex 2>"
            exclude: "<regex to exclude>"
    If 'conditions' or 'filtered' missing, returns None (caller will fallback).
    """
    if not conditions or 'filtered' not in conditions:
        return None

    spec = conditions['filtered']
    any_clauses = spec.get('any', [])
    if not any_clauses:
        return None

    compiled_any = []
    for clause in any_clauses:
        inc_pat = clause.get('include')
        exc_pat = clause.get('exclude')
        if not inc_pat:
            # ignore malformed clause
            continue
        compiled_any.append((
            re.compile(inc_pat),
            re.compile(exc_pat) if exc_pat else None
        ))

    if not compiled_any:
        return None

    def predicate(text):
        for inc_re, exc_re in compiled_any:
            if inc_re.search(text) and (exc_re is None or not exc_re.search(text)):
                return True
        return False

    return predicate


if __name__ == "__main__":
    # Load parameters from YAML
    cfg_path = os.environ.get("CONFIG_YAML_PATH", "config.yaml")
    cfg = load_config(cfg_path)

    file_extension = cfg["file_extension"]
    detailed = cfg["detailed"]
    details_path = cfg["details_path"]
    details_folder = cfg["details_folder"]
    folder_to_process = cfg["folder_to_process"]
    summary_csv = cfg["summary_csv"]

    # Build the filter predicate from YAML (falls back to original [+ number] rule if not present)
    filter_predicate = build_filter_predicate(cfg.get("conditions"))

    parse_all_chat_files_in_folder(
        folder_to_process,
        summary_csv,
        file_extension=file_extension,
        detailed=detailed,
        details_path=details_path,
        details_folder=details_folder,
        filter_predicate=filter_predicate
    )
    print(f"Summary CSV generated at: {summary_csv}")
