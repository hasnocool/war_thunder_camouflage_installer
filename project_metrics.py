import os
import re
import csv
import json
from collections import defaultdict, Counter
from datetime import datetime
import matplotlib.pyplot as plt
from git import Repo
import toml
import magic
import mmap
import networkx as nx
import subprocess
import pyperclip
import argparse

# File for storing historical data
HISTORY_FILE = 'project_metrics_history.csv'
CACHE_FILE = 'project_metrics_cache.json'
DEFAULT_IMAGE_DIR = 'project_metrics_images'  # New constant for default image directory

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

def process_file(file_path, git_repo):
    """Process each file and gather statistics."""
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    print(f"Processing file: {file_path}")
    
    try:
        file_size = os.path.getsize(file_path)
        lines, words, chars = count_lines_words_chars(file_path)

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
    """Analyze project dependencies from Cargo.toml."""
    print("Analyzing dependencies from Cargo.toml...")
    cargo_file = 'Cargo.toml'
    if os.path.exists(cargo_file):
        try:
            with open(cargo_file, 'r') as file:
                cargo_data = toml.load(file)
                return cargo_data.get('dependencies', {})
        except Exception as e:
            print(f"Error reading {cargo_file}: {e}")
            return {}
    else:
        print("Cargo.toml not found.")
        return {}


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
        "src/ui/handlers/utility_handlers.rs", "src/ui/layout.rs", "src/ui/mod.rs", "src/war_thunder_utils.rs"
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


def ensure_dir_exists(directory):
    """Ensure that a directory exists, creating it if necessary."""
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Created directory: {directory}")

def plot_history():
    """Plot and save a comprehensive project history as an image."""
    print("Plotting comprehensive project history...")
    dates, files, lines, size, words, chars, complexities, code_to_comment_ratios = [], [], [], [], [], [], [], []
    
    with open(HISTORY_FILE, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            dates.append(datetime.fromisoformat(row['timestamp']))
            files.append(int(row['total_files']))
            lines.append(int(row['total_lines']))
            size.append(int(row['total_size']))
            words.append(int(row['total_words']))
            chars.append(int(row['total_chars']))
            complexities.append(float(row.get('avg_complexity', 0)))
            code_to_comment_ratios.append(float(row.get('code_to_comment_ratio', 0)))
    
    fig, axs = plt.subplots(3, 2, figsize=(15, 20))
    
    # Total Files and Lines
    axs[0, 0].plot(dates, files, label='Total Files', color='purple')
    axs[0, 0].set_ylabel('Files')
    axs[0, 0].set_title('Total Files Over Time')
    ax2 = axs[0, 0].twinx()
    ax2.plot(dates, lines, label='Total Lines', color='orange')
    ax2.set_ylabel('Lines')
    axs[0, 0].legend(loc='upper left')
    ax2.legend(loc='upper right')
    
    # Project Size
    axs[0, 1].plot(dates, [s / 1024 for s in size], label='Total Size (KB)', color='green')
    axs[0, 1].set_ylabel('Size (KB)')
    axs[0, 1].set_title('Project Size Over Time')
    axs[0, 1].legend()
    
    # Words and Characters
    axs[1, 0].plot(dates, words, label='Total Words', color='blue')
    axs[1, 0].set_ylabel('Words')
    axs[1, 0].set_title('Total Words Over Time')
    ax2 = axs[1, 0].twinx()
    ax2.plot(dates, chars, label='Total Characters', color='red')
    ax2.set_ylabel('Characters')
    axs[1, 0].legend(loc='upper left')
    ax2.legend(loc='upper right')
    
    # Average Complexity
    axs[1, 1].plot(dates, complexities, label='Average Complexity', color='purple')
    axs[1, 1].set_ylabel('Complexity')
    axs[1, 1].set_title('Average Complexity Over Time')
    axs[1, 1].legend()
    
    # Code to Comment Ratio
    axs[2, 0].plot(dates, code_to_comment_ratios, label='Code to Comment Ratio', color='brown')
    axs[2, 0].set_ylabel('Ratio')
    axs[2, 0].set_title('Code to Comment Ratio Over Time')
    axs[2, 0].legend()
    
    # Lines per File
    lines_per_file = [l / f if f > 0 else 0 for l, f in zip(lines, files)]
    axs[2, 1].plot(dates, lines_per_file, label='Lines per File', color='green')
    axs[2, 1].set_ylabel('Lines/File')
    axs[2, 1].set_title('Average Lines per File Over Time')
    axs[2, 1].legend()
    
    for ax in axs.flat:
        ax.set_xlabel('Date')
        ax.grid(True)
    
    plt.tight_layout()
    ensure_dir_exists(DEFAULT_IMAGE_DIR)
    plt.savefig(os.path.join(DEFAULT_IMAGE_DIR, 'project_growth.png'))
    plt.close()
    print(f"Comprehensive project growth chart saved as '{os.path.join(DEFAULT_IMAGE_DIR, 'project_growth.png')}'")

def calculate_complexity(file_path):
    """Calculate the complexity of a file."""
    if is_binary(file_path):
        return 0
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
        content = file.read()
        branches = len(re.findall(r'\bif\b|\bfor\b|\bwhile\b|\bcase\b', content))
        return 1 + branches

def analyze_code_complexity(file_path):
    """Analyze the complexity of a file (Python, Rust, TOML, etc.)."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
        content = file.read()

    loc = len(content.splitlines())

    if file_path.endswith('.py'):
        functions = len(re.findall(r'def\s+\w+\s*\(', content))
        classes = len(re.findall(r'class\s+\w+', content))
        complexity = content.count('if') + content.count('for') + content.count('while') + content.count('except') + functions + classes
    elif file_path.endswith('.rs'):
        functions = len(re.findall(r'fn\s+\w+\s*\(', content))
        structs = len(re.findall(r'struct\s+\w+', content))
        impls = len(re.findall(r'impl\s+', content))
        complexity = content.count('if') + content.count('for') + content.count('while') + content.count('match') + functions + structs + impls
    elif file_path.endswith('.toml'):
        # For TOML, we only care about the number of sections and key-value pairs
        sections = len(re.findall(r'\[.*?\]', content))
        key_values = len(re.findall(r'=', content))
        complexity = sections + key_values
    else:
        # For other file types, just calculate lines of code and a basic complexity score
        complexity = content.count('if') + content.count('for') + content.count('while')

    return {
        'loc': loc,
        'functions': functions if 'functions' in locals() else 0,
        'classes_or_structs': classes if 'classes' in locals() else structs if 'structs' in locals() else 0,
        'estimated_complexity': complexity
    }

def generate_dependency_graph(base_dir):
    """Generate a dependency graph of Python and Rust files in the project."""
    G = nx.DiGraph()
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith(('.py', '.rs')):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if file.endswith('.py'):
                            imports = re.findall(r'from\s+(\w+)\s+import', content)
                            imports += re.findall(r'import\s+(\w+)', content)
                            for imp in imports:
                                G.add_edge(file, f"{imp}.py")
                        elif file.endswith('.rs'):
                            imports = re.findall(r'use\s+([\w:]+)', content)
                            for imp in imports:
                                G.add_edge(file, f"{imp.split(':')[-1]}.rs")
                except Exception as e:
                    print(f"Error processing file {file_path}: {e}")
    return G


def plot_code_metrics(metrics):
    """Plot various code metrics for Python, Rust, TOML, and other files."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    sizes = [m['loc'] for m in metrics.values()]
    labels = list(metrics.keys())
    colors = ['blue' if l.endswith('.py') else 'red' if l.endswith('.rs') else 'green' for l in labels]  # Different colors for .py, .rs, and others
    ax1.bar(labels, sizes, color=colors)
    ax1.set_title('File Sizes (Lines of Code)')
    ax1.set_xlabel('Files')
    ax1.set_ylabel('Lines of Code')
    plt.setp(ax1.get_xticklabels(), rotation=45, ha='right')

    x = [m['functions'] + m['classes_or_structs'] for m in metrics.values()]
    y = [m['estimated_complexity'] for m in metrics.values()]
    ax2.scatter(x, y, c=colors)
    for i, label in enumerate(labels):
        ax2.annotate(label, (x[i], y[i]))
    ax2.set_title('Complexity vs. Functions/Classes/Structs')
    ax2.set_xlabel('Number of Functions + Classes/Structs')
    ax2.set_ylabel('Estimated Complexity')

    plt.tight_layout()
    ensure_dir_exists(DEFAULT_IMAGE_DIR)
    plt.savefig(os.path.join(DEFAULT_IMAGE_DIR, 'code_metrics.png'))
    plt.close()
    print(f"Code metrics graph generated: {os.path.join(DEFAULT_IMAGE_DIR, 'code_metrics.png')}")


def plot_dependency_graph(G):
    """Plot the dependency graph for Python and Rust files."""
    plt.figure(figsize=(12, 8))
    pos = nx.spring_layout(G)
    node_colors = ['lightblue' if node.endswith('.py') else 'lightcoral' for node in G.nodes()]
    nx.draw(G, pos, with_labels=True, node_color=node_colors, 
            node_size=2000, font_size=8, arrows=True)
    plt.title("Project Dependency Graph (Blue: Python, Red: Rust)")
    ensure_dir_exists(DEFAULT_IMAGE_DIR)
    plt.savefig(os.path.join(DEFAULT_IMAGE_DIR, 'dependency_graph.png'))
    plt.close()
    print(f"Dependency graph generated: {os.path.join(DEFAULT_IMAGE_DIR, 'dependency_graph.png')}")


def analyze_rust_specific_metrics(file_path):
    """Analyze Rust-specific metrics."""
    try:
        # Attempt to read the file using utf-8 encoding
        with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
            content = file.read()
    except UnicodeDecodeError:
        # Fallback to latin-1 encoding if utf-8 fails
        with open(file_path, 'r', encoding='latin-1', errors='replace') as file:
            content = file.read()
    
    unsafe_blocks = len(re.findall(r'unsafe\s*\{', content))
    lifetimes = len(re.findall(r"'[a-z]+", content))
    trait_implementations = len(re.findall(r'impl\s+.*for\s+', content))
    
    return {
        'unsafe_blocks': unsafe_blocks,
        'lifetimes': lifetimes,
        'trait_implementations': trait_implementations
    }


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

def generate_metrics_md(stats, totals, code_ratio, todos, avg_complexity, dependencies, license):
    """Generate a METRICS.md file with project statistics and images."""
    print("Generating METRICS.md file...")
    
    md_content = f"""# Project Metrics

## Overview
- **Total Files:** {totals['files']}
- **Total Lines:** {totals['lines']}
- **Total Words:** {totals['words']}
- **Total Characters:** {totals['chars']}
- **Total Size:** {format_size(totals['size'])}
- **Code to Comment Ratio:** {code_ratio:.2f}
- **Average Complexity:** {avg_complexity:.2f}
- **Detected License:** {license}

## File Type Statistics

| Extension | Files | Lines | Words | Characters | Size |
|-----------|-------|-------|-------|------------|------|
"""
    
    for ext, data in sorted(stats.items(), key=lambda x: x[1]['size'], reverse=True):
        md_content += f"| {ext} | {data['files']} | {data['lines']} | {data['words']} | {data['chars']} | {format_size(data['size'])} |\n"
    
    md_content += f"""
## Dependencies

"""
    for dep, version in dependencies.items():
        md_content += f"- {dep}: {version}\n"
    
    md_content += f"""
## TODOs and FIXMEs

"""
    for todo in todos:
        md_content += f"- {todo}\n"
    
    md_content += f"""
## Visualizations

### Project Growth
![Project Growth](project_metrics_images/project_growth.png)

### Code Metrics
![Code Metrics](project_metrics_images/code_metrics.png)

### Dependency Graph
![Dependency Graph](project_metrics_images/dependency_graph.png)
"""

    with open('METRICS.md', 'w') as md_file:
        md_file.write(md_content)
    
    print("METRICS.md file generated successfully.")

def main():
    root_dir = '.'  # Current directory

    try:
        repo = Repo(root_dir)
        print("Analyzing changes since last commit...")
    except Exception:
        repo = None
        print("Not a Git repository. Analyzing all files...")

    stats, totals, todos = analyze_project(root_dir, repo)

    code_lines, comment_lines, code_ratio = calculate_code_to_comment_ratio(root_dir)

    print("Calculating average complexity...")
    complexity_sum = sum(calculate_complexity(os.path.join(root, file))
                         for root, _, files in os.walk(root_dir)
                         for file in files if file.endswith(('.rs', '.py', '.toml')))
    avg_complexity = complexity_sum / totals['files'] if totals['files'] > 0 else 0

    dependencies = analyze_dependencies()
    license = detect_license()

    print_stats(stats, totals, code_ratio, todos, avg_complexity, dependencies, license)

    save_history(stats, totals, avg_complexity, code_ratio)
    plot_history()

    # Analyze code complexity and dependencies for files
    selected_files = []
    for root, _, files in os.walk(root_dir):
        selected_files.extend([os.path.join(root, f) for f in files if f.endswith(('.py', '.rs', '.toml'))])

    metrics = {}
    rust_specific_metrics = {}
    for file in selected_files:
        if file.endswith(('.py', '.rs', '.toml')):
            metrics[file] = analyze_code_complexity(file)
            if file.endswith('.rs'):
                rust_specific_metrics[file] = analyze_rust_specific_metrics(file)

    plot_code_metrics(metrics)
    print(f"\nCode metrics graph generated: {os.path.join(DEFAULT_IMAGE_DIR, 'code_metrics.png')}\n")

    dep_graph = generate_dependency_graph(root_dir)
    plot_dependency_graph(dep_graph)
    print(f"Dependency graph generated: {os.path.join(DEFAULT_IMAGE_DIR, 'dependency_graph.png')}\n")

    # Generate METRICS.md file
    generate_metrics_md(stats, totals, code_ratio, todos, avg_complexity, dependencies, license)

if __name__ == "__main__":
    main()