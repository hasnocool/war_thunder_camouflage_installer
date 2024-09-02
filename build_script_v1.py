import os
import subprocess
import sys

def run_command(command):
    """Run a command and return its output and error (if any)."""
    result = subprocess.run(command, capture_output=True, text=True, shell=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode

def increment_version(version):
    """Increment the last number in the version string."""
    parts = version.split('.')
    parts[-1] = str(int(parts[-1]) + 1)
    return '.'.join(parts)

def check_repo_status():
    """Check if there are uncommitted changes."""
    _, _, return_code = run_command('git diff-index --quiet HEAD --')
    return return_code == 0

def main():
    # Check if we're in a git repository
    if not os.path.isdir('.git'):
        print("Error: This script must be run from the root of a git repository.")
        return

    # Check for uncommitted changes
    if not check_repo_status():
        print("There are uncommitted changes in your repository.")
        print("Please commit or stash your changes before running this script.")
        return

    # Get the latest tag
    latest_tag, error, _ = run_command('git describe --tags --abbrev=0')

    if error and "No names found" in error:
        print("No existing tags found. Creating initial tag v0.1.0")
        new_tag = "v0.1.0"
    elif latest_tag:
        print(f"Latest tag: {latest_tag}")
        version = latest_tag[1:] if latest_tag.startswith('v') else latest_tag
        new_version = increment_version(version)
        new_tag = f"v{new_version}"
    else:
        print(f"Error fetching latest tag: {error}")
        return

    print(f"Creating new tag: {new_tag}")

    # Create the new tag
    _, error, _ = run_command(f'git tag {new_tag}')
    if error:
        print(f"Error creating tag: {error}")
        return

    # Try to push the new tag
    _, error, return_code = run_command(f'git push origin {new_tag}')
    if return_code != 0:
        print(f"Error pushing tag: {error}")
        print("\nIt seems there might be issues with your repository history.")
        print("Please try the following steps to resolve:")
        print("1. Remove the large file from Git history:")
        print("   git filter-branch --force --index-filter \"git rm --cached --ignore-unmatch path/to/large/file\" --prune-empty --tag-name-filter cat -- --all")
        print("2. Force push the changes:")
        print("   git push origin --force --all")
        print("3. Force push the tags:")
        print("   git push origin --force --tags")
        print("\nAfter completing these steps, run this script again.")
        run_command(f'git tag -d {new_tag}')
        return

    print(f"Tag {new_tag} created and pushed to remote.")

    # Create a release using gh cli
    print(f"Creating release for tag {new_tag}")
    output, error, return_code = run_command(f'gh release create {new_tag} --generate-notes')
    
    if return_code != 0:
        print(f"Error creating release: {error}")
        print("You may need to create the release manually or check your GitHub CLI configuration.")
    else:
        print("Release created successfully.")
        print(output)

if __name__ == "__main__":
    main()