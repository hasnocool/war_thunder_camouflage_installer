import subprocess
import os
import sys
import time
import argparse
import logging
import shutil
import toml
import configparser
import requests
from bs4 import BeautifulSoup
from packaging import version
import hashlib

# Configuration
CARGO_BUILD_OPTIONS = "--release -j50"
DEFAULT_BUILD_INTERVAL = 3600  # 1 hour
CONFIG_FILE = "config.ini"
OLLAMA_MODEL = "llama3"
OLLAMA_API_URL = "http://192.168.1.223:11434"
DB_FILE = "war_thunder_camouflages.db"  # Update with your database file name

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(command, verbose=True):
    if verbose:
        print(f"Running command: {command}")
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True, encoding='utf-8', errors='ignore')
    output, error = process.communicate()
    return process.returncode, output, error

def authenticate_github():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    
    if 'github' not in config or 'token' not in config['github']:
        logger.error("GitHub token not found in config.ini. Please add your GitHub token.")
        sys.exit(1)

    github_token = config['github']['token']

    logger.info("Authenticating with GitHub using gh CLI...")
    code, output, error = run_command(f'echo {github_token} | gh auth login --with-token', verbose=True)
    
    if code != 0:
        logger.error(f"Failed to authenticate with GitHub: {error}")
        sys.exit(1)
    
    logger.info("Successfully authenticated with GitHub.")

def check_dependencies(auto_confirm=True):
    logger.info("Checking for required dependencies...")
    for cmd in ['git --version', 'cargo --version', 'gh --version']:
        code, output, error = run_command(cmd, verbose=True)
        if code != 0:
            logger.error(f"Dependency check failed for command: {cmd}. Error: {error}")
            sys.exit(1)
    print("All dependencies are installed.")

def git_pull(auto_confirm=True):
    logger.info("Pulling latest changes...")

    # Try pulling changes
    code, output, error = run_command("git pull", verbose=True)
    
    if code != 0 and "Your local changes to the following files would be overwritten by merge" in error:
        logger.warning("Local changes detected that would be overwritten by merge.")
        if not auto_confirm and not prompt_user("Local changes detected. Do you want to automatically commit these changes? (y/n)"):
            return code, output, error

        # Automatically commit or stash changes
        logger.info("Automatically committing or stashing local changes...")
        
        # Check for uncommitted changes
        code, output, error = run_command("git status --porcelain", verbose=False)
        if output.strip():
            # Commit changes if there are any
            run_command("git add .", verbose=True)
            run_command('git commit -m "Auto-commit before pulling latest changes"', verbose=True)
        else:
            # If nothing to commit, stash changes
            run_command("git stash", verbose=True)

        # Retry pulling latest changes
        code, output, error = run_command("git pull", verbose=True)
        if code == 0:
            logger.info("Successfully pulled latest changes after handling local changes.")
        else:
            logger.error(f"Failed to pull latest changes even after handling local changes: {error}")

    elif code != 0:
        logger.error(f"Failed to pull latest changes: {error}")

    return code, output, error

def cargo_build(auto_confirm=True):
    logger.info(f"Building project with options: {CARGO_BUILD_OPTIONS}")
    if not auto_confirm and not prompt_user("Do you want to build the project?"):
        return (0, "", "")
    return run_command(f"cargo build {CARGO_BUILD_OPTIONS}", verbose=True)

def cargo_test(auto_confirm=True):
    logger.info("Running tests...")
    if not auto_confirm and not prompt_user("Do you want to run the tests?"):
        return (0, "", "")
    return run_command("cargo test", verbose=True)

def generate_detailed_changes_summary():
    try:
        run_command("git fetch", verbose=True)

        code, branches_output, _ = run_command("git branch -r", verbose=True)
        if code != 0:
            logger.error("Failed to retrieve remote branches.")
            return ""

        remote_branch = None
        for line in branches_output.splitlines():
            if 'origin/main' in line:
                remote_branch = 'origin/main'
                break
            elif 'origin/master' in line:
                remote_branch = 'origin/master'
                break

        if not remote_branch:
            logger.error("No valid remote branch found (e.g., origin/main or origin/master).")
            return ""

        code, output, _ = run_command(f"git diff {remote_branch} -- src/ Cargo.toml", verbose=True)
        if code != 0:
            logger.error("Failed to get the diff of modified files against the remote.")
            return ""

        if not output.strip():
            logger.info("No changes detected between the local and remote repository.")
            return "No changes detected."

        changes_summary = output.strip()
        logger.info(f"Generated detailed changes summary for Ollama:\n{changes_summary}")
        return changes_summary
    except Exception as e:
        logger.error(f"Error generating detailed changes summary: {e}")
        return ""

def generate_release_args_with_ollama():
    try:
        prompt = (
            "Generate a title and description for a GitHub release based on the following context:\n"
            "- The release is for a database file update related to the War Thunder Camouflage Installer.\n"
            "- Include relevant details about what the update contains or improves.\n"
            "Provide the title and description in a clear format.\n"
        )

        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }
        
        headers = {'Content-Type': 'application/json'}
        response = requests.post(f"{OLLAMA_API_URL}/api/generate", json=payload, headers=headers)
        response.raise_for_status()
        
        print(f"Raw response from Ollama: {response.text}")
        
        # Assuming response is structured with 'title' and 'description'
        title, description = response.json().get("response", "").split('\n', 1)
        logger.info(f"Generated release title: {title.strip()}")
        logger.info(f"Generated release description: {description.strip()}")
        return title.strip(), description.strip()
    except requests.RequestException as e:
        logger.error(f"Error generating release arguments with Ollama: {e}")
        return "Database Update Release", "Contains the latest version of the database file."

def git_commit_and_push(auto_confirm=False, use_ollama=False):
    logger.info("Committing and pushing changes...")
    if not auto_confirm and not prompt_user("Do you want to commit and push changes?"):
        return (0, "", "")

    changes_summary = generate_detailed_changes_summary()

    if changes_summary == "No changes detected.":
        commit_message = "Automated commit: No changes detected, repository updated."
    else:
        commit_message = "Automated build commit"

        if use_ollama:
            logger.info("Generating commit message using Ollama...")
            commit_message = generate_commit_message_with_ollama(changes_summary)
            if not commit_message:
                logger.error("Failed to generate commit message using Ollama. Using default commit message.")
                commit_message = "Automated build commit"

    run_command("git add .", verbose=True)
    run_command(f'git commit -m "{commit_message}"', verbose=True)

    # Attempt to push changes
    code, output, error = run_command("git push", verbose=True)

    # Check for LFS quota exceeded error
    if code != 0 and "This repository is over its data quota" in error:
        logger.warning("Git LFS quota exceeded. Skipping LFS files in the push.")
        
        # Instead of trying to delete the LFS files, we log and continue
        logger.info(f"Skipping LFS files: {DB_FILE}")
        logger.info("Proceeding with GitHub release upload instead.")
        upload_db_to_github_release(auto_confirm)

    elif code != 0:
        logger.error(f"Failed to push changes: {error}")

    return code, output, error

def get_file_checksum(file_path):
    """
    Calculate and return the SHA-256 checksum of a file.
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def get_latest_release_checksum():
    """
    Retrieve the checksum of the latest release's database file from GitHub releases.
    """
    try:
        response = requests.get(f"https://api.github.com/repos/hasnocool/war_thunder_camouflage_installer/releases/latest")
        response.raise_for_status()
        release_data = response.json()
        for asset in release_data.get("assets", []):
            if asset["name"] == DB_FILE:
                logger.info(f"Found existing database file in release: {asset['name']}")
                # Assuming checksum is stored in the release notes or another location
                # Placeholder logic for extracting checksum from release notes or a specific field
                # You may need to parse or modify this depending on how you store the checksum
                return asset.get("checksum", "")
        logger.info("No existing database file found in the latest release.")
        return ""
    except requests.RequestException as e:
        logger.error(f"Failed to retrieve latest release data: {e}")
        return ""

DB_FILE = "war_thunder_camouflages.db"  # Update with the correct path

def upload_db_to_github_release(auto_confirm=False):
    """
    Upload the database file to the GitHub release page.
    """
    logger.info("Uploading database file to GitHub release...")

    # Check if the database file exists before attempting to upload
    if not os.path.exists(DB_FILE):
        logger.error(f"Database file '{DB_FILE}' not found. Ensure the file path is correct.")
        return False  # Exit if the file is not found

    # Calculate the checksum of the local database file
    local_checksum = get_file_checksum(DB_FILE)
    logger.info(f"Local checksum: {local_checksum}")

    # Get the checksum of the latest release database file
    latest_checksum = get_latest_release_checksum()

    # Compare checksums to determine if an upload is necessary
    if local_checksum == latest_checksum:
        logger.info("Database file has not changed since the last release. Skipping upload.")
        return True

    # Generate release title and notes using Ollama
    title, notes = generate_release_args_with_ollama()

    # Check if the 'latest' release exists
    code, output, error = run_command("gh release view latest", verbose=False)
    
    if code != 0:
        logger.info("No 'latest' release found. Creating a new release.")
        code, output, error = run_command(f"gh release create latest --title '{title}' --notes '{notes}'", verbose=True)
        if code != 0:
            logger.error(f"Failed to create a new release: {error}")
            return False
    else:
        logger.info("'Latest' release found. Updating the existing release.")

    # Upload the DB file to the release
    code, output, error = run_command(f"gh release upload latest '{DB_FILE}' --clobber", verbose=True)
    
    if code == 0:
        logger.info(f"Successfully uploaded {DB_FILE} to the 'latest' release.")
        return True
    else:
        logger.error(f"Failed to upload {DB_FILE} to the 'latest' release: {error}")
        return False

def generate_commit_message_with_ollama(changes_summary):
    try:
        prompt = (
            "Based on the following changes in the source files and Cargo.toml, "
            "generate a concise and factual commit message summarizing these updates. "
            "Only provide the commit message, nothing else.\n\n"
            "Example commit message format:\n"
            "- Refactored API endpoints to improve performance and scalability.\n"
            "- Added error handling to enhance debugging capabilities.\n"
            "- Fixed UI alignment issue on the dashboard (Fixes #234).\n"
            "- Updated Cargo dependencies to the latest stable versions.\n\n"
            f"Changes summary:\n{changes_summary}"
        )

        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }
        
        headers = {'Content-Type': 'application/json'}
        response = requests.post(f"{OLLAMA_API_URL}/api/generate", json=payload, headers=headers)
        response.raise_for_status()
        
        print(f"Raw response from Ollama: {response.text}")
        
        commit_message = response.json().get("response", "").strip()
        logger.info(f"Generated commit message: {commit_message}")
        return commit_message
    except requests.RequestException as e:
        logger.error(f"Error generating commit message with Ollama: {e}")
        return None

def get_latest_github_version():
    logger.info("Fetching the latest GitHub release version using the gh CLI...")

    code, output, error = run_command("gh release view --json tagName -q .tagName", verbose=True)
    if code != 0 or "release not found" in error.lower():
        logger.warning("Failed to fetch the latest release version using gh CLI, attempting to scrape the GitHub tags page...")
        return scrape_github_tags_page()

    latest_version = output.strip().lstrip('v')
    logger.info(f"Latest GitHub release version: {latest_version}")
    print(f"Latest version from GitHub CLI: {latest_version}")
    return latest_version

def scrape_github_tags_page():
    try:
        tags_page_url = "https://github.com/hasnocool/war_thunder_camouflage_installer/tags"
        response = requests.get(tags_page_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        tag_div = soup.find('div', class_='Box-body p-0')
        if not tag_div:
            logger.error("No tags found on the GitHub tags page.")
            return None

        latest_tag = tag_div.find('h2', class_='f4 d-inline').find('a', class_='Link--primary Link')
        if latest_tag:
            latest_version = latest_tag.text.strip().lstrip('v')
            logger.info(f"Scraped latest GitHub tag version: {latest_version}")
            print(f"Scraped latest version from GitHub tags page: {latest_version}")
            return latest_version
        else:
            logger.error("Failed to find tag version on the GitHub tags page.")
            return None

    except requests.RequestException as e:
        logger.error(f"Error scraping GitHub tags page: {e}")
        return None

def copy_executable(auto_confirm=False):
    logger.info("Copying executable to current directory...")
    project_name, _ = get_project_info()
    if not project_name:
        return False
    
    source_path = os.path.join("target", "release", f"{project_name}.exe")
    
    if not os.path.exists(source_path):
        logger.error(f"Executable not found at {source_path}")
        return False
    
    if not auto_confirm and not prompt_user(f"Do you want to copy the executable {source_path} to the current directory?"):
        return False

    try:
        shutil.copy(source_path, ".")
        logger.info(f"Executable copied successfully: {project_name}.exe")
        return True
    except Exception as e:
        logger.error(f"Failed to copy executable: {e}")
        return False

def create_release(auto_confirm=False):
    _, current_version = get_project_info()
    if not current_version:
        logger.error("Failed to get current version from Cargo.toml")
        return False

    latest_github_version = get_latest_github_version()
    if latest_github_version:
        if version.parse(current_version) <= version.parse(latest_github_version):
            new_version = increment_version(latest_github_version, 'patch')
        else:
            new_version = current_version
    else:
        new_version = current_version

    if new_version != current_version:
        if not update_cargo_toml(new_version, auto_confirm):
            return False
        
        if not auto_confirm and not prompt_user("Do you want to commit the version update in Cargo.toml?"):
            return False
        run_command("git add Cargo.toml", verbose=True)
        run_command(f'git commit -m "Update version to {new_version}"', verbose=True)

    logger.info(f"Creating release v{new_version}...")
    if not auto_confirm and prompt_user(f"Do you want to create a release with tag v{new_version}?"):
        code, output, error = run_command(f'git tag -a v{new_version} -m "Release v{new_version}"', verbose=True)
        if code != 0:
            logger.error(f"Failed to create git tag: {error}")
            return False

        code, output, error = run_command("git push --tags", verbose=True)
        if code != 0:
            logger.error(f"Failed to push git tag: {error}")
            return False

        code, output, error = run_command(f"gh release create v{new_version}", verbose=True)
        if code != 0:
            logger.error(f"Failed to create GitHub release: {error}")
            return False

    logger.info(f"Release v{new_version} created and pushed successfully")
    return True

def increment_version(version_str, bump_type):
    v = version.parse(version_str)
    if isinstance(v, version.Version):
        major, minor, patch = v.major, v.minor, v.micro
        if bump_type == 'major':
            return f"{major + 1}.0.0-beta"
        elif bump_type == 'minor':
            return f"{major}.{minor + 1}.0-beta"
        else:  # patch
            return f"{major}.{minor}.{patch + 1}-beta"
    else:
        return f"{version_str}-1"

def update_cargo_toml(new_version, auto_confirm=False):
    try:
        with open("Cargo.toml", "r") as f:
            lines = f.readlines()
        
        in_package_section = False

        with open("Cargo.toml", "w") as f:
            for line in lines:
                if line.strip().startswith("[package]"):
                    in_package_section = True
                
                if in_package_section and line.strip().startswith("[") and not line.strip().startswith("[package]"):
                    in_package_section = False
                
                if in_package_section and line.strip().startswith("version ="):
                    if not auto_confirm and not prompt_user(f"Do you want to update version to {new_version} in Cargo.toml?"):
                        return False
                    f.write(f'version = "{new_version}"\n')
                else:
                    f.write(line)
        
        logger.info(f"Updated Cargo.toml with new version: {new_version}")
        return True
    except Exception as e:
        logger.error(f"Failed to update Cargo.toml: {e}")
        return False

def prompt_user(message):
    response = input(f"{message} (y/n): ").lower()
    return response == 'y'

def get_project_info():
    try:
        with open("Cargo.toml", "r") as f:
            cargo_toml = toml.load(f)
        return cargo_toml['package']['name'], cargo_toml['package']['version']
    except Exception as e:
        logger.error(f"Failed to read project info from Cargo.toml: {e}")
        return None, None

def build_cycle(auto_confirm=False, use_ollama=False):
    logger.info(f"Starting build cycle at {time.strftime('%Y-%m-%d %H:%M:%S')}")

    code, output, error = git_pull(auto_confirm)
    if code != 0:
        logger.error(f"Failed to pull latest changes: {error}")
        return False

    code, output, error = cargo_build(auto_confirm)
    if code != 0:
        logger.error(f"Build failed: {error}")
        return False

    if not copy_executable(auto_confirm):
        return False

    code, output, error = cargo_test(auto_confirm)
    if code != 0:
        logger.error(f"Tests failed: {error}")
        return False

    code, output, error = git_commit_and_push(auto_confirm, use_ollama)
    if code != 0:
        logger.error(f"Failed to commit and push: {error}")
        return False

    if not upload_db_to_github_release(auto_confirm):
        logger.error("Failed to upload database file to GitHub release.")
        return False

    logger.info("Build cycle completed successfully!")

    if not auto_confirm and prompt_user("Do you want to create and push a release?"):
        if create_release(auto_confirm):
            logger.info("Release created and pushed successfully!")
        else:
            logger.error("Failed to create and push release.")

    return True

def main(daemon_mode, build_interval, auto_confirm, use_ollama):
    authenticate_github()
    check_dependencies(auto_confirm)

    while True:
        success = build_cycle(auto_confirm, use_ollama)
        if not daemon_mode:
            sys.exit(0 if success else 1)
        logger.info(f"Waiting for next build cycle. Next build at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + build_interval))}")
        time.sleep(build_interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Continuous build pipeline for Rust project")
    parser.add_argument("--daemon", action="store_true", help="Run in daemon mode (continuous building)")
    parser.add_argument("--interval", type=int, default=DEFAULT_BUILD_INTERVAL, help="Build interval in seconds (for daemon mode)")
    parser.add_argument("--yes", "-y", action="store_true", help="Automatically say yes to all prompts")
    parser.add_argument("--use-ollama", action="store_true", help="Use Ollama API to generate commit messages")
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    use_ollama = config.getboolean('ollama', 'use_ollama', fallback=False) or args.use_ollama

    try:
        main(args.daemon, args.interval, args.yes, use_ollama)
    except KeyboardInterrupt:
        logger.info("\nBuild pipeline stopped by user.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        sys.exit(1)
