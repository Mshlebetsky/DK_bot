from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

def update_all_news():
    url = "https://дк-яуза.рф/novosti/"

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
    start_time = time.time()

    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(4)

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(4)

    text = ''
    data = {}
    counter = 0
    error_counter = 0
    try:
        body = driver.find_element(By.TAG_NAME,'body')
        news_table = driver.find_element(By.CLASS_NAME,'progress.news').find_element(By.CLASS_NAME,'flex')
        news_list = news_table.find_elements(By.CLASS_NAME,'b-event__slide-item.news_block')
    except:
        text = 'Ошибка с нахождением блоков новостей'
        return data, text
    for item in news_list[-1::-1]:
        driver.execute_script("arguments[0].scrollIntoView(true);", item)
        counter += 1
        body.send_keys(Keys.ESCAPE)
        time.sleep(0.5)

        item.find_element(By.CLASS_NAME,'b-event__slide-link.js-load-info').click()
        time.sleep(2)
        try:
            info_table = driver.find_element(By.ID,'hidden-content-2')
        except:
            # text += f'Ошибка с поиском блока информации {counter} новости'
            error_counter +=1
            continue
        try:
            title = info_table.find_element(By.CLASS_NAME,'title').text
        except:
            # text += f'Ошибка с поиском заголовка {counter} новости'
            error_counter +=1
            continue
        try:
            img = info_table.find_element(By.CLASS_NAME,'column-left').find_element(By.TAG_NAME,'img').get_attribute('src')
        except:
            # text += f'Ошибка с поиском заголовка {counter} новости'
            error_counter += 1
            continue

        try:
            description = info_table.find_element(By.CLASS_NAME,'modal_more_text').text
        except:
            # text += f'Ошибка с поиском описания {counter} новости'
            error_counter += 1
            continue
        data[title] = [description, img]
    end_time = time.time()
    elapsed_time = end_time - start_time
    text = f"Обновление завершено за {elapsed_time} секунд"
    if error_counter > 0:
        text += f"При обновлении было пропущено {error_counter} новостей"
    driver.close()
    return data, text
#        data[title] = [img, description]