import subprocess
import platform
import pyperclip
import re
import os
import sys
import time
import glob

def estimate_total_files():
    rust_files = glob.glob('**/*.rs', recursive=True)
    return max(len(rust_files), 1)

def run_clippy_and_capture_output():
    process = subprocess.Popen(
        ['cargo', 'clippy'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True,
        encoding='utf-8',
        errors='replace'
    )

    output_file_path = 'clippy_combined_output.txt'
    full_files_output_path = 'clippy_full_files_output.txt'

    combined_output = []
    raw_output = []
    mentioned_files = set()

    total_files = estimate_total_files()
    current_file = 0
    start_time = time.time()

    print("Starting Clippy analysis...")
    update_progress_bar(0, total_files, start_time)

    with open(output_file_path, 'w', encoding='utf-8') as file:
        while True:
            stdout_line = process.stdout.readline()
            if stdout_line:
                raw_output.append(stdout_line)
                if 'Checking' in stdout_line:
                    current_file += 1
                    update_progress_bar(current_file, total_files, start_time)
                process_output_line(stdout_line, combined_output, mentioned_files)

            stderr_line = process.stderr.readline()
            if stderr_line:
                raw_output.append(stderr_line)
                process_output_line(stderr_line, combined_output, mentioned_files)

            if process.poll() is not None:
                break

        for remaining_output in process.stdout:
            raw_output.append(remaining_output)
            process_output_line(remaining_output, combined_output, mentioned_files)

        for remaining_error in process.stderr:
            raw_output.append(remaining_error)
            process_output_line(remaining_error, combined_output, mentioned_files)

    update_progress_bar(total_files, total_files, start_time)
    print("\nClippy analysis complete!")

    write_outputs(output_file_path, full_files_output_path, raw_output, combined_output, mentioned_files)
    copy_to_clipboard_if_windows(output_file_path + '_final.txt')

    return check_clippy_results(raw_output)

def check_clippy_results(raw_output):
    for line in raw_output:
        if 'error:' in line or 'warning:' in line:
            return False
    return True

def process_output_line(line, combined_output, mentioned_files):
    if ('error[' in line or 'error:' in line or 'warning:' in line) and '-->' not in line:
        combined_output.append(line)
    elif '-->' in line:
        combined_output.append(line)
        error_detail = extract_file_and_line(line)
        if error_detail:
            mentioned_files.add(error_detail[0])
            file_content = cat_file_content(*error_detail)
            combined_output.append(file_content)

def update_progress_bar(current, total, start_time):
    bar_length = 50
    filled_length = int(bar_length * current // total)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    percent = round(100 * current / total, 1)
    elapsed_time = time.time() - start_time
    estimated_total_time = elapsed_time * total / current if current > 0 else 0
    remaining_time = max(estimated_total_time - elapsed_time, 0)
    
    sys.stdout.write(f'\rProgress: |{bar}| {percent}% Complete. ETA: {remaining_time:.0f}s')
    sys.stdout.flush()

def write_outputs(output_file_path, full_files_output_path, raw_output, combined_output, mentioned_files):
    with open(output_file_path, 'w', encoding='utf-8') as file:
        file.write("\n-------------------\nRAW CONSOLE OUTPUT\n")
        file.write(''.join(raw_output))
        file.write("\n-------------------\nCOMBINED OUTPUT WITH SNIPPETS\n")
        file.write(''.join(combined_output))

    with open(full_files_output_path, 'w', encoding='utf-8') as file:
        for file_path in mentioned_files:
            full_content = read_full_file_content(file_path)
            file.write(full_content)

    final_output = output_file_path + '_final.txt'
    with open(final_output, 'w', encoding='utf-8') as final_file:
        with open(output_file_path, 'r', encoding='utf-8') as f1:
            final_file.write(f1.read())
        final_file.write("\n-------------------\nFULL CONTENT OF MENTIONED FILES\n")
        with open(full_files_output_path, 'r', encoding='utf-8') as f2:
            final_file.write(f2.read())

def copy_to_clipboard_if_windows(file_path):
    if platform.system() == 'Windows':
        with open(file_path, 'r', encoding='utf-8') as final_file:
            pyperclip.copy(final_file.read())
        print("\nThe final combined output has been copied to the clipboard.")

def extract_file_and_line(line):
    match = re.search(r'--> (.+):(\d+):\d+', line)
    if match:
        file_path = match.group(1).strip()
        line_number = int(match.group(2).strip())
        return file_path, line_number
    return None

def cat_file_content(file_path, line_number):
    if not os.path.isfile(file_path):
        return f"File {file_path} not found.\n"
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
            start = max(0, line_number - 6)
            end = min(len(lines), line_number + 5)
            snippet = ''.join(lines[start:end])
            return f"\n--- Code Snippet from {file_path} (around line {line_number}) ---\n{snippet}\n--- End of Snippet ---\n"
    except Exception as e:
        return f"Error reading file {file_path}: {str(e)}\n"

def read_full_file_content(file_path):
    if not os.path.isfile(file_path):
        return f"File {file_path} not found.\n"
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            return f"\n--- Full Content of {file_path} ---\n{content}\n--- End of Full Content ---\n"
    except Exception as e:
        return f"Error reading file {file_path}: {str(e)}\n"

def build_project(release=False):
    command = ['cargo', 'build']
    if release:
        command.append('--release')
    
    print(f"Starting {'release ' if release else ''}build...")
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True,
        encoding='utf-8',
        errors='replace'
    )

    while True:
        stdout_line = process.stdout.readline()
        if stdout_line:
            print(stdout_line.strip())

        stderr_line = process.stderr.readline()
        if stderr_line:
            print(stderr_line.strip(), file=sys.stderr)

        if process.poll() is not None:
            break

    print(f"{'Release b' if release else 'B'}uild complete!")

if __name__ == '__main__':
    no_problems = run_clippy_and_capture_output()
    
    if no_problems:
        print("\nNo problems found by Clippy!")
        build_choice = input("Would you like to build the project? (y/n): ").lower()
        
        if build_choice == 'y':
            release_choice = input("Do you want to build a release version? (y/n): ").lower()
            build_project(release=release_choice == 'y')
    else:
        print("\nClippy found some issues. Please review the output and fix the problems before building.")