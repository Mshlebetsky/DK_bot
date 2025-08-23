from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import selenium
from selenium.webdriver import Chrome
from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

def get_scrap_Word():
    url = "https://дк-яуза.рф/studii/"

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(4)

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(4)

    data = driver.find_elements(By.CLASS_NAME, 'tab-item.tab-all')[0].text
    driver.close()
    return data