from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from datetime import datetime
import re
import undetected_chromedriver as uc


def find_age_limits(text: str) -> int:
    try:
        matches = re.findall(r"\(\+?(\d{1,2})\+?\)", text)
        return [int(m) for m in matches][0]
    except:
        return 0


def update_all_events():
    url = "https://xn----8sbknn9c9d.xn--p1ai/afisha/"


    start_time = time.time()
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--headless=new")

    driver = uc.Chrome(options=options, version_main=139)
    # driver = uc.Chrome(headless=True)
    driver.get(url)
    time.sleep(4)
    error_text = ''
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(4)

    data = {}
    error_counter = 0
    items = driver.find_element(By.CLASS_NAME, 'tabs-content').find_element(By.CLASS_NAME, 'flex').find_elements(
        By.CLASS_NAME, 'b-event__slide-item')
    driver.execute_script("arguments[0].scrollIntoView(true);", items[0])
    time.sleep(2)
    for item in items:
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        driver.execute_script("arguments[0].scrollIntoView(true);", item)
        time.sleep(1)
        try:
            is_free = (item.find_element(By.CLASS_NAME, 'text-is-payable').text.lower() == 'бесплатно')
        except:
            is_free = False
        try:
            item.find_elements(By.TAG_NAME, 'a')[0].click()
        except Exception as e:
            # print('error')
            error_text += f'{e}\n'
            continue
        time.sleep(2)
        try:
            main_info = driver.find_element(By.ID, 'hidden-content-2')

            name = main_info.find_element(By.CLASS_NAME, 'title').text
            event_date = main_info.find_element(By.CLASS_NAME, 'modal_more_calendar').find_element(By.TAG_NAME,
                                                                                                   'span').text
            description = main_info.find_element(By.CLASS_NAME, 'modal_more_text').text
            age_limit = find_age_limits(description)
            event_time = main_info.find_element(By.CLASS_NAME, 'modal_more_time').find_element(By.TAG_NAME, 'span').text
            img = main_info.find_element(By.CLASS_NAME, 'modal_more_image').find_element(By.TAG_NAME,
                                                                                'img').get_attribute('src')
            try:
                link = main_info.find_element(By.CLASS_NAME, 'button-link.abiframelnk').get_attribute('href')
            except:
                link = ''

            month = {
                "ЯНВ": 1, "ФЕВ": 2, "МАР": 3, "АПР": 4,
                "МАЙ": 5, "ИЮН": 6, "ИЮЛ": 7, "АВГ": 8,
                "СЕН": 9, "ОКТ": 10, "НОЯ": 11, "ДЕК": 12,
            }
            mon, day, year = event_date.replace(',', '').split(' ')
            hour, minutes = event_time.split(':')
            date = datetime(int(year), int(month[mon.upper()]), int(day), int(hour), int(minutes))
            date_str = f'{str(year)}-{str(month[mon.upper()])}-{str(day)} {str(hour)}:{str(minutes)}'
            # information = [date, description, img, link]
            information = [date_str, description,age_limit, img, link, is_free]
            data[name] = information

        except Exception as e:
            error_counter += 1
            error_text += f'{e}\n'
    end_time = time.time()
    elapsed_time = end_time - start_time
    text = f"Обновление завершено за {round(elapsed_time)} сек\n"
    if error_counter > 0:
        text += f"При обновлении было пропущено {error_counter} мероприятий со следующими ошибками:\n{error_text}"
    driver.close()
    driver.quit()
    return data, text