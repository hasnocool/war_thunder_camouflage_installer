import os
import re
import csv
import json
from collections import defaultdict, Counter
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
from git import Repo
import subprocess
import argparse
import pathspec
import seaborn as sns
import networkx as nx

# File for storing historical data
HISTORY_FILE = 'project_metrics_history.csv'
CACHE_FILE = 'project_metrics_cache.json'
DEFAULT_IMAGE_DIR = 'project_metrics_images'

EXCLUDE_PATTERNS = ['*.pack', '*.sample', '*.idx', '*.jpg', '*.png', '*.rev']

class AtomicCounter:
    """Thread-safe counter for atomic operations."""
    def __init__(self, initial=0):
        self.value = initial

    def increment(self, num=1):
        self.value += num

    def get(self):
        return self.value

class ThreadSafeDefaultDict:
    """Thread-safe defaultdict."""
    def __init__(self, default_factory):
        self.default_factory = default_factory
        self.d = {}

    def __getitem__(self, key):
        if key not in self.d:
            self.d[key] = self.default_factory()
        return self.d[key]

    def items(self):
        return list(self.d.items())

def is_binary(file_path):
    """Determine if a file is binary."""
    try:
        with open(file_path, 'rb') as f:
            return b'\0' in f.read(1024)
    except Exception:
        return True

def count_lines_words_chars(file_path):
    """Count the number of lines, words, and characters in a file."""
    if is_binary(file_path):
        return 0, 0, os.path.getsize(file_path)

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.splitlines()
            words = content.split()
            chars = len(content)
        return len(lines), len(words), chars
    except Exception as e:
        print(f"Error counting lines, words, and characters for {file_path}: {str(e)}")
        return 0, 0, os.path.getsize(file_path)

def process_file(file_path):
    """Process each file and gather statistics."""
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    if ext == '':
        ext = '[no extension]'  # Label files with no extension

    print(f"Processing file: {file_path}")

    try:
        file_size = os.path.getsize(file_path)
        lines, words, chars = count_lines_words_chars(file_path)

        if is_binary(file_path):
            return ext, {'lines': 0, 'words': 0, 'chars': file_size, 'size': file_size, 'todos': []}

        todos = find_todos(file_path)
        return ext, {'lines': lines, 'words': words, 'chars': chars, 'size': file_size, 'todos': todos}
    except Exception as e:
        print(f"Error processing file: {file_path}. Error: {str(e)}")
        return ext, None


def analyze_chunk(file_list):
    """Analyze a list of files and return stats and todos."""
    local_stats = ThreadSafeDefaultDict(lambda: {
        'files': AtomicCounter(),
        'lines': AtomicCounter(),
        'words': AtomicCounter(),
        'chars': AtomicCounter(),
        'size': AtomicCounter()
    })
    local_totals = {
        'files': AtomicCounter(),
        'lines': AtomicCounter(),
        'words': AtomicCounter(),
        'chars': AtomicCounter(),
        'size': AtomicCounter()
    }
    local_todos = []
    
    print(f"Analyzing {len(file_list)} files...")

    for file_path in file_list:
        ext, data = process_file(file_path)
        if data:
            local_stats[ext]['files'].increment()
            local_stats[ext]['lines'].increment(data['lines'])
            local_stats[ext]['words'].increment(data['words'])
            local_stats[ext]['chars'].increment(data['chars'])
            local_stats[ext]['size'].increment(data['size'])
            
            local_totals['files'].increment()
            local_totals['lines'].increment(data['lines'])
            local_totals['words'].increment(data['words'])
            local_totals['chars'].increment(data['chars'])
            local_totals['size'].increment(data['size'])
            
            local_todos.extend(data['todos'])
    
    return local_stats, local_totals, local_todos

def load_gitignore_patterns(root_dir):
    """Load .gitignore patterns from the root directory."""
    gitignore_path = os.path.join(root_dir, '.gitignore')
    patterns = EXCLUDE_PATTERNS[:]  # Start with the default exclude patterns

    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            patterns.extend(f.read().splitlines())
    
    spec = pathspec.PathSpec.from_lines('gitwildmatch', patterns)
    return spec

def is_ignored(path, spec, root_dir):
    """Check if a given path should be ignored based on the .gitignore spec."""
    if spec is None:
        return False
    rel_path = os.path.relpath(path, root_dir)
    return spec.match_file(rel_path)

def detect_license():
    """Detect the project license by examining the LICENSE file."""
    print("Detecting project license...")
    license_files = ['LICENSE', 'LICENSE.txt', 'LICENSE.md']
    
    for license_file in license_files:
        if os.path.exists(license_file):
            try:
                with open(license_file, 'r', encoding='utf-8') as file:
                    content = file.read()
                    if 'MIT' in content:
                        return 'MIT License'
                    elif 'Apache' in content:
                        return 'Apache License'
                    elif 'GPL' in content or 'General Public License' in content:
                        return 'GPL License'
                    else:
                        return 'License detected, but not recognized'
            except Exception as e:
                print(f"Error reading {license_file}: {e}")
                return 'Error reading license file'
    
    return 'License file not found'

def format_size(size_in_bytes):
    """Format the size in bytes to a human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} PB"

def analyze_dependencies():
    """Analyze project dependencies from package files."""
    print("Analyzing dependencies...")
    dependencies = {}
    # Add logic to parse dependencies from different package managers
    # For example, parse requirements.txt for Python, package.json for Node.js, etc.
    if os.path.exists('requirements.txt'):
        with open('requirements.txt', 'r') as f:
            for line in f:
                if '==' in line:
                    dep, version = line.strip().split('==')
                    dependencies[dep] = version
                else:
                    dependencies[line.strip()] = 'Latest'
    elif os.path.exists('Cargo.toml'):
        try:
            import toml
            with open('Cargo.toml', 'r') as file:
                cargo_data = toml.load(file)
                dependencies = cargo_data.get('dependencies', {})
        except Exception as e:
            print(f"Error reading Cargo.toml: {e}")
    else:
        print("No known dependency files found.")
    return dependencies

def find_todos(file_path):
    """Find TODO and FIXME comments in files."""
    todos = []
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for i, line in enumerate(file, 1):
                if 'TODO' in line or 'FIXME' in line:
                    todos.append(f"{file_path}:{i}: {line.strip()}")
    except Exception:
        pass
    return todos

def calculate_code_to_comment_ratio(root_dir):
    """Calculate the ratio of code lines to comment lines."""
    print("Calculating code-to-comment ratio...")
    code_lines = AtomicCounter()
    comment_lines = AtomicCounter()

    file_list = get_git_tracked_files()
    for file_path in file_list:
        if file_path.endswith(('.rs', '.py', '.js', '.java', '.c', '.cpp')):
            if not is_binary(file_path):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                    in_block_comment = False
                    for line in file:
                        line = line.strip()
                        if line.startswith('/*') or line.startswith('"""') or line.startswith("'''"):
                            in_block_comment = True
                            comment_lines.increment()
                        elif line.endswith('*/') or line.endswith('"""') or line.endswith("'''"):
                            in_block_comment = False
                            comment_lines.increment()
                        elif in_block_comment or line.startswith('//') or line.startswith('#'):
                            comment_lines.increment()
                        elif line:
                            code_lines.increment()
    
    ratio = code_lines.get() / comment_lines.get() if comment_lines.get() > 0 else float('inf')
    print(f"Code-to-comment ratio calculated: {ratio:.2f}")
    return code_lines.get(), comment_lines.get(), ratio

def get_git_tracked_files():
    """Get a list of files tracked by Git."""
    try:
        result = subprocess.run(
            ['git', 'ls-files'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        files = result.stdout.strip().split('\n')
        return files
    except subprocess.CalledProcessError as e:
        print(f"Error getting tracked files: {e.stderr}")
        return []

def get_git_commit_stats():
    """Get commit statistics using git log."""
    try:
        # Get commit counts per date and author
        result = subprocess.run(
            ['git', 'log', '--pretty=format:%ad|%an', '--date=short'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        logs = result.stdout.strip().split('\n')
        commit_dates = []
        commit_authors = []
        for line in logs:
            if '|' in line:
                date, author = line.split('|')
                commit_dates.append(date)
                commit_authors.append(author)
        date_counts = Counter(commit_dates)
        author_counts = Counter(commit_authors)
        
        # Get lines added and deleted per date and author
        result = subprocess.run(
            ['git', 'log', '--shortstat', '--pretty=format:%ad|%an', '--date=short'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        lines = result.stdout.strip().split('\n')
        dates = []
        authors = []
        insertions = []
        deletions = []
        
        current_date = ''
        current_author = ''
        for line in lines:
            if '|' in line:
                current_date, current_author = line.split('|')
            elif 'files changed' in line:
                # Parse the line to get insertions and deletions
                ins = re.search(r'(\d+) insertions?', line)
                dels = re.search(r'(\d+) deletions?', line)
                ins_count = int(ins.group(1)) if ins else 0
                del_count = int(dels.group(1)) if dels else 0

                dates.append(current_date)
                authors.append(current_author)
                insertions.append(ins_count)
                deletions.append(del_count)
        
        df = pd.DataFrame({
            'date': dates,
            'author': authors,
            'insertions': insertions,
            'deletions': deletions
        })
        df['date'] = pd.to_datetime(df['date'])
        return date_counts, author_counts, df
    except subprocess.CalledProcessError as e:
        print(f"Error getting commit stats: {e.stderr}")
        return {}, {}, pd.DataFrame()

def get_file_change_frequencies():
    """Get the number of times each file has been changed."""
    try:
        result = subprocess.run(
            ['git', 'log', '--name-only', '--pretty=format:'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        files = result.stdout.strip().split('\n')
        files = [f for f in files if f.strip() != '']
        file_counts = Counter(files)
        return file_counts
    except subprocess.CalledProcessError as e:
        print(f"Error getting file change frequencies: {e.stderr}")
        return Counter()

def plot_file_change_frequencies(file_counts):
    """Plot the files that have changed most frequently."""
    print("Plotting file change frequencies...")
    most_common = file_counts.most_common(10)
    files = [item[0] for item in most_common]
    counts = [item[1] for item in most_common]
    
    plt.figure(figsize=(12, 6))
    plt.barh(files[::-1], counts[::-1], color='purple')
    plt.xlabel('Number of Changes')
    plt.ylabel('Files')
    plt.title('Top 10 Most Frequently Changed Files')
    plt.tight_layout()
    plt.savefig(os.path.join(DEFAULT_IMAGE_DIR, 'file_change_frequencies.png'))
    plt.close()
    print(f"File change frequencies graph generated: {os.path.join(DEFAULT_IMAGE_DIR, 'file_change_frequencies.png')}")

def get_bug_fix_trends():
    """Get the number of bug fix commits over time."""
    try:
        result = subprocess.run(
            ['git', 'log', '--grep', 'fix|bug', '--pretty=format:%ad', '--date=short'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        dates = result.stdout.strip().split('\n')
        date_counts = Counter(dates)
        return date_counts
    except subprocess.CalledProcessError as e:
        print(f"Error getting bug fix trends: {e.stderr}")
        return Counter()

def plot_bug_fix_trends(bug_fix_counts):
    print("Plotting bug fix trends...")
    dates = sorted(bug_fix_counts.keys())
    counts = [bug_fix_counts[date] for date in dates]
    dates = pd.to_datetime(dates)

    plt.figure(figsize=(12, 6))
    plt.plot(dates, counts, label='Bug Fixes', color='red')
    plt.xlabel('Date')
    plt.ylabel('Number of Bug Fixes')
    plt.title('Bug Fixes Over Time')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(DEFAULT_IMAGE_DIR, 'bug_fixes_over_time.png'))
    plt.close()
    print(f"Bug fixes over time graph generated: {os.path.join(DEFAULT_IMAGE_DIR, 'bug_fixes_over_time.png')}")

def plot_commit_heatmap():
    """Plot a heatmap of commits by day of week and hour."""
    print("Plotting commit heatmap...")
    try:
        result = subprocess.run(
            ['git', 'log', '--pretty=format:%cd', '--date=format:%w %H'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        logs = result.stdout.strip().split('\n')
        weekdays = []
        hours = []
        for line in logs:
            weekday, hour = line.split(' ')
            weekdays.append(int(weekday))
            hours.append(int(hour))
        data = pd.DataFrame({'weekday': weekdays, 'hour': hours})
        heatmap_data = data.groupby(['weekday', 'hour']).size().unstack(fill_value=0)

        plt.figure(figsize=(12, 6))
        sns.heatmap(heatmap_data, cmap='YlGnBu')
        plt.xlabel('Hour of Day')
        plt.ylabel('Day of Week')
        plt.title('Commit Activity Heatmap')
        plt.yticks([0,1,2,3,4,5,6], ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'], rotation=0)
        plt.tight_layout()
        plt.savefig(os.path.join(DEFAULT_IMAGE_DIR, 'commit_heatmap.png'))
        plt.close()
        print(f"Commit heatmap generated: {os.path.join(DEFAULT_IMAGE_DIR, 'commit_heatmap.png')}")
    except subprocess.CalledProcessError as e:
        print(f"Error generating commit heatmap: {e.stderr}")

def plot_author_contributions(df):
    """Plot contributions per author."""
    print("Plotting author contributions...")
    numeric_cols = df.select_dtypes(include=['number']).columns
    author_stats = df.groupby('author')[numeric_cols].sum().reset_index()
    author_stats = author_stats.sort_values('insertions', ascending=False)

    plt.figure(figsize=(12, 6))
    plt.bar(author_stats['author'], author_stats['insertions'], label='Lines Added', color='green')
    plt.bar(author_stats['author'], author_stats['deletions'], label='Lines Deleted', color='red', bottom=author_stats['insertions'])
    plt.xlabel('Author')
    plt.ylabel('Lines of Code')
    plt.title('Lines Added and Deleted per Author')
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(DEFAULT_IMAGE_DIR, 'author_contributions.png'))
    plt.close()
    print(f"Author contributions graph generated: {os.path.join(DEFAULT_IMAGE_DIR, 'author_contributions.png')}")

def plot_git_metrics(date_counts, df):
    """Plot Git metrics such as commits over time and code churn."""
    ensure_dir_exists(DEFAULT_IMAGE_DIR)
    
    # Plot commits over time
    print("Plotting commits over time...")
    dates = sorted(date_counts.keys())
    commits = [date_counts[date] for date in dates]
    dates = pd.to_datetime(dates)
    
    plt.figure(figsize=(12, 6))
    plt.plot(dates, commits, label='Commits per Day', color='orange')
    plt.xlabel('Date')
    plt.ylabel('Number of Commits')
    plt.title('Commits Over Time')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(DEFAULT_IMAGE_DIR, 'commits_over_time.png'))
    plt.close()
    print(f"Commits over time graph generated: {os.path.join(DEFAULT_IMAGE_DIR, 'commits_over_time.png')}")
    
    # Plot code churn (insertions and deletions)
    print("Plotting code churn over time...")
    df_daily = df.groupby('date').sum().reset_index()
    plt.figure(figsize=(12, 6))
    plt.plot(df_daily['date'], df_daily['insertions'], label='Lines Added', color='green')
    plt.plot(df_daily['date'], df_daily['deletions'], label='Lines Deleted', color='red')
    plt.xlabel('Date')
    plt.ylabel('Lines of Code')
    plt.title('Code Churn Over Time')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(DEFAULT_IMAGE_DIR, 'code_churn.png'))
    plt.close()
    print(f"Code churn graph generated: {os.path.join(DEFAULT_IMAGE_DIR, 'code_churn.png')}")

def ensure_dir_exists(directory):
    """Ensure that a directory exists, creating it if necessary."""
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Created directory: {directory}")

def calculate_complexity(file_path):
    """Calculate the complexity of a file."""
    if is_binary(file_path):
        return 0
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
        content = file.read()
        branches = len(re.findall(r'\bif\b|\bfor\b|\bwhile\b|\bcase\b|\bdef\b|\bclass\b', content))
        return 1 + branches

def save_history(stats, totals, avg_complexity, code_to_comment_ratio):
    """Save project history to CSV, including complexity and code-to-comment ratio."""
    print("Saving project history...")
    fieldnames = ['timestamp', 'total_files', 'total_lines', 'total_words', 'total_chars', 'total_size', 'avg_complexity', 'code_to_comment_ratio']
    file_exists = os.path.isfile(HISTORY_FILE)

    current_entry = {
        'timestamp': datetime.now().isoformat(),
        'total_files': totals['files'].get(),
        'total_lines': totals['lines'].get(),
        'total_words': totals['words'].get(),
        'total_chars': totals['chars'].get(),
        'total_size': totals['size'].get(),
        'avg_complexity': float(avg_complexity),  
        'code_to_comment_ratio': float(code_to_comment_ratio)  
    }

    if file_exists:
        # Check if the existing headers match the expected fieldnames
        with open(HISTORY_FILE, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            existing_headers = reader.fieldnames
            if existing_headers != fieldnames:
                print("Updating CSV headers...")
                # Read all existing rows and overwrite the file with new headers
                rows = list(reader)
                with open(HISTORY_FILE, 'w', newline='') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    for row in rows:
                        # Adjust the rows to fit new headers if needed
                        writer.writerow({field: row.get(field, '') for field in fieldnames})
    
    # Append the new data
    with open(HISTORY_FILE, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()  # Write headers if file doesn't exist
        writer.writerow(current_entry)

    print("Project history updated.")

def print_stats(stats, totals, code_ratio, todos, complexity, dependencies, license):
    """Print statistics for the analyzed project."""
    print("File Type Statistics:")
    print("-" * 100)
    print(f"{'Extension':<10} {'Files':<8} {'Lines':<10} {'Words':<10} {'Characters':<12} {'Size':<12}")
    print("-" * 100)
    
    for ext, data in sorted(stats.items(), key=lambda x: x[1]['size'].get(), reverse=True):
        print(f"{ext:<10} {data['files'].get():<8} {data['lines'].get():<10} {data['words'].get():<10} {data['chars'].get():<12} {format_size(data['size'].get()):<12}")
    
    print("-" * 100)
    print(f"{'Total':<10} {totals['files'].get():<8} {totals['lines'].get():<10} {totals['words'].get():<10} {totals['chars'].get():<12} {format_size(totals['size'].get()):<12}")
    
    print(f"\nCode to Comment Ratio: {code_ratio:.2f}")
    
    print("\nTODOs and FIXMEs:")
    for todo in todos:
        print(todo)
    
    print(f"\nAverage Complexity: {complexity:.2f}")
    
    print("\nDependencies:")
    for dep, version in dependencies.items():
        print(f"{dep}: {version}")
    
    print(f"\nDetected License: {license}")

def plot_project_growth(history_data):
    """Plot project growth over time based on historical data."""
    print("Plotting project growth over time...")
    if not history_data:
        print("No historical data available.")
        return

    df = pd.DataFrame(history_data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    plt.figure(figsize=(12, 6))
    plt.plot(df['timestamp'], df['total_lines'], label='Total Lines', color='blue')
    plt.plot(df['timestamp'], df['total_files'], label='Total Files', color='green')
    plt.xlabel('Date')
    plt.ylabel('Count')
    plt.title('Project Growth Over Time')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(DEFAULT_IMAGE_DIR, 'project_growth.png'))
    plt.close()
    print(f"Project growth graph generated: {os.path.join(DEFAULT_IMAGE_DIR, 'project_growth.png')}")

def plot_code_metrics_over_time(history_data):
    """Plot code metrics (complexity, code/comment ratio) over time."""
    print("Plotting code metrics over time...")
    if not history_data:
        print("No historical data available.")
        return

    df = pd.DataFrame(history_data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    plt.figure(figsize=(12, 6))
    plt.plot(df['timestamp'], df['avg_complexity'], label='Average Complexity', color='orange')
    plt.xlabel('Date')
    plt.ylabel('Complexity')
    plt.title('Average Complexity Over Time')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(DEFAULT_IMAGE_DIR, 'average_complexity_over_time.png'))
    plt.close()
    print(f"Average complexity over time graph generated: {os.path.join(DEFAULT_IMAGE_DIR, 'average_complexity_over_time.png')}")

    plt.figure(figsize=(12, 6))
    plt.plot(df['timestamp'], df['code_to_comment_ratio'], label='Code to Comment Ratio', color='purple')
    plt.xlabel('Date')
    plt.ylabel('Ratio')
    plt.title('Code to Comment Ratio Over Time')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(DEFAULT_IMAGE_DIR, 'code_to_comment_ratio_over_time.png'))
    plt.close()
    print(f"Code to comment ratio over time graph generated: {os.path.join(DEFAULT_IMAGE_DIR, 'code_to_comment_ratio_over_time.png')}")

def plot_complexity_vs_structural_elements(file_list):
    """Plot complexity vs. number of structural elements with different colors for each file type and label each point with the filename."""
    print("Plotting complexity vs structural elements with different colors for each file type...")
    
    complexities = []
    structural_elements = []
    filenames = []
    file_types = []  # Store file types to differentiate colors

    # Define a color map for different file extensions
    color_map = {
        '.py': 'blue',
        '.rs': 'orange',
        '.js': 'green',
        '.java': 'red',
        '.c': 'purple',
        '.cpp': 'brown',
    }

    for file_path in file_list:
        if not is_binary(file_path) and file_path.endswith(tuple(color_map.keys())):
            complexity = calculate_complexity(file_path)
            num_functions, num_classes = count_structural_elements(file_path)
            total_structures = num_functions + num_classes
            if total_structures > 0:  # Only consider files with at least 1 function/class
                structural_elements.append(total_structures)
                complexities.append(complexity)
                filenames.append(os.path.basename(file_path))  # Store the filename
                ext = os.path.splitext(file_path)[1]
                file_types.append(ext)  # Store the file extension for color mapping

    # Create the scatter plot
    plt.figure(figsize=(12, 6))

    # Plot each file type with a different color
    for ext in color_map.keys():
        # Get the indices for files with the current extension
        indices = [i for i, ft in enumerate(file_types) if ft == ext]
        plt.scatter(
            [structural_elements[i] for i in indices],
            [complexities[i] for i in indices],
            color=color_map[ext],
            label=f'{ext} files'
        )

    # Add labels for each point in the scatter plot with font size 6
    for i, filename in enumerate(filenames):
        plt.text(structural_elements[i], complexities[i], filename, fontsize=10, ha='right')

    plt.xlabel('Number of Structural Elements (Functions + Classes)')
    plt.ylabel('Complexity Score')
    plt.title('Complexity vs Structural Elements by File Type')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(DEFAULT_IMAGE_DIR, 'complexity_vs_structural_elements.png'))
    plt.close()

    print(f"Complexity vs structural elements graph generated: {os.path.join(DEFAULT_IMAGE_DIR, 'complexity_vs_structural_elements.png')}")

def count_structural_elements(file_path):
    """Count the number of functions and classes in a file."""
    num_functions = 0
    num_classes = 0
    if not is_binary(file_path):
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            for line in file:
                if re.match(r'^\s*def\b', line) or re.match(r'^\s*function\b', line) or re.match(r'^\s*[a-zA-Z0-9_]+\s*\(', line):
                    num_functions += 1
                elif re.match(r'^\s*class\b', line) or re.match(r'^\s*struct\b', line):
                    num_classes += 1
    return num_functions, num_classes

def calculate_totals(stats):
    """Calculate total files, lines, words, characters, and size for non-binary files."""
    total_files = total_lines = total_words = total_chars = total_size = 0
    excluded_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tif', '.tiff']  # Exclude common image types

    for ext, data in stats.items():
        if ext not in excluded_extensions:  # Exclude binary and image files
            total_files += data['files'].get()
            total_lines += data['lines'].get()
            total_words += data['words'].get()
            total_chars += data['chars'].get()
            total_size += data['size'].get()

    return total_files, total_lines, total_words, total_chars, total_size


def generate_metrics_md(stats, totals, code_ratio, todos, avg_complexity, dependencies, license):
    """Generate a METRICS.md file summarizing the project metrics."""
    metrics_file = 'docs/METRICS.md'  # Adjusted path to save the MD file in src/docs/
    excluded_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tif', '.tiff']  # Exclude common image types

    # Calculate totals for non-binary files
    total_files, total_lines, total_words, total_chars, total_size = calculate_totals(stats)

    with open(metrics_file, 'w', encoding='utf-8') as f:
        f.write("# Project Metrics Summary\n\n")
        
        f.write("## Overview\n")
        f.write(f"- **Total Files:** {total_files}\n")
        f.write(f"- **Total Lines:** {total_lines}\n")
        f.write(f"- **Total Words:** {total_words}\n")
        f.write(f"- **Total Characters:** {total_chars}\n")
        f.write(f"- **Total Size:** {format_size(total_size)}\n")
        f.write(f"- **Code to Comment Ratio:** {code_ratio:.2f}\n")
        f.write(f"- **Average Complexity:** {avg_complexity:.2f}\n")
        f.write(f"- **Detected License:** {license}\n\n")

        # File Type Statistics (Excluding binary and image files)
        f.write("## File Type Statistics\n\n")
        f.write("| Extension | Files | Lines | Words | Characters | Size |\n")
        f.write("|-----------|-------|-------|-------|------------|------|\n")
        for ext, data in sorted(stats.items(), key=lambda x: x[1]['size'].get(), reverse=True):
            if ext not in excluded_extensions:  # Skip binary and image file extensions
                extension = ext if ext else "No Extension"
                f.write(f"| {extension} | {data['files'].get()} | {data['lines'].get()} | {data['words'].get()} | {data['chars'].get()} | {format_size(data['size'].get())} |\n")

        # Dependencies
        f.write("\n## Dependencies\n\n")
        if dependencies:
            for dep, version in dependencies.items():
                f.write(f"- {dep}: {version}\n")
        else:
            f.write("- No dependencies found.\n")

        # TODOs and FIXMEs
        f.write("\n## TODOs and FIXMEs\n\n")
        if todos:
            for todo in todos:
                f.write(f"- {todo}\n")
        else:
            f.write("- No TODOs or FIXMEs found.\n")

        # Visualizations (Include all PNGs from the project_metrics_images directory)
        f.write("\n## Visualizations\n\n")
        png_files = sorted([f for f in os.listdir(DEFAULT_IMAGE_DIR) if f.endswith('.png')])
        if png_files:
            for png_file in png_files:
                # Format title from file name
                title = os.path.splitext(png_file)[0].replace('_', ' ').title()
                # Adjust the path to the images with ../ to navigate from src/docs/
                f.write(f"### {title}\n")
                f.write(f"![{title}](../project_metrics_images/{png_file})\n\n")
        else:
            f.write("- No visualizations found.\n")

    print(f"Metrics markdown file generated: {metrics_file}")




def load_history_data():
    """Load project history from CSV file and return it as a list of dictionaries."""
    history_data = []

    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    # Convert numerical fields back to numbers
                    row['total_files'] = int(row['total_files'])
                    row['total_lines'] = int(row['total_lines'])
                    row['total_words'] = int(row['total_words'])
                    row['total_chars'] = int(row['total_chars'])
                    row['total_size'] = int(row['total_size'])
                    row['avg_complexity'] = float(row['avg_complexity'])
                    row['code_to_comment_ratio'] = float(row['code_to_comment_ratio'])
                    history_data.append(row)
        except Exception as e:
            print(f"Error loading history data: {e}")
    
    return history_data

def plot_dependency_graph(dependencies):
    """Plot a graph of project dependencies."""
    print("Plotting dependency graph...")
    G = nx.DiGraph()

    for dep, version in dependencies.items():
        G.add_edge('Project', dep)

    plt.figure(figsize=(12, 8))
    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=True, node_color='skyblue', edge_color='gray', node_size=3000, font_size=12, font_weight='bold')
    plt.title('Project Dependency Graph')
    plt.savefig(os.path.join(DEFAULT_IMAGE_DIR, 'dependency_graph.png'))
    plt.close()
    print(f"Dependency graph generated: {os.path.join(DEFAULT_IMAGE_DIR, 'dependency_graph.png')}")

def plot_file_type_distribution(stats):
    """Plot the distribution of file types in the project."""
    print("Plotting file type distribution...")
    extensions = []
    file_counts = []
    
    for ext, data in stats.items():
        extensions.append(ext if ext else '[no extension]')
        file_counts.append(data['files'].get())
    
    plt.figure(figsize=(10, 6))
    plt.bar(extensions, file_counts, color='skyblue')
    plt.xlabel('File Extensions')
    plt.ylabel('Number of Files')
    plt.title('Distribution of File Types')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(DEFAULT_IMAGE_DIR, 'file_type_distribution.png'))
    plt.close()
    print(f"File type distribution graph generated: {os.path.join(DEFAULT_IMAGE_DIR, 'file_type_distribution.png')}")


def main():
    print("Starting project metrics analysis...")

    root_dir = '.'  # Current directory

    try:
        repo = Repo(root_dir)
        print("Analyzing repository using Git...")
    except Exception:
        print("Not a Git repository. Exiting.")
        return

    # Ensure the image directory exists
    ensure_dir_exists(DEFAULT_IMAGE_DIR)

    # Use Git to get the list of files
    file_list = get_git_tracked_files()
    file_list = [os.path.join(root_dir, f) for f in file_list]

    stats, totals, todos = analyze_chunk(file_list)

    code_lines, comment_lines, code_ratio = calculate_code_to_comment_ratio(root_dir)

    print("Calculating average complexity...")
    complexity_sum = sum(calculate_complexity(file_path) for file_path in file_list if file_path.endswith(('.rs', '.py', '.toml', '.js', '.java', '.c', '.cpp')))
    total_files = totals['files'].get()
    avg_complexity = complexity_sum / total_files if total_files > 0 else 0

    dependencies = analyze_dependencies()
    license = detect_license()

    print_stats(stats, totals, code_ratio, todos, avg_complexity, dependencies, license)

    save_history(stats, totals, avg_complexity, code_ratio)

    # Load history data and plot project growth and metrics over time
    history_data = load_history_data()
    plot_project_growth(history_data)
    plot_code_metrics_over_time(history_data)

    # Plot complexity vs structural elements
    plot_complexity_vs_structural_elements(file_list)

    # Plot file type distribution
    plot_file_type_distribution(stats)

    # Generate Git metrics
    date_counts, author_counts, df = get_git_commit_stats()
    plot_git_metrics(date_counts, df)
    plot_author_contributions(df)
    plot_commit_heatmap()
    file_change_counts = get_file_change_frequencies()
    plot_file_change_frequencies(file_change_counts)
    bug_fix_counts = get_bug_fix_trends()
    plot_bug_fix_trends(bug_fix_counts)

    # Plot additional code metrics and dependency graph
    plot_dependency_graph(dependencies)

    # Generate METRICS.md file
    generate_metrics_md(stats, totals, code_ratio, todos, avg_complexity, dependencies, license)

# Ensure direct execution
if __name__ == "__main__":
    main()
    
    
