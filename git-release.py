import requests
from bs4 import BeautifulSoup

def get_latest_github_version():
    logger.info("Fetching the latest GitHub release version using the gh CLI...")

    # First, try to get the latest release version using the gh CLI
    code, output, error = run_command("gh release view --json tagName -q .tagName", verbose=True)
    if code != 0 or "release not found" in error.lower():
        logger.warning("Failed to fetch the latest release version using gh CLI, attempting to scrape the GitHub tags page...")
        # Fallback to scraping the GitHub tags page
        return scrape_github_tags_page()

    latest_version = output.strip().lstrip('v')
    logger.info(f"Latest GitHub release version: {latest_version}")
    return latest_version

def scrape_github_tags_page():
    """
    Scrape the GitHub tags page to find the latest tag version.
    """
    try:
        # URL of the tags page (replace with your actual repository URL)
        tags_page_url = "https://github.com/hasnocool/war_thunder_camouflage_installer/tags"
        response = requests.get(tags_page_url)
        response.raise_for_status()

        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the latest tag from the tags page
        tag_div = soup.find('div', class_='Box-body p-0')
        if not tag_div:
            logger.error("No tags found on the GitHub tags page.")
            return None

        # Extract the first tag found, which should be the latest
        latest_tag = tag_div.find('h2', class_='f4 d-inline').find('a', class_='Link--primary Link')
        if latest_tag:
            latest_version = latest_tag.text.strip().lstrip('v')
            logger.info(f"Scraped latest GitHub tag version: {latest_version}")
            return latest_version
        else:
            logger.error("Failed to find tag version on the GitHub tags page.")
            return None

    except requests.RequestException as e:
        logger.error(f"Error scraping GitHub tags page: {e}")
        return None

# Rest of your script continues...

