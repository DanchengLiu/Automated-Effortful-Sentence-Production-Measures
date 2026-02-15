import os
import re
import csv

# YAML support (graceful fallback to defaults if not installed or file missing)
try:
    import yaml
except ImportError:
    yaml = None


SIMPLE_ITEMS = {1, 4, 5, 7, 9, 10, 13, 15}
PASSIVE_ITEMS = {2, 3, 6, 8, 11, 12, 14, 16}


def parse_chat_file(filepath, csv_output_path, detailed=False, identifier='*CHI', filter_predicate=None):
    # --- REGEX patterns ---
    remove_timestamps_regex = re.compile(r'\x15.*?\x15')
    silent_pause_pattern = re.compile(r'\(\s*(\d+(\.\d+)?)\s*\)')

    # New: extract trailing [+ xx] item id (must be at end)
    plus_item_at_end = re.compile(r'\[\s*\+\s*(\d+)\s*\]\s*$')

    # Fallback filter: ends with [+ number]
    ends_with_plus_number = re.compile(r'\[\s*\+\s*\d+\s*\]\s*$')

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

    append_current_utterance()

    def total_time_in_utterance(utt_dict):
        total_ms = 0
        for (a_str, b_str) in utt_dict['timestamps']:
            a, b = int(a_str), int(b_str)
            total_ms += (b - a)
        return total_ms

    def count_words_in_text(raw_text):
        tmp = remove_timestamps_regex.sub('', raw_text)
        tmp = remove_brackets_pattern.sub('', tmp)
        words = word_pattern.findall(tmp)
        return len(words)

    def fallback_is_filtered(clean_text):
        # default behavior if YAML conditions absent
        return bool(ends_with_plus_number.search(clean_text))

    is_filtered = filter_predicate if filter_predicate is not None else fallback_is_filtered

    # Overall (kept, in case you still want them)
    all_time_ms = 0
    all_word_count = 0

    # Per-group accumulators
    groups = {
        "simple": {"time_ms": 0, "word_count": 0, "stall": 0, "revision": 0, "total": 0},
        "passive": {"time_ms": 0, "word_count": 0, "stall": 0, "revision": 0, "total": 0},
        "other": {"time_ms": 0, "word_count": 0, "stall": 0, "revision": 0, "total": 0},  # safety net
    }

    def has_revision(clean_text):
        return '[//' in clean_text

    def has_stall(clean_text):
        if '[/]' in clean_text:
            return True
        if '&-' in clean_text:
            return True
        for match in silent_pause_pattern.finditer(clean_text):
            if float(match.group(1)) >= 1.0:
                return True
        return False

    # Detailed rows
    detail_rows = []

    for utt_dict in utterances:
        raw_text = utt_dict['text']
        utt_time_ms = total_time_in_utterance(utt_dict)
        all_time_ms += utt_time_ms

        num_words = count_words_in_text(raw_text)
        all_word_count += num_words

        cleaned_no_ts = re.sub(r'\x15.*?\x15', '', raw_text).strip()

        if not is_filtered(cleaned_no_ts):
            continue

        # Extract item id from trailing [+ xx]
        m = plus_item_at_end.search(cleaned_no_ts)
        item_id = int(m.group(1)) if m else None

        if item_id in SIMPLE_ITEMS:
            gname = "simple"
        elif item_id in PASSIVE_ITEMS:
            gname = "passive"
        else:
            gname = "other"

        groups[gname]["time_ms"] += utt_time_ms
        groups[gname]["word_count"] += num_words
        groups[gname]["total"] += 1

        if has_revision(cleaned_no_ts):
            cls = "revision"
            groups[gname]["revision"] += 1
        elif has_stall(cleaned_no_ts):
            cls = "stall"
            groups[gname]["stall"] += 1
        else:
            cls = "n/a"

        if detailed:
            detail_rows.append([cleaned_no_ts, item_id if item_id is not None else "", gname, cls])

    def finalize_group(g):
        time_s = g["time_ms"] / 1000.0
        total = g["total"]
        stall = g["stall"]
        revision = g["revision"]
        disrupted = stall + revision

        wpm = (g["word_count"] / time_s) * 60 if time_s > 0 else 0.0
        stall_rate = stall / total if total else 0.0
        revision_rate = revision / total if total else 0.0
        non_disrupted_rate = (total - disrupted) / total if total else 0.0

        return {
            "time_s": time_s,
            "word_count": g["word_count"],
            "total": total,
            "stall": stall,
            "revision": revision,
            "stall_rate": stall_rate,
            "revision_rate": revision_rate,
            "non_disrupted_rate": non_disrupted_rate,
            "wpm": wpm,
        }

    simple_metrics = finalize_group(groups["simple"])
    passive_metrics = finalize_group(groups["passive"])
    other_metrics = finalize_group(groups["other"])

    # Write the detail CSV
    if detailed:
        with open(csv_output_path, 'w', newline='', encoding='utf-8') as out_csv:
            writer = csv.writer(out_csv)
            writer.writerow(["Utterance", "ItemID", "Group", "Classification"])
            writer.writerows(detail_rows)

    # Keep overall "all" metrics too (optional / backward-compat)
    all_time_s = all_time_ms / 1000.0
    wpm_all = (all_word_count / all_time_s) * 60 if all_time_s > 0 else 0.0

    return {
        "time_all": all_time_s,
        "word_count_all": all_word_count,
        "wpm_all": wpm_all,

        "simple": simple_metrics,
        "passive": passive_metrics,
        "other": other_metrics,
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

                sm = metrics["simple"]
                pm = metrics["passive"]

                summary_rows.append([
                    fname,

                    sm["total"],
                    f"{sm['stall_rate']:.4f}",
                    f"{sm['revision_rate']:.4f}",
                    f"{sm['non_disrupted_rate']:.4f}",
                    f"{sm['wpm']:.2f}",

                    pm["total"],
                    f"{pm['stall_rate']:.4f}",
                    f"{pm['revision_rate']:.4f}",
                    f"{pm['non_disrupted_rate']:.4f}",
                    f"{pm['wpm']:.2f}",
                ])

    with open(summary_csv_path, 'w', newline='', encoding='utf-8') as sf:
        writer = csv.writer(sf)
        writer.writerow([
            "Filename",

            "TotalUtterances_Simple",
            "StallRate_Simple",
            "RevisionRate_Simple",
            "NonDisruptedRate_Simple",
            "WPM_Simple",

            "TotalUtterances_Passive",
            "StallRate_Passive",
            "RevisionRate_Passive",
            "NonDisruptedRate_Passive",
            "WPM_Passive",
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
    cfg_path = os.environ.get("CONFIG_YAML_PATH", "config.yaml")
    cfg = load_config(cfg_path)

    file_extension = cfg["file_extension"]
    detailed = cfg["detailed"]
    details_path = cfg["details_path"]
    details_folder = cfg["details_folder"]
    folder_to_process = cfg["folder_to_process"]
    summary_csv = cfg["summary_csv"]

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
