import os
import re
import csv
import json
from collections import defaultdict
from datetime import datetime
import matplotlib.pyplot as plt
from git import Repo
import toml
import magic
import mmap

# File for storing historical data
HISTORY_FILE = 'project_metrics_history.csv'
CACHE_FILE = 'project_metrics_cache.json'

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
            lines = content.splitlines()  # Split the content into lines
            words = content.split()       # Split the content into words
            chars = len(content)          # Total number of characters
        return len(lines), len(words), chars
    except Exception as e:
        print(f"Error counting lines, words, and characters for {file_path}: {str(e)}")
        return 0, 0, os.path.getsize(file_path)


def process_file(file_path, git_repo):
    """Process each file and gather statistics."""
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    print(f"Processing file: {file_path}")
    
    try:
        file_size = os.path.getsize(file_path)
        lines, words, chars = count_lines_words_chars(file_path)

        # If the file is binary, don't count lines and words
        if is_binary(file_path):
            return ext, {'lines': 0, 'words': 0, 'chars': file_size, 'size': file_size, 'todos': []}
        
        todos = find_todos(file_path) if not is_binary(file_path) else []
        return ext, {'lines': lines, 'words': words, 'chars': chars, 'size': file_size, 'todos': todos}
    except Exception as e:
        print(f"Error processing file: {file_path}. Error: {str(e)}")
        return ext, None


def analyze_chunk(chunk, git_repo):
    """Analyze a chunk of files and return stats and todos."""
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
    
    print(f"Analyzing chunk of {len(chunk)} files...")
    
    for file_path in chunk:
        ext, data = process_file(file_path, git_repo)
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

def analyze_project(root_dir, git_repo=None):
    """Analyze the entire project directory."""
    print(f"Analyzing project in directory: {root_dir}")
    
    allowed_files_and_dirs = [
        "build_script.py", "Cargo.toml", "CHANGE.log", "check.py", 
        "print_project.py", "project_metrics.py", "README.MACOSX.md", "README.md", 
        "TODO.md", "TREE.md",
        "src/data.rs", "src/database.rs", "src/experimental.rs", "src/file_operations.rs", 
        "src/image_utils.rs", "src/main.rs", "src/path_utils.rs", "src/tags.rs",
        "src/ui/app.rs", "src/ui/components.rs", "src/ui/handlers/database_handlers.rs", 
        "src/ui/handlers/file_handlers.rs", "src/ui/handlers/general_handlers.rs", 
        "src/ui/handlers/image_handlers.rs", "src/ui/handlers/mod.rs", 
        "src/ui/handlers/navigation_handlers.rs", "src/ui/handlers/popup_handlers.rs", 
        "src/ui/handlers/utility_handlers.rs", "src/ui/layout.rs", "src/ui/mod.rs"
    ]
    
    file_list = [
        os.path.join(root_dir, f) if not f.startswith('src/') else os.path.join(root_dir, f.replace('/', os.sep))
        for f in allowed_files_and_dirs
    ]
    
    print(f"Total number of files found: {len(file_list)}")
    
    combined_stats, combined_totals, combined_todos = analyze_chunk(file_list, git_repo)
    
    print("Analysis complete.")
    
    stats_dict = {ext: {k: v.get() for k, v in stat.items()} for ext, stat in combined_stats.items()}
    totals_dict = {k: v.get() for k, v in combined_totals.items()}
    
    return stats_dict, totals_dict, combined_todos


def is_file_changed(repo, file_path):
    """Check if a file has changed in the repository."""
    try:
        return bool(repo.git.diff('HEAD~1..HEAD', '--', file_path))
    except Exception:
        return True

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
    
    def process_file(file_path):
        if not is_binary(file_path):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                in_block_comment = False
                for line in file:
                    line = line.strip()
                    if line.startswith('/*'):
                        in_block_comment = True
                        comment_lines.increment()
                    elif line.endswith('*/'):
                        in_block_comment = False
                        comment_lines.increment()
                    elif in_block_comment or line.startswith('//') or line.startswith('#'):
                        comment_lines.increment()
                    elif line:
                        code_lines.increment()
    
    file_list = [os.path.join(dirpath, f) for dirpath, _, filenames in os.walk(root_dir) 
                 for f in filenames if f.endswith(('.rs', '.py'))]
    
    for file_path in file_list:
        process_file(file_path)
    
    ratio = code_lines.get() / comment_lines.get() if comment_lines.get() > 0 else float('inf')
    print(f"Code-to-comment ratio calculated: {ratio:.2f}")
    return code_lines.get(), comment_lines.get(), ratio

def load_cache():
    """Load cache from the file."""
    print("Loading cache...")
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_cache(cache):
    """Save cache to the file."""
    print("Saving cache...")
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)

def save_history(stats, totals, avg_complexity, code_to_comment_ratio):
    """Save project history to CSV, including complexity and code-to-comment ratio."""
    print("Saving project history...")
    fieldnames = ['timestamp', 'total_files', 'total_lines', 'total_words', 'total_chars', 'total_size', 'avg_complexity', 'code_to_comment_ratio']
    file_exists = os.path.isfile(HISTORY_FILE)
    
    current_entry = {
        'timestamp': datetime.now().isoformat(),
        'total_files': totals['files'],
        'total_lines': totals['lines'],
        'total_words': totals['words'],
        'total_chars': totals['chars'],
        'total_size': totals['size'],
        'avg_complexity': float(avg_complexity),  # Ensure complexity is saved as float
        'code_to_comment_ratio': float(code_to_comment_ratio)  # Ensure ratio is saved as float
    }
    
    if file_exists:
        with open(HISTORY_FILE, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            last_entry = next(reversed(list(reader)), None)
        
        if last_entry:
            # Compare with the last entry to avoid duplicate entries
            if all(float(current_entry[key]) == float(last_entry[key]) for key in fieldnames if key != 'timestamp'):
                print("No changes detected. Skipping history update.")
                return
    
    with open(HISTORY_FILE, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow(current_entry)
    
    print("Project history updated.")



def plot_history():
    """Plot and save project history as an image."""
    print("Plotting project history...")
    dates, files, lines, size, complexities, code_to_comment_ratios = [], [], [], [], [], []
    
    # Read the project history CSV file
    with open(HISTORY_FILE, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            dates.append(datetime.fromisoformat(row['timestamp']))
            files.append(int(row['total_files']))
            lines.append(int(row['total_lines']))
            size.append(int(row['total_size']))
            complexities.append(float(row.get('avg_complexity', 0)))  # Ensure avg_complexity is read as float
            code_to_comment_ratios.append(float(row.get('code_to_comment_ratio', 0)))  # Ensure ratio is read as float
    
    # Create subplots for files, lines, size, complexity, and code-to-comment ratio
    fig, (ax1, ax2, ax3, ax4, ax5) = plt.subplots(5, 1, figsize=(12, 20))
    
    # Plot total files over time (separate plot)
    ax1.plot(dates, files, label='Total Files', color='purple')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Files')
    ax1.set_title('Total Files Over Time')
    ax1.legend()
    ax1.grid(True)
    
    # Plot total lines over time
    ax2.plot(dates, lines, label='Total Lines', color='orange')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Lines')
    ax2.set_title('Total Lines Over Time')
    ax2.legend()
    ax2.grid(True)
    
    # Plot project size over time
    ax3.plot(dates, size, label='Total Size', color='green')
    ax3.set_xlabel('Date')
    ax3.set_ylabel('Size (bytes)')
    ax3.set_title('Project Size Over Time')
    ax3.legend()
    ax3.grid(True)

    # Plot average complexity over time
    ax4.plot(dates, complexities, label='Average Complexity', color='red')
    ax4.set_xlabel('Date')
    ax4.set_ylabel('Complexity')
    ax4.set_title('Average Complexity Over Time')
    ax4.legend()
    ax4.grid(True)

    # Plot code-to-comment ratio over time
    ax5.plot(dates, code_to_comment_ratios, label='Code to Comment Ratio', color='blue')
    ax5.set_xlabel('Date')
    ax5.set_ylabel('Ratio')
    ax5.set_title('Code to Comment Ratio Over Time')
    ax5.legend()
    ax5.grid(True)
    
    plt.tight_layout()
    plt.savefig('project_growth.png')
    plt.close()
    print("Project growth chart saved as 'project_growth.png'")



def calculate_complexity(file_path):
    """Calculate the complexity of a file."""
    if is_binary(file_path):
        return 0
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
        content = file.read()
        branches = len(re.findall(r'\bif\b|\bfor\b|\bwhile\b|\bcase\b', content))
        return 1 + branches

def analyze_dependencies():
    """Analyze project dependencies from Cargo.toml."""
    print("Analyzing dependencies from Cargo.toml...")
    cargo_file = 'Cargo.toml'
    if os.path.exists(cargo_file):
        with open(cargo_file, 'r') as file:
            cargo_data = toml.load(file)
            return cargo_data.get('dependencies', {})
    return {}

def detect_license():
    """Detect the project license."""
    print("Detecting project license...")
    license_files = ['LICENSE', 'LICENSE.txt', 'LICENSE.md']
    for license_file in license_files:
        if os.path.exists(license_file):
            with open(license_file, 'r') as file:
                content = file.read()
                if 'MIT' in content:
                    return 'MIT License'
                elif 'Apache' in content:
                    return 'Apache License'
                elif 'GPL' in content:
                    return 'GPL License'
    return 'License not detected'

def format_size(size_in_bytes):
    """Format the size in bytes to a human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} PB"

def print_stats(stats, totals, code_ratio, todos, complexity, dependencies, license):
    """Print statistics for the analyzed project."""
    print("File Type Statistics:")
    print("-" * 100)
    print(f"{'Extension':<10} {'Files':<8} {'Lines':<10} {'Words':<10} {'Characters':<12} {'Size':<12}")
    print("-" * 100)
    
    for ext, data in sorted(stats.items(), key=lambda x: x[1]['size'], reverse=True):
        print(f"{ext:<10} {data['files']:<8} {data['lines']:<10} {data['words']:<10} {data['chars']:<12} {format_size(data['size']):<12}")
    
    print("-" * 100)
    print(f"{'Total':<10} {totals['files']:<8} {totals['lines']:<10} {totals['words']:<10} {totals['chars']:<12} {format_size(totals['size']):<12}")
    
    print(f"\nCode to Comment Ratio: {code_ratio:.2f}")
    
    print("\nTODOs and FIXMEs:")
    for todo in todos:
        print(todo)
    
    print(f"\nAverage Complexity: {complexity:.2f}")
    
    print("\nDependencies:")
    for dep, version in dependencies.items():
        print(f"{dep}: {version}")
    
    print(f"\nDetected License: {license}")


def main():
    root_dir = '.'  # Current directory
    
    try:
        repo = Repo(root_dir)
        print("Analyzing changes since last commit...")
    except Exception:
        repo = None
        print("Not a Git repository. Analyzing all files...")
    
    stats, totals, todos = analyze_project(root_dir, repo)
    
    # Calculate code-to-comment ratio
    code_lines, comment_lines, code_ratio = calculate_code_to_comment_ratio(root_dir)
    
    # Calculate average complexity
    print("Calculating average complexity...")
    complexity_sum = sum(calculate_complexity(os.path.join(root, file))
                         for root, _, files in os.walk(root_dir)
                         for file in files if file.endswith(('.rs', '.py')))
    avg_complexity = complexity_sum / totals['files'] if totals['files'] > 0 else 0
    
    dependencies = analyze_dependencies()
    license = detect_license()
    
    print_stats(stats, totals, code_ratio, todos, avg_complexity, dependencies, license)
    
    # Save history including complexity and code-to-comment ratio
    save_history(stats, totals, avg_complexity, code_ratio)
    plot_history()
    
    print("\nProject growth chart saved as 'project_growth.png'")



if __name__ == "__main__":
    main()




