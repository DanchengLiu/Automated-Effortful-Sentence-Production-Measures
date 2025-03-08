import os
import re
import csv

def parse_chat_file(filepath, csv_output_path, detailed=False, identifier='*CHI'):
    # --- REGEX patterns ---
    remove_timestamps_regex = re.compile(r'\x15.*?\x15')
    silent_pause_pattern = re.compile(r'\(\s*(\d+(\.\d+)?)\s*\)')
    ends_with_plus_number = re.compile(r'\[\+\s*\d+\]') 

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

    all_time_ms = 0
    all_word_count = 0

    plus_time_ms = 0
    plus_word_count = 0

    plus_stall_count = 0
    plus_revision_count = 0
    plus_total_utt = 0

    # Classification helpers
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

    # [utterance_text, is_plus, classification_str]
    detail_rows = []

    for utt_dict in utterances:
        raw_text = utt_dict['text']
        # Accumulate time (ms) for all sets
        utt_time_ms = total_time_in_utterance(utt_dict)
        all_time_ms += utt_time_ms

        # Word count for all sets
        num_words = count_words_in_text(raw_text)
        all_word_count += num_words

        # Check if it's a plus utterance
        cleaned_no_ts = remove_timestamps_regex.sub('', raw_text).strip()
        is_plus = bool(ends_with_plus_number.search(cleaned_no_ts))

        if is_plus:
            plus_time_ms += utt_time_ms
            plus_word_count += num_words
            plus_total_utt += 1

            if has_revision(cleaned_no_ts):
                cls = 'revision'
                plus_revision_count += 1
            elif has_stall(cleaned_no_ts):
                cls = 'stall'
                plus_stall_count += 1
            else:
                cls = 'n/a'
        else:
            cls = '' 
        if is_plus:
            detail_rows.append([    
                cleaned_no_ts, 
                #'True' if is_plus else 'False',
                cls
            ])


    all_time_s = all_time_ms / 1000.0
    plus_time_s = plus_time_ms / 1000.0

    wpm_all = (all_word_count / all_time_s) * 60 if all_time_s > 0 else 0.0
    wpm_plus = (plus_word_count / plus_time_s) * 60 if plus_time_s > 0 else 0.0


    plus_stall_rate = plus_stall_count / plus_total_utt if plus_total_utt else 0.0
    plus_revision_rate = plus_revision_count / plus_total_utt if plus_total_utt else 0.0

    # Write the detail CSV
    if detailed:
        with open(csv_output_path, 'w', newline='', encoding='utf-8') as out_csv:
            writer = csv.writer(out_csv)
            writer.writerow(["Utterance", "Classification"])
            writer.writerows(detail_rows)

    return {
        'time_all': all_time_s,
        'time_plus': plus_time_s,
        'word_count_all': all_word_count,
        'word_count_plus': plus_word_count,
        'wpm_all': wpm_all,
        'wpm_plus': wpm_plus,

        'plus_stall_count': plus_stall_count,
        'plus_revision_count': plus_revision_count,
        'plus_total_utterances': plus_total_utt,
        'plus_stall_rate': plus_stall_rate,
        'plus_revision_rate': plus_revision_rate
    }


def parse_all_chat_files_in_folder(folder_path, summary_csv_path, file_extension='.cex', detailed=False, details_path="_details.csv", details_folder='./'):
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

                metrics = parse_chat_file(full_path, detail_csv_path, detailed)

                summary_rows.append([
                    fname,
                    f"{metrics['time_all']:.2f}",
                    f"{metrics['time_plus']:.2f}",
                    metrics['word_count_all'],
                    metrics['word_count_plus'],
                    f"{metrics['wpm_all']:.2f}",
                    f"{metrics['wpm_plus']:.2f}",
                    metrics['plus_stall_count'],
                    metrics['plus_revision_count'],
                    metrics['plus_total_utterances'],
                    f"{metrics['plus_stall_rate']:.4f}",
                    f"{metrics['plus_revision_rate']:.4f}",
                ])

    # Write summary CSV
    with open(summary_csv_path, 'w', newline='', encoding='utf-8') as sf:
        writer = csv.writer(sf)
        writer.writerow([
            "Filename",
            "TimeAll_sec", "TimeUtt_sec",
            "WordCountAll", "WordCountUtt",
            "WPM_All", "WPM_Utt",
            "StallCount", "RevisionCount",
            "TotalUtterances", "StallRate", "RevisionRate"
        ])
        writer.writerows(summary_rows)


if __name__ == "__main__":
    # Example usage:
    file_extension = '.cex'                             # extension of the file to be processed
    detailed = True                                     # if you want the detailed report on revision/stall/NA
    details_path="_details.csv"                         # what is the trailing file name you want for the detailed reports
    detailed_folder = './output_details/'        # where do you want to put the detailed files (note that this directory must exist)
    #--------------------------------------------------------------------------
    folder_to_process = "./test_folder/"               # the folder to input files (note that this directory must exist)
    #--------------------------------------------------------------------------
    summary_csv = "summary_TD.csv"                      # the output summary table
    parse_all_chat_files_in_folder(folder_to_process, summary_csv, file_extension=file_extension, detailed=detailed, details_path=details_path, details_folder=detailed_folder)
    print(f"Summary CSV generated at: {summary_csv}")
