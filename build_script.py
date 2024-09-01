import subprocess
import os
import sys
import time
import argparse
import logging
import shutil
import toml
import configparser  # Import ConfigParser to read config.ini
import requests  # For API calls
from packaging import version

# Configuration
CARGO_BUILD_OPTIONS = "--release -j50"
DEFAULT_BUILD_INTERVAL = 3600  # 1 hour
CONFIG_FILE = "config.ini"
OLLAMA_MODEL = "llama3"
OLLAMA_API_URL = "http://192.168.1.223:11434"  # Assuming Ollama is running locally on this port

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(command, verbose=False):
    if verbose:
        print(f"Running command: {command}")
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
    output, error = process.communicate()
    return process.returncode, output, error

def authenticate_github():
    # Read GitHub token from config.ini
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    
    if 'github' not in config or 'token' not in config['github']:
        logger.error("GitHub token not found in config.ini. Please add your GitHub token.")
        sys.exit(1)

    github_token = config['github']['token']

    # Authenticate gh CLI with the token
    logger.info("Authenticating with GitHub using gh CLI...")
    code, output, error = run_command(f'echo {github_token} | gh auth login --with-token', verbose=True)
    
    if code != 0:
        logger.error(f"Failed to authenticate with GitHub: {error}")
        sys.exit(1)
    
    logger.info("Successfully authenticated with GitHub.")

def check_dependencies(auto_confirm=False):
    logger.info("Checking for required dependencies...")
    for cmd in ['git --version', 'cargo --version', 'gh --version']:
        code, output, error = run_command(cmd, verbose=True)
        if code != 0:
            logger.error(f"Dependency check failed for command: {cmd}. Error: {error}")
            sys.exit(1)
    print("All dependencies are installed.")

def git_pull(auto_confirm=False):
    logger.info("Pulling latest changes...")
    if not auto_confirm and not prompt_user("Do you want to pull the latest changes from the repository?"):
        return (0, "", "")
    return run_command("git pull", verbose=True)

def cargo_build(auto_confirm=False):
    logger.info(f"Building project with options: {CARGO_BUILD_OPTIONS}")
    if not auto_confirm and not prompt_user("Do you want to build the project?"):
        return (0, "", "")
    return run_command(f"cargo build {CARGO_BUILD_OPTIONS}", verbose=True)

def cargo_test(auto_confirm=False):
    logger.info("Running tests...")
    if not auto_confirm and not prompt_user("Do you want to run the tests?"):
        return (0, "", "")
    return run_command("cargo test", verbose=True)

def git_commit_and_push(auto_confirm=False, use_ollama=False):
    logger.info("Committing and pushing changes...")
    if not auto_confirm and not prompt_user("Do you want to commit and push changes?"):
        return (0, "", "")
    
    commit_message = "Automated build commit"
    
    if use_ollama:
        logger.info("Generating commit message using Ollama...")
        commit_message = generate_commit_message_with_ollama()
        if not commit_message:
            logger.error("Failed to generate commit message using Ollama. Using default commit message.")
            commit_message = "Automated build commit"

    run_command("git add .", verbose=True)
    run_command(f'git commit -m "{commit_message}"', verbose=True)
    return run_command("git push", verbose=True)

def generate_commit_message_with_ollama():
    try:
        # Construct the request payload based on the working curl command
        payload = {
            "model": "llama3",
            "prompt": "Generate a concise and descriptive commit message summarizing recent updates and changes to a software project.",
            "stream": False
        }
        
        # Send the POST request to the Ollama API
        headers = {'Content-Type': 'application/json'}
        response = requests.post(f"{OLLAMA_API_URL}/api/generate", json=payload, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Parse the JSON response
        commit_message = response.json().get("text", "").strip()
        logger.info(f"Generated commit message: {commit_message}")
        return commit_message
    except requests.RequestException as e:
        logger.error(f"Error generating commit message with Ollama: {e}")
        return None

def get_project_info():
    try:
        with open("Cargo.toml", "r") as f:
            cargo_toml = toml.load(f)
        return cargo_toml['package']['name'], cargo_toml['package']['version']
    except Exception as e:
        logger.error(f"Failed to read project info from Cargo.toml: {e}")
        return None, None

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

def get_latest_github_version():
    logger.info("Fetching the latest GitHub release version using the gh CLI...")
    
    # First, check if there are any releases at all
    code, output, error = run_command("gh release list", verbose=True)
    if code != 0:
        logger.error(f"Failed to fetch release list from GitHub: {error}")
        return None

    if "No releases found" in output:
        logger.warning("No releases found on GitHub. Using version from Cargo.toml.")
        return None
    
    # Try to get the latest release version
    code, output, error = run_command("gh release view --json tagName -q .tagName", verbose=True)
    if code != 0:
        logger.error(f"Failed to fetch the latest release version from GitHub: {error}")
        return None
    
    latest_version = output.strip().lstrip('v')
    logger.info(f"Latest GitHub release version: {latest_version}")
    return latest_version

def determine_version_bump(changed_files):
    cargo_toml_changed = any('Cargo.toml' in file for file in changed_files)
    src_files_changed = any(file.startswith('src/') for file in changed_files)
    
    if cargo_toml_changed:
        # Check if dependencies were added or removed
        code, output, error = run_command(f"git diff {get_latest_tag()}..HEAD Cargo.toml", verbose=True)
        if '[dependencies]' in output:
            return 'minor'
    
    if src_files_changed:
        # Check for changes in public API
        code, output, error = run_command(f"git diff {get_latest_tag()}..HEAD src/", verbose=True)
        if 'pub fn' in output or 'pub struct' in output or 'pub enum' in output:
            return 'minor'
    
    return 'patch'

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
        # If it's not a valid version, just append -1 to the string
        return f"{version_str}-1"

def update_cargo_toml(new_version, auto_confirm=False):
    try:
        with open("Cargo.toml", "r") as f:
            lines = f.readlines()
        
        # Flag to track if we're in the [package] section
        in_package_section = False

        with open("Cargo.toml", "w") as f:
            for line in lines:
                # Check for the start of the [package] section
                if line.strip().startswith("[package]"):
                    in_package_section = True
                
                # Check for the end of the [package] section
                if in_package_section and line.strip().startswith("[") and not line.strip().startswith("[package]"):
                    in_package_section = False
                
                # Update version only if in [package] section
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

def create_release(auto_confirm=False):
    _, current_version = get_project_info()
    if not current_version:
        logger.error("Failed to get current version from Cargo.toml")
        return False

    latest_github_version = get_latest_github_version()
    if latest_github_version:
        if version.parse(current_version) <= version.parse(latest_github_version):
            changed_files = get_changed_files(latest_github_version)
            bump_type = determine_version_bump(changed_files)
            new_version = increment_version(latest_github_version, bump_type)
        else:
            new_version = current_version  # Cargo.toml version is already ahead
    else:
        new_version = current_version  # Use the version from Cargo.toml if no GitHub release found

    if new_version != current_version:
        if not update_cargo_toml(new_version, auto_confirm):
            return False
        
        # Commit the Cargo.toml changes
        if not auto_confirm and not prompt_user("Do you want to commit the version update in Cargo.toml?"):
            return False
        run_command("git add Cargo.toml", verbose=True)
        run_command(f'git commit -m "Update version to {new_version}"', verbose=True)

    logger.info(f"Creating release v{new_version}...")
    if not auto_confirm and not prompt_user(f"Do you want to create a release with tag v{new_version}?"):
        return False

    code, output, error = run_command(f'git tag -a v{new_version} -m "Release v{new_version}"', verbose=True)
    if code != 0:
        logger.error(f"Failed to create git tag: {error}")
        return False

    code, output, error = run_command("git push --tags", verbose=True)
    if code != 0:
        logger.error(f"Failed to push git tag: {error}")
        return False

    code, output, error = run_command("git push", verbose=True)  # Push the commit with updated Cargo.toml
    if code != 0:
        logger.error(f"Failed to push Cargo.toml update: {error}")
        return False

    logger.info(f"Release v{new_version} created and pushed successfully")
    return True

def prompt_user(message):
    response = input(f"{message} (y/n): ").lower()
    return response == 'y'

def build_cycle(auto_confirm=False, use_ollama=False):
    logger.info(f"Starting build cycle at {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Pull latest changes
    code, output, error = git_pull(auto_confirm)
    if code != 0:
        logger.error(f"Failed to pull latest changes: {error}")
        return False

    # Build the project
    code, output, error = cargo_build(auto_confirm)
    if code != 0:
        logger.error(f"Build failed: {error}")
        return False

    # Copy the executable
    if not copy_executable(auto_confirm):
        return False

    # Run tests
    code, output, error = cargo_test(auto_confirm)
    if code != 0:
        logger.error(f"Tests failed: {error}")
        return False

    # If we got here, everything succeeded. Commit and push.
    code, output, error = git_commit_and_push(auto_confirm, use_ollama)
    if code != 0:
        logger.error(f"Failed to commit and push: {error}")
        return False

    logger.info("Build cycle completed successfully!")

    # Prompt for release creation
    if not auto_confirm and prompt_user("Do you want to create and push a release?"):
        if create_release(auto_confirm):
            logger.info("Release created and pushed successfully!")
        else:
            logger.error("Failed to create and push release.")

    return True

def main(daemon_mode, build_interval, auto_confirm, use_ollama):
    authenticate_github()  # Authenticate with GitHub using the token
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

    # Read config.ini for use_ollama setting
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
