# Project Metrics

## Overview
- **Total Files:** 63
- **Total Lines:** 3990
- **Total Words:** 14111
- **Total Characters:** 171263
- **Total Size:** 172.67 KB
- **Code to Comment Ratio:** 17.51
- **Average Complexity:** 6.48
- **Detected License:** License file not found

## File Type Statistics

| Extension | Files | Lines | Words | Characters | Size |
|-----------|-------|-------|-------|------------|------|
| .py | 4 | 1702 | 5760 | 64276 | 64.43 KB |
| .rs | 21 | 1599 | 4468 | 54259 | 54.54 KB |
|  | 29 | 170 | 417 | 24017 | 25.05 KB |
| .md | 5 | 406 | 3151 | 23530 | 23.48 KB |
| .csv | 1 | 39 | 39 | 3243 | 3.21 KB |
| .log | 1 | 45 | 175 | 1273 | 1.29 KB |
| .toml | 1 | 28 | 98 | 636 | 664.00 B |
| .bat | 1 | 1 | 3 | 29 | 30.00 B |

## Dependencies

- eframe: {'version': '0.22.0', 'features': ['persistence']}
- egui: 0.22.0
- rusqlite: {'version': '0.29.0', 'features': ['bundled']}
- ehttp: 0.2.0
- image: 0.24.6
- base64: 0.21.0
- rfd: 0.9
- zip: 0.5
- reqwest: {'version': '0.11', 'features': ['blocking']}
- tempfile: 3.3
- thiserror: 1.0
- parking_lot: 0.12
- dirs: 5.0
- rayon: 1.5
- serde: {'version': '1.0', 'features': ['derive']}
- serde_json: 1.0
- native-dialog: 0.6.3

## TODOs and FIXMEs

- .\build_script.py:187: "TODO.md": "todo list",
- .\build_script.py:218: code, output, _ = run_command(f"git diff {remote_branch} -- src/ Cargo.toml CHANGE.log TODO.md README.md", verbose=True)
- .\build_script.py:271: Based on the following changes in the source files, Cargo.toml, CHANGE.log, TODO.md, and README.md,
- .\build_script.py:278: - Revised TODO.md, removing completed tasks and adding new features.
- .\build_script.py:414: """Update the README.md, TODO.md, and CHANGE.log with new changes."""
- .\build_script.py:422: "TODO.md": "ToDo List",
- .\build_script.py:441: subprocess.run(["git", "add", "README.md", "TODO.md", "CHANGE.log"], check=True)
- .\project_metrics.py:239: """Find TODO and FIXME comments in files."""
- .\project_metrics.py:244: if 'TODO' in line or 'FIXME' in line:
- .\project_metrics.py:668: print("\nTODOs and FIXMEs:")
- .\project_metrics.py:713: ## TODOs and FIXMEs
- .\docs\METRICS.md:46: ## TODOs and FIXMEs
- .\docs\METRICS.md:48: - .\build_script.py:187: "TODO.md": "todo list",
- .\docs\METRICS.md:49: - .\build_script.py:218: code, output, _ = run_command(f"git diff {remote_branch} -- src/ Cargo.toml CHANGE.log TODO.md README.md", verbose=True)
- .\docs\METRICS.md:50: - .\build_script.py:271: Based on the following changes in the source files, Cargo.toml, CHANGE.log, TODO.md, and README.md,
- .\docs\METRICS.md:51: - .\build_script.py:278: - Revised TODO.md, removing completed tasks and adding new features.
- .\docs\METRICS.md:52: - .\build_script.py:414: """Update the README.md, TODO.md, and CHANGE.log with new changes."""
- .\docs\METRICS.md:53: - .\build_script.py:422: "TODO.md": "ToDo List",
- .\docs\METRICS.md:54: - .\build_script.py:441: subprocess.run(["git", "add", "README.md", "TODO.md", "CHANGE.log"], check=True)
- .\docs\METRICS.md:55: - .\project_metrics.py:239: """Find TODO and FIXME comments in files."""
- .\docs\METRICS.md:56: - .\project_metrics.py:244: if 'TODO' in line or 'FIXME' in line:
- .\docs\METRICS.md:57: - .\project_metrics.py:668: print("\nTODOs and FIXMEs:")
- .\docs\METRICS.md:58: - .\project_metrics.py:713: ## TODOs and FIXMEs
- .\docs\METRICS.md:59: - .\docs\METRICS.md:46: ## TODOs and FIXMEs
- .\docs\METRICS.md:60: - .\docs\METRICS.md:48: - .\build_script.py:187: "TODO.md": "todo list",
- .\docs\METRICS.md:61: - .\docs\METRICS.md:49: - .\build_script.py:218: code, output, _ = run_command(f"git diff {remote_branch} -- src/ Cargo.toml CHANGE.log TODO.md README.md", verbose=True)
- .\docs\METRICS.md:62: - .\docs\METRICS.md:50: - .\build_script.py:271: Based on the following changes in the source files, Cargo.toml, CHANGE.log, TODO.md, and README.md,
- .\docs\METRICS.md:63: - .\docs\METRICS.md:51: - .\build_script.py:278: - Revised TODO.md, removing completed tasks and adding new features.
- .\docs\METRICS.md:64: - .\docs\METRICS.md:52: - .\build_script.py:414: """Update the README.md, TODO.md, and CHANGE.log with new changes."""
- .\docs\METRICS.md:65: - .\docs\METRICS.md:53: - .\build_script.py:422: "TODO.md": "ToDo List",
- .\docs\METRICS.md:66: - .\docs\METRICS.md:54: - .\build_script.py:441: subprocess.run(["git", "add", "README.md", "TODO.md", "CHANGE.log"], check=True)
- .\docs\METRICS.md:67: - .\docs\METRICS.md:55: - .\project_metrics.py:239: """Find TODO and FIXME comments in files."""
- .\docs\METRICS.md:68: - .\docs\METRICS.md:56: - .\project_metrics.py:244: if 'TODO' in line or 'FIXME' in line:
- .\docs\METRICS.md:69: - .\docs\METRICS.md:57: - .\project_metrics.py:622: print("\nTODOs and FIXMEs:")
- .\docs\METRICS.md:70: - .\docs\METRICS.md:58: - .\project_metrics.py:667: ## TODOs and FIXMEs
- .\docs\METRICS.md:71: - .\docs\METRICS.md:59: - .\docs\METRICS.md:46: ## TODOs and FIXMEs
- .\docs\METRICS.md:72: - .\docs\METRICS.md:60: - .\docs\METRICS.md:48: - .\build_script.py:187: "TODO.md": "todo list",
- .\docs\METRICS.md:73: - .\docs\METRICS.md:61: - .\docs\METRICS.md:49: - .\build_script.py:218: code, output, _ = run_command(f"git diff {remote_branch} -- src/ Cargo.toml CHANGE.log TODO.md README.md", verbose=True)
- .\docs\METRICS.md:74: - .\docs\METRICS.md:62: - .\docs\METRICS.md:50: - .\build_script.py:271: Based on the following changes in the source files, Cargo.toml, CHANGE.log, TODO.md, and README.md,
- .\docs\METRICS.md:75: - .\docs\METRICS.md:63: - .\docs\METRICS.md:51: - .\build_script.py:278: - Revised TODO.md, removing completed tasks and adding new features.
- .\docs\METRICS.md:76: - .\docs\METRICS.md:64: - .\docs\METRICS.md:52: - .\build_script.py:414: """Update the README.md, TODO.md, and CHANGE.log with new changes."""
- .\docs\METRICS.md:77: - .\docs\METRICS.md:65: - .\docs\METRICS.md:53: - .\build_script.py:422: "TODO.md": "ToDo List",
- .\docs\METRICS.md:78: - .\docs\METRICS.md:66: - .\docs\METRICS.md:54: - .\build_script.py:441: subprocess.run(["git", "add", "README.md", "TODO.md", "CHANGE.log"], check=True)
- .\docs\METRICS.md:79: - .\docs\METRICS.md:67: - .\docs\METRICS.md:55: - .\project_metrics.py:236: """Find TODO and FIXME comments in files."""
- .\docs\METRICS.md:80: - .\docs\METRICS.md:68: - .\docs\METRICS.md:56: - .\project_metrics.py:241: if 'TODO' in line or 'FIXME' in line:
- .\docs\METRICS.md:81: - .\docs\METRICS.md:69: - .\docs\METRICS.md:57: - .\project_metrics.py:619: print("\nTODOs and FIXMEs:")
- .\docs\METRICS.md:82: - .\docs\METRICS.md:70: - .\docs\METRICS.md:58: - .\project_metrics.py:664: ## TODOs and FIXMEs
- .\docs\METRICS.md:83: - .\docs\METRICS.md:71: - .\docs\METRICS.md:59: - .\docs\METRICS.md:52: ## TODOs and FIXMEs
- .\docs\METRICS.md:84: - .\docs\METRICS.md:72: - .\docs\METRICS.md:60: - .\docs\METRICS.md:54: - .\build_script.py:187: "TODO.md": "todo list",
- .\docs\METRICS.md:85: - .\docs\METRICS.md:73: - .\docs\METRICS.md:61: - .\docs\METRICS.md:55: - .\build_script.py:218: code, output, _ = run_command(f"git diff {remote_branch} -- src/ Cargo.toml CHANGE.log TODO.md README.md", verbose=True)
- .\docs\METRICS.md:86: - .\docs\METRICS.md:74: - .\docs\METRICS.md:62: - .\docs\METRICS.md:56: - .\build_script.py:271: Based on the following changes in the source files, Cargo.toml, CHANGE.log, TODO.md, and README.md,
- .\docs\METRICS.md:87: - .\docs\METRICS.md:75: - .\docs\METRICS.md:63: - .\docs\METRICS.md:57: - .\build_script.py:278: - Revised TODO.md, removing completed tasks and adding new features.
- .\docs\METRICS.md:88: - .\docs\METRICS.md:76: - .\docs\METRICS.md:64: - .\docs\METRICS.md:58: - .\build_script.py:414: """Update the README.md, TODO.md, and CHANGE.log with new changes."""
- .\docs\METRICS.md:89: - .\docs\METRICS.md:77: - .\docs\METRICS.md:65: - .\docs\METRICS.md:59: - .\build_script.py:422: "TODO.md": "ToDo List",
- .\docs\METRICS.md:90: - .\docs\METRICS.md:78: - .\docs\METRICS.md:66: - .\docs\METRICS.md:60: - .\build_script.py:441: subprocess.run(["git", "add", "README.md", "TODO.md", "CHANGE.log"], check=True)
- .\docs\METRICS.md:91: - .\docs\METRICS.md:79: - .\docs\METRICS.md:67: - .\docs\METRICS.md:61: - .\project_metrics.py:236: """Find TODO and FIXME comments in files."""
- .\docs\METRICS.md:92: - .\docs\METRICS.md:80: - .\docs\METRICS.md:68: - .\docs\METRICS.md:62: - .\project_metrics.py:241: if 'TODO' in line or 'FIXME' in line:
- .\docs\METRICS.md:93: - .\docs\METRICS.md:81: - .\docs\METRICS.md:69: - .\docs\METRICS.md:63: - .\project_metrics.py:619: print("\nTODOs and FIXMEs:")
- .\docs\METRICS.md:94: - .\docs\METRICS.md:82: - .\docs\METRICS.md:70: - .\docs\METRICS.md:64: - .\project_metrics.py:664: ## TODOs and FIXMEs
- .\docs\METRICS.md:95: - .\docs\METRICS.md:83: - .\docs\METRICS.md:71: - .\docs\METRICS.md:65: - .\.git\hooks\sendemail-validate.sample:22: # Replace the TODO placeholders with appropriate checks according to your
- .\docs\METRICS.md:96: - .\docs\METRICS.md:84: - .\docs\METRICS.md:72: - .\docs\METRICS.md:66: - .\.git\hooks\sendemail-validate.sample:27: # TODO: Replace with appropriate checks (e.g. spell checking).
- .\docs\METRICS.md:97: - .\docs\METRICS.md:85: - .\docs\METRICS.md:73: - .\docs\METRICS.md:67: - .\.git\hooks\sendemail-validate.sample:35: # TODO: Replace with appropriate checks for this patch
- .\docs\METRICS.md:98: - .\docs\METRICS.md:86: - .\docs\METRICS.md:74: - .\docs\METRICS.md:68: - .\.git\hooks\sendemail-validate.sample:41: # TODO: Replace with appropriate checks for the whole series
- .\docs\METRICS.md:99: - .\docs\METRICS.md:87: - .\docs\METRICS.md:75: - .\docs\METRICS.md:69: - .\docs\METRICS.md:42: ## TODOs and FIXMEs
- .\docs\METRICS.md:100: - .\docs\METRICS.md:88: - .\docs\METRICS.md:76: - .\docs\METRICS.md:70: - .\docs\METRICS.md:44: - .\build_script.py:187: "TODO.md": "todo list",
- .\docs\METRICS.md:101: - .\docs\METRICS.md:89: - .\docs\METRICS.md:77: - .\docs\METRICS.md:71: - .\docs\METRICS.md:45: - .\build_script.py:218: code, output, _ = run_command(f"git diff {remote_branch} -- src/ Cargo.toml CHANGE.log TODO.md README.md", verbose=True)
- .\docs\METRICS.md:102: - .\docs\METRICS.md:90: - .\docs\METRICS.md:78: - .\docs\METRICS.md:72: - .\docs\METRICS.md:46: - .\build_script.py:271: Based on the following changes in the source files, Cargo.toml, CHANGE.log, TODO.md, and README.md,
- .\docs\METRICS.md:103: - .\docs\METRICS.md:91: - .\docs\METRICS.md:79: - .\docs\METRICS.md:73: - .\docs\METRICS.md:47: - .\build_script.py:278: - Revised TODO.md, removing completed tasks and adding new features.
- .\docs\METRICS.md:104: - .\docs\METRICS.md:92: - .\docs\METRICS.md:80: - .\docs\METRICS.md:74: - .\docs\METRICS.md:48: - .\build_script.py:414: """Update the README.md, TODO.md, and CHANGE.log with new changes."""
- .\docs\METRICS.md:105: - .\docs\METRICS.md:93: - .\docs\METRICS.md:81: - .\docs\METRICS.md:75: - .\docs\METRICS.md:49: - .\build_script.py:422: "TODO.md": "ToDo List",
- .\docs\METRICS.md:106: - .\docs\METRICS.md:94: - .\docs\METRICS.md:82: - .\docs\METRICS.md:76: - .\docs\METRICS.md:50: - .\build_script.py:441: subprocess.run(["git", "add", "README.md", "TODO.md", "CHANGE.log"], check=True)
- .\docs\METRICS.md:107: - .\docs\METRICS.md:95: - .\docs\METRICS.md:83: - .\docs\METRICS.md:77: - .\docs\METRICS.md:51: - .\project_metrics.py:190: "TODO.md", "TREE.md",
- .\docs\METRICS.md:108: - .\docs\METRICS.md:96: - .\docs\METRICS.md:84: - .\docs\METRICS.md:78: - .\docs\METRICS.md:52: - .\project_metrics.py:224: """Find TODO and FIXME comments in files."""
- .\docs\METRICS.md:109: - .\docs\METRICS.md:97: - .\docs\METRICS.md:85: - .\docs\METRICS.md:79: - .\docs\METRICS.md:53: - .\project_metrics.py:229: if 'TODO' in line or 'FIXME' in line:
- .\docs\METRICS.md:110: - .\docs\METRICS.md:98: - .\docs\METRICS.md:86: - .\docs\METRICS.md:80: - .\docs\METRICS.md:54: - .\project_metrics.py:596: print("\nTODOs and FIXMEs:")
- .\docs\METRICS.md:111: - .\docs\METRICS.md:99: - .\docs\METRICS.md:87: - .\docs\METRICS.md:81: - .\docs\METRICS.md:55: - .\project_metrics.py:641: ## TODOs and FIXMEs
- .\docs\METRICS.md:112: - .\docs\METRICS.md:100: - .\docs\METRICS.md:88: - .\docs\METRICS.md:82: - .\docs\TODO.md:1: # TODO: Feature Suggestions for App Enhancement
- .\docs\METRICS.md:113: - .\docs\METRICS.md:101: - .\docs\METRICS.md:89: - .\docs\METRICS.md:83: - .\scripts\print_project.py:13: "README.md", "TAGS.json", "TODO.md", "TREE.md",
- .\docs\METRICS.md:114: - .\docs\METRICS.md:102: - .\docs\METRICS.md:90: - .\docs\TODO.md:1: # TODO: Feature Suggestions for App Enhancement
- .\docs\METRICS.md:115: - .\docs\METRICS.md:103: - .\docs\METRICS.md:91: - .\scripts\print_project.py:13: "README.md", "TAGS.json", "TODO.md", "TREE.md",
- .\docs\METRICS.md:116: - .\docs\METRICS.md:104: - .\docs\TODO.md:1: # TODO: Feature Suggestions for App Enhancement
- .\docs\METRICS.md:117: - .\docs\METRICS.md:105: - .\scripts\print_project.py:13: "README.md", "TAGS.json", "TODO.md", "TREE.md",
- .\docs\METRICS.md:118: - .\docs\TODO.md:1: # TODO: Feature Suggestions for App Enhancement
- .\docs\METRICS.md:119: - .\scripts\print_project.py:13: "README.md", "TAGS.json", "TODO.md", "TREE.md",
- .\docs\TODO.md:1: # TODO: Feature Suggestions for App Enhancement
- .\scripts\print_project.py:13: "README.md", "TAGS.json", "TODO.md", "TREE.md",

## Visualizations

### Project Growth
![Project Growth](../project_metrics_images/project_growth.png)

### Code Metrics
![Code Metrics](../project_metrics_images/code_metrics.png)

### Dependency Graph
![Dependency Graph](../project_metrics_images/dependency_graph.png)
