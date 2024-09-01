import subprocess
import os
import sys
import time
import argparse
import logging
import shutil
import toml
import re
from packaging import version

# Configuration
CARGO_BUILD_OPTIONS = "--release -j50"
DEFAULT_BUILD_INTERVAL = 3600  # 1 hour

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(command):
    logger.info(f"Running command: {command}")
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
    output, error = process.communicate()
    return process.returncode, output, error

def check_dependencies():
    logger.info("Checking for required dependencies...")
    for cmd in ['git --version', 'cargo --version']:
        code, output, error = run_command(cmd)
        if code != 0:
            logger.error(f"Dependency check failed for command: {cmd}. Error: {error}")
            sys.exit(1)

def git_pull():
    logger.info("Pulling latest changes...")
    return run_command("git pull")

def cargo_build():
    logger.info(f"Building project with options: {CARGO_BUILD_OPTIONS}")
    return run_command(f"cargo build {CARGO_BUILD_OPTIONS}")

def cargo_test():
    logger.info("Running tests...")
    return run_command("cargo test")

def git_commit_and_push():
    logger.info("Committing and pushing changes...")
    run_command("git add .")
    run_command('git commit -m "Automated build commit"')
    return run_command("git push")

def get_project_info():
    try:
        with open("Cargo.toml", "r") as f:
            cargo_toml = toml.load(f)
        return cargo_toml['package']['name'], cargo_toml['package']['version']
    except Exception as e:
        logger.error(f"Failed to read project info from Cargo.toml: {e}")
        return None, None

def copy_executable():
    logger.info("Copying executable to current directory...")
    project_name, _ = get_project_info()
    if not project_name:
        return False
    
    source_path = os.path.join("target", "release", f"{project_name}.exe")
    
    if not os.path.exists(source_path):
        logger.error(f"Executable not found at {source_path}")
        return False
    
    try:
        shutil.copy(source_path, ".")
        logger.info(f"Executable copied successfully: {project_name}.exe")
        return True
    except Exception as e:
        logger.error(f"Failed to copy executable: {e}")
        return False

def get_latest_tag():
    code, output, error = run_command("git describe --tags --abbrev=0")
    if code != 0:
        logger.error(f"Failed to get latest tag: {error}")
        return None
    return output.strip()

def get_changed_files(last_tag):
    code, output, error = run_command(f"git diff --name-only {last_tag}..HEAD")
    if code != 0:
        logger.error(f"Failed to get changed files: {error}")
        return []
    return output.split('\n')

def determine_version_bump(changed_files):
    cargo_toml_changed = any('Cargo.toml' in file for file in changed_files)
    src_files_changed = any(file.startswith('src/') for file in changed_files)
    
    if cargo_toml_changed:
        # Check if dependencies were added or removed
        code, output, error = run_command(f"git diff {get_latest_tag()}..HEAD Cargo.toml")
        if '[dependencies]' in output:
            return 'minor'
    
    if src_files_changed:
        # Check for changes in public API
        code, output, error = run_command(f"git diff {get_latest_tag()}..HEAD src/")
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

def update_cargo_toml(new_version):
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
                    f.write(f'version = "{new_version}"\n')
                else:
                    f.write(line)
        
        logger.info(f"Updated Cargo.toml with new version: {new_version}")
        return True
    except Exception as e:
        logger.error(f"Failed to update Cargo.toml: {e}")
        return False

def fix_eframe_dependency():
    try:
        with open("Cargo.toml", "r") as f:
            content = toml.load(f)
        
        if 'dependencies' in content and 'eframe' in content['dependencies']:
            content['dependencies']['eframe'] = { "version": "0.22.0", "features": ["persistence"] }
        
        with open("Cargo.toml", "w") as f:
            toml.dump(content, f)
        
        logger.info("Updated eframe dependency in Cargo.toml")
        return True
    except Exception as e:
        logger.error(f"Failed to update eframe dependency in Cargo.toml: {e}")
        return False

def create_release():
    _, current_version = get_project_info()
    if not current_version:
        logger.error("Failed to get current version from Cargo.toml")
        return False

    latest_tag = get_latest_tag()
    if latest_tag:
        if version.parse(current_version) <= version.parse(latest_tag.lstrip('v')):
            changed_files = get_changed_files(latest_tag)
            bump_type = determine_version_bump(changed_files)
            new_version = increment_version(current_version, bump_type)
        else:
            new_version = current_version  # Cargo.toml version is already ahead
    else:
        new_version = current_version  # Use the version from Cargo.toml if no tags exist

    if new_version != current_version:
        if not update_cargo_toml(new_version):
            return False
        
        # Commit the Cargo.toml changes
        run_command("git add Cargo.toml")
        run_command(f'git commit -m "Update version to {new_version}"')

    logger.info(f"Creating release v{new_version}...")
    code, output, error = run_command(f'git tag -a v{new_version} -m "Release v{new_version}"')
    if code != 0:
        logger.error(f"Failed to create git tag: {error}")
        return False

    code, output, error = run_command("git push --tags")
    if code != 0:
        logger.error(f"Failed to push git tag: {error}")
        return False

    code, output, error = run_command("git push")  # Push the commit with updated Cargo.toml
    if code != 0:
        logger.error(f"Failed to push Cargo.toml update: {error}")
        return False

    logger.info(f"Release v{new_version} created and pushed successfully")
    return True

def prompt_for_release():
    while True:
        response = input("Do you want to create and push a release? (y/n): ").lower()
        if response in ['y', 'n']:
            return response == 'y'
        print("Please enter 'y' or 'n'.")

def build_cycle():
    logger.info(f"Starting build cycle at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Pull latest changes
    code, output, error = git_pull()
    if code != 0:
        logger.error(f"Failed to pull latest changes: {error}")
        return False
    
    # Build the project
    code, output, error = cargo_build()
    if code != 0:
        logger.error(f"Build failed: {error}")
        if "failed to select a version for the requirement `eframe" in error:
            logger.info("Attempting to fix eframe dependency...")
            if fix_eframe_dependency():
                logger.info("Retrying build after fixing eframe dependency...")
                code, output, error = cargo_build()
                if code != 0:
                    logger.error(f"Build failed again: {error}")
                    return False
            else:
                return False
        else:
            return False
    
    # Copy the executable
    if not copy_executable():
        return False
    
    # Run tests
    code, output, error = cargo_test()
    if code != 0:
        logger.error(f"Tests failed: {error}")
        return False
    
    # If we got here, everything succeeded. Commit and push.
    code, output, error = git_commit_and_push()
    if code != 0:
        logger.error(f"Failed to commit and push: {error}")
        return False
    
    logger.info("Build cycle completed successfully!")

    # Prompt for release creation
    if prompt_for_release():
        if create_release():
            logger.info("Release created and pushed successfully!")
        else:
            logger.error("Failed to create and push release.")
    
    return True

def main(daemon_mode, build_interval):
    check_dependencies()
    
    while True:
        success = build_cycle()
        if not daemon_mode:
            sys.exit(0 if success else 1)
        logger.info(f"Waiting for next build cycle. Next build at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + build_interval))}")
        time.sleep(build_interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Continuous build pipeline for Rust project")
    parser.add_argument("--daemon", action="store_true", help="Run in daemon mode (continuous building)")
    parser.add_argument("--interval", type=int, default=DEFAULT_BUILD_INTERVAL, help="Build interval in seconds (for daemon mode)")
    args = parser.parse_args()

    try:
        main(args.daemon, args.interval)
    except KeyboardInterrupt:
        logger.info("\nBuild pipeline stopped by user.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        sys.exit(1)
