from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def test_selenium_setup():
    # Setup Chrome options
    chrome_options = webdriver.ChromeOptions()
    # chrome_options.add_argument('--headless')  # Run in headless mode if needed
    
    # Setup WebDriver using webdriver_manager
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        # Navigate to a website
        driver.get("https://www.python.org")
        
        # Find an element
        search_bar = driver.find_element(By.NAME, "q")
        
        # Print title
        print(f"Page title: {driver.title}")
        
        assert "Python" in driver.title
        
    finally:
        # Close the browser
        driver.quit()

if __name__ == "__main__":
    test_selenium_setup()
