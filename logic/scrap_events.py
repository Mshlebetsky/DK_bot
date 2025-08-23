from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import selenium
from selenium.webdriver import Chrome
from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

AFISHA_URL = "https://xn----8sbknn9c9d.xn--p1ai/afisha/"


def fetch_events():
    options = Options()
    #     options.add_argument("--headless=new")
    #     options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)
    driver.get(AFISHA_URL)
    time.sleep(4)

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(4)

    try:
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        time.sleep(0.3)
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.HOME)
    except:
        print('error with pressing button')
        time.sleep(1)

    net = driver.find_element(By.CLASS_NAME, 'tabs-content').find_elements(By.CLASS_NAME, 'flex')[0].find_elements(
        By.CSS_SELECTOR, 'div')[0::4]
    events_list = []

    for element in net:

        status = True

        time.sleep(1)
        if element.text.split('\n')[2] == 'БЕСПЛАТНО':
            event_free = 'БЕСПЛАТНО'
        else:
            event_free = 'ПЛАТНО'

        try:
            element.find_element(By.CSS_SELECTOR, 'a.b-event__slide-link.js-load-info').click()
        except:
            print(f'error on attempt click selector')
            status = False
            continue
        time.sleep(1)

        try:
            if event_free == 'БЕСПЛАТНО':
                event_link = False
            else:
                event_link = driver.find_element(By.CLASS_NAME, 'modal_more_info').find_element(By.CLASS_NAME,
                                                                                                'button-link.abiframelnk').get_attribute(
                    'href')
        except:
            status = False
            print('error with link')
            continue

        try:
            event_name = driver.find_element(By.CLASS_NAME, 'fancybox-stage').find_element(By.CLASS_NAME, 'title').text
        except:
            status = False
            print(f'error on  attempt | name')
            continue

        try:
            event_date = driver.find_element(By.CLASS_NAME, 'fancybox-stage').find_element(By.CLASS_NAME,
                                                                                           'modal_more_calendar').find_element(
                By.TAG_NAME, 'span').text
        except:
            status = False
            print(f'error on attempt date')
            continue

        try:
            event_time = driver.find_element(By.CLASS_NAME, 'fancybox-stage').find_element(By.CLASS_NAME,
                                                                                           'modal_more_time').find_element(
                By.TAG_NAME, 'span').text
        except:
            status = False
            print(f'error on  attempt time')
            continue

        try:
            event_full_description = driver.find_element(By.CLASS_NAME, 'fancybox-stage').find_element(By.CLASS_NAME,
                                                                                                       'modal_more_text').text
        except:
            status = False
            print(f'error on  attempt description')
            continue

        try:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        except:
            status = False
            print(f'error on  attempt closing')
            continue

        time.sleep(1)
        event = []
        event = [event_name, event_date, event_time, event_free, event_link, event_full_description]
        if status:
            events_list.append(event)
    #         print(f'{event_date}\n{event_name}\n{event_time}')
    driver.quit()

    return events_list


# fetch_events()