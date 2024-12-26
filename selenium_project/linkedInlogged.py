import logging
import json
from datetime import datetime
import os

# Set up detailed logging configuration
log_format = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.FileHandler('linkedin_automation.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import csv
#import getpass

def get_processed_urls_filename(username):
    """Generate a unique processed URLs filename for each account"""
    safe_username = "".join(x for x in username if x.isalnum())
    return f'processed_urls_{safe_username}.json'

def setup_browser():
    logger.info("Setting up Chrome browser...")
    try:
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        service = Service(ChromeDriverManager().install())
        browser = webdriver.Chrome(service=service, options=chrome_options)
        logger.info("Chrome browser setup successful")
        return browser
    except Exception as e:
        logger.error(f"Failed to setup browser: {str(e)}")
        raise

# XPaths used
XPATHS = {
    'send_note_button': "//button[contains(@aria-label, 'Add a note')]",
    'send_without_note_button': "//button[contains(@aria-label, 'Send without a note')]",
    'connect_to_invite': "(//main//button[contains(@aria-label, 'Invite')])[1]",
    'note_text_box': "//textarea[contains(@name, 'message')]",
    'send_invitation_confirmation_button': "//button[contains(@aria-label, 'Send invitation')]",
    'more_options': "//main//button[contains(@aria-label, 'More actions')]",
    'invite_options': "//main//div[contains(@aria-label, 'to connect')]",
    'message_option': "//span[text()='1st']",
    'already_connected_indicator': "//span[text()='1st']"
}

def load_processed_urls(username):
    logger.info(f"Loading previously processed URLs for account: {username}")
    filename = get_processed_urls_filename(username)
    try:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                data = json.load(f)
                logger.info(f"Loaded {len(data)} previously processed URLs for {username}")
                return data
    except Exception as e:
        logger.error(f"Error loading processed URLs for {username}: {str(e)}")
    logger.info(f"No previous processed URLs found for {username}, starting fresh")
    return {}

def save_processed_url(url, status, username):
    logger.debug(f"Saving URL status for {username} - URL: {url}, Status: {status}")
    try:
        filename = get_processed_urls_filename(username)
        processed_urls = load_processed_urls(username)
        processed_urls[url] = {
            'status': status,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        with open(filename, 'w') as f:
            json.dump(processed_urls, f)
        logger.info(f"Successfully saved status for URL: {url} for account: {username}")
    except Exception as e:
        logger.error(f"Error saving processed URL {url} for {username}: {str(e)}")

def is_already_connected(browser):
    logger.debug("Checking if already connected...")
    try:
        element = safe_find_element(browser, By.XPATH, XPATHS['already_connected_indicator'])
        is_connected = element is not None and element.is_displayed()
        logger.info(f"Connection status check result: {'Connected' if is_connected else 'Not connected'}")
        return is_connected
    except Exception as e:
        logger.error(f"Error checking connection status: {str(e)}")
        return False

def safe_find_element(browser, by, value):
    logger.debug(f"Searching for element: {by}={value}")
    try:
        element = browser.find_element(by, value)
        logger.debug(f"Element found: {by}={value}")
        return element
    except NoSuchElementException:
        logger.debug(f"Element not found: {by}={value}")
        return None

def login_to_linkedin(browser, username, password):
    logger.info("Starting LinkedIn login process...")
    try:
        browser.get("https://www.linkedin.com/login")
        logger.info("Navigated to LinkedIn login page")
        
        wait = WebDriverWait(browser, 10)
        wait.until(EC.presence_of_element_located((By.ID, "username")))
        
        username_input = safe_find_element(browser, By.ID, "username")
        password_input = safe_find_element(browser, By.ID, "password")
        sign_in_button = safe_find_element(browser, By.CSS_SELECTOR, "button[aria-label='Sign in']")

        if all([username_input, password_input, sign_in_button]):
            username_input.send_keys(username)
            logger.info("Username entered")
            password_input.send_keys(password)
            logger.info("Password entered")
            sign_in_button.click()
            logger.info("Sign in button clicked")
            
            logger.info("Waiting for OTP verification (10 seconds)")
            time.sleep(10)
            return True
        else:
            logger.error("One or more login form elements not found")
            return False
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        return False

def send_invitation(note, browser):
    logger.info("Attempting to send invitation...")
    if note:
        logger.info("Sending invitation with note")
        send_note = safe_find_element(browser, By.XPATH, XPATHS['send_note_button'])
        if send_note:
            try:
                send_note.click()
                logger.info("Clicked 'Add a note' button")
                time.sleep(2)
                
                note_box = safe_find_element(browser, By.XPATH, XPATHS['note_text_box'])
                if note_box:
                    note_box.send_keys(note)
                    logger.info("Note text entered successfully")
                    time.sleep(2)
                    
                    confirm_button = safe_find_element(browser, By.XPATH, XPATHS['send_invitation_confirmation_button'])
                    if confirm_button:
                        confirm_button.click()
                        logger.info("Invitation with note sent successfully")
                        time.sleep(2)
                        return True
            except Exception as e:
                logger.error(f"Error sending invitation with note: {str(e)}")
    else:
        logger.info("Sending invitation without note")
        send_without_note = safe_find_element(browser, By.XPATH, XPATHS['send_without_note_button'])
        if send_without_note:
            try:
                send_without_note.click()
                logger.info("Invitation without note sent successfully")
                time.sleep(2)
                return True
            except Exception as e:
                logger.error(f"Error sending invitation without note: {str(e)}")
    
    logger.error("Failed to send invitation")
    return False

def pre_scan_profiles(browser, file_path, username):
    logger.info("Starting pre-scan of profiles...")
    processed_urls = load_processed_urls(username)
    already_connected_count = 0
    total_profiles = 0
    scan_start_time = datetime.now()

    try:
        with open(file_path, 'r') as file:
            csv_reader = csv.reader(file)
            next(csv_reader, None)  # Skip header
            urls = [row[0] for row in csv_reader]
            total_profiles = len(urls)
            
            logger.info(f"Found {total_profiles} profiles to scan")
            
            for i, url in enumerate(urls, 1):
                logger.info(f"Scanning profile {i}/{total_profiles}: {url}")
                
                if url in processed_urls and processed_urls[url]['status'] == "Already Connected":
                    already_connected_count += 1
                    logger.info(f"Profile already connected: {url}")
                    continue
                
                browser.get(url)
                time.sleep(2)
                
                if is_already_connected(browser):
                    save_processed_url(url, "Already Connected", username)
                    already_connected_count += 1
                    logger.info(f"Found new already connected profile: {url}")
                
                if i % 5 == 0:
                    logger.info(f"Progress: {i}/{total_profiles} profiles scanned. Found {already_connected_count} existing connections")
                    
        scan_duration = datetime.now() - scan_start_time
        logger.info(f"Pre-scan completed in {scan_duration}")
        logger.info(f"Final Results - Total: {total_profiles}, Already Connected: {already_connected_count}")
        
        return already_connected_count, total_profiles
    
    except Exception as e:
        logger.error(f"Error during pre-scan: {str(e)}")
        return 0, 0

def connect_with_remaining(browser, file_path, note, username):
    logger.info("Starting to connect with remaining profiles...")
    processed_urls = load_processed_urls(username)
    connection_attempts = 0
    successful_connections = 0
    
    try:
        with open(file_path, 'r') as file:
            csv_reader = csv.reader(file)
            next(csv_reader, None)
            
            for row in csv_reader:
                url = row[0]
                
                if url in processed_urls and processed_urls[url]['status'] == "Already Connected":
                    logger.info(f"Skipping already connected profile: {url}")
                    continue
                
                logger.info(f"Processing URL: {url}")
                connection_attempts += 1
                
                browser.get(url)
                time.sleep(3)
                
                if is_already_connected(browser):
                    logger.info(f"Found already connected profile: {url}")
                    save_processed_url(url, "Already Connected", username)
                    continue

                connect_button = safe_find_element(browser, By.XPATH, XPATHS['connect_to_invite'])
                if connect_button and connect_button.is_displayed():
                    logger.info("Found direct connect button")
                    connect_button.click()
                    time.sleep(2)
                    if send_invitation(note, browser):
                        save_processed_url(url, "Connection Sent", username)
                        successful_connections += 1
                    continue
                
                logger.info("Direct connect button not found, trying more options...")
                more_options = safe_find_element(browser, By.XPATH, XPATHS['more_options'])
                if more_options and more_options.is_displayed():
                    more_options.click()
                    logger.info("Clicked more options")
                    time.sleep(2)
                    browser.execute_script("window.scrollBy(0, 200);")
                    time.sleep(2)
                    
                    invite_option = safe_find_element(browser, By.XPATH, XPATHS['invite_options'])
                    if invite_option and invite_option.is_displayed():
                        invite_option.click()
                        logger.info("Found and clicked invite option")
                        time.sleep(2)
                        if send_invitation(note, browser):
                            save_processed_url(url, "Connection Sent", username)
                            successful_connections += 1
                    else:
                        logger.warning(f"No invite option found for {url}")
                        save_processed_url(url, "No Invite Option", username)
                else:
                    logger.warning(f"No connection options found for {url}")
                    save_processed_url(url, "No Connect Option", username)
        
        logger.info(f"Connection process completed. Attempts: {connection_attempts}, Successful: {successful_connections}")
        
    except Exception as e:
        logger.error(f"Error in connect_with_remaining: {str(e)}")

def main():
    logger.info("=== LinkedIn Automation Script Started ===")
    start_time = datetime.now()
    
    try:
        csv_path = "C:/Users/Indhu/Downloads/inputs.csv"
        logger.info(f"Using CSV file: {csv_path}")
        
        username = input("Enter your username: ")
        password = input("Enter your password: ")
        
        browser = setup_browser()
        
        if not login_to_linkedin(browser, username, password):
            logger.error("Login failed, exiting script")
            browser.quit()
            return
        
        # Pre-scan phase
        logger.info("Starting pre-scan phase...")
        already_connected, total_profiles = pre_scan_profiles(browser, csv_path, username)
        
        logger.info("\nPre-scan Results Summary:")
        logger.info(f"Total profiles found: {total_profiles}")
        logger.info(f"Already connected profiles: {already_connected}")
        logger.info(f"Remaining profiles to connect: {total_profiles - already_connected}")
        
        if total_profiles - already_connected > 0:
            proceed = input("\nDo you want to proceed with connecting to remaining profiles? (y/n): ")
            if proceed.lower() == 'y':
                logger.info("User chose to proceed with remaining connections")
                send_with_note = input("Do you want to send a note with connections? (y/n): ")
                note = None
                if send_with_note.lower() == 'y':
                    logger.info("User opted to send connection note")
                    note = "Hey,\n\n It's always great connecting with classmates! Let's stay in touch and explore any opportunities to collaborate in the future. \n\nCheers,\nIndhu"
                
                connect_with_remaining(browser, csv_path, note, username)
            else:
                logger.info("User chose not to proceed with remaining connections")
        else:
            logger.info("No new connections to make - all profiles are already connected")
        
    except Exception as e:
        logger.error(f"Critical error in main execution: {str(e)}")
    finally:
        browser.quit()
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"=== Script completed in {duration} ===")

if __name__ == "__main__":
    main()