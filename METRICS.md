# Project Metrics

## Overview
- **Total Files:** 31
- **Total Lines:** 3579
- **Total Words:** 12162
- **Total Characters:** 130200
- **Total Size:** 130.74 KB
- **Code to Comment Ratio:** 19.71
- **Average Complexity:** 12.87
- **Detected License:** License file not found

## File Type Statistics

| Extension | Files | Lines | Words | Characters | Size |
|-----------|-------|-------|-------|------------|------|
| .py | 4 | 1643 | 5471 | 61109 | 61.28 KB |
| .rs | 21 | 1587 | 4463 | 54403 | 54.67 KB |
| .md | 4 | 276 | 1955 | 12779 | 12.85 KB |
| .log | 1 | 45 | 175 | 1273 | 1.29 KB |
| .toml | 1 | 28 | 98 | 636 | 664.00 B |

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
- .\print_project.py:15: "README.md", "TAGS.json", "TODO.md", "TREE.md",
- .\project_metrics.py:190: "TODO.md", "TREE.md",
- .\project_metrics.py:224: """Find TODO and FIXME comments in files."""
- .\project_metrics.py:229: if 'TODO' in line or 'FIXME' in line:
- .\project_metrics.py:596: print("\nTODOs and FIXMEs:")
- .\project_metrics.py:641: ## TODOs and FIXMEs
- .\TODO.md:1: # TODO: Feature Suggestions for App Enhancement

## Visualizations

### Project Growth
![Project Growth](project_metrics_images/project_growth.png)

### Code Metrics
![Code Metrics](project_metrics_images/code_metrics.png)

### Dependency Graph
![Dependency Graph](project_metrics_images/dependency_graph.png)
