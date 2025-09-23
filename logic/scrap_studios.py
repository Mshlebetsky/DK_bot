import logging

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import undetected_chromedriver as uc
import re


logger = logging.getLogger(__name__)


def extract_numbers(text: str) -> list[int]:
    """
    Извлекает все целые числа из строки.
    Возвращает список int.
    """
    # \d+ — одна или несколько цифр
    numbers = re.findall(r'\d+', str(text))
    # конвертируем в int
    return [int(num) for num in numbers] if numbers else []


def update_all_studios():
    url = "https://дк-яуза.рф/studii/"

    # options = Options()
    # options.add_argument("--headless=new")
    # options.add_argument("--no-sandbox")
    # options.add_argument("--disable-dev-shm-usage")
    # options.add_argument("--disable-gpu")
    # options.add_argument("--window-size=1920,1080")
    # options.add_argument(
    #     "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    #     "AppleWebKit/537.36 (KHTML, like Gecko) "
    #     "Chrome/120.0.0.0 Safari/537.36"
    # )
    start_time = time.time()
    # driver = webdriver.Chrome(options=options)
    # driver = uc.Chrome(headless=True)
    # driver = uc.Chrome(options=options, version_main=139)
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--headless=new")

    driver = uc.Chrome(options=options, version_main=139)
    driver.get(url)
    time.sleep(2)

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(2)

    error_text = ''

    elements_parent = driver.find_element(By.CLASS_NAME,'tabs-content').find_element(By.CLASS_NAME,'tab-item.tab-all').find_element(By.CLASS_NAME,'flex')
    items = elements_parent.find_elements(By.CLASS_NAME,f'services__item')
    data = {}
    counter = 0
    error_counter = 0
    driver.execute_script("arguments[0].scrollIntoView(true);", items[0])
    time.sleep(3)
    for item in items:
        counter+=1
        driver.execute_script("arguments[0].scrollIntoView(true);", item)
        body = driver.find_element(By.TAG_NAME,'body')
        body.send_keys(Keys.ESCAPE)
        time.sleep(1)

        try:  #----------GET img link / is_free and  clicking for details
            img = item.find_element(By.CLASS_NAME,'services__item-image').find_element(By.TAG_NAME,'img').get_attribute('src')
            is_free = item.find_elements(By.TAG_NAME,'div')[-1].text
            is_free = is_free.lower() == 'платно'

            item.find_element(By.CLASS_NAME,'services__item-info').click()

        except Exception as e:
            error_counter +=1
            logger.warning(f"ошибка на {counter} студии: картинка/имя/платно: \n{e}")
            continue
        time.sleep(2)

        try: # -------- GET name
            title = driver.find_element(By.CLASS_NAME,'title').text
        except:
            error_counter +=1
            error_text += e
            logger.warning(f"ошибка на {counter} студии: Имя \n{e}")
            continue
        try: # ------- GET description
            description = driver.find_element(By.CLASS_NAME,'modal_more_text').text
        except:
            error_counter +=1
            error_text += e
            logger.warning(f"ошибка на {counter} студии: Описание \n{e}")
            continue
        try: #--------------Get teacher / age / cost
            more_info = driver.find_elements(By.CLASS_NAME,'modal_more_info_text')
            teacher = more_info[0].text
            try: #Get cost
                if is_free:
                    cost = driver.find_elements(By.CLASS_NAME,'modal_more_info_text')[-2].text
                else:
                    cost = 0
            except:
                cost = 1
            try:
                age = driver.find_elements(By.CLASS_NAME,'modal_more_info_text')[-1].text
            except:
                error_counter+=1
                error_text += e
                logger.warning(f"ошибка на {counter} студии: Преподаватель \n{e}")
                continue
        except:
            error_text += e
            logger.warning(f"ошибка на {counter} студии: Хз что это \n{e}")
            continue
        try: #--------------Get QR_img
            qr_img = driver.find_element(By.CLASS_NAME,'about__slider').find_elements(By.TAG_NAME,'a')[0].get_attribute('href')
        except:
            error_counter += 1
            logger.warning(f"ошибка на {counter} студии: QR \n{e}")

        category = 'unknown'

        time.sleep(0.5)
        temp_list = extract_numbers(str(cost))
        if len(temp_list) > 1:
            second_cost = temp_list[1]
        else:
            second_cost = None
        cost = temp_list[0]
        try:
            studio_info = [description,cost,second_cost, age,img,qr_img,teacher, category]
            data[title] = studio_info
        except:
            error_counter +=1
    categories = driver.find_element(By.CLASS_NAME,'tabs-wrapper').find_elements(By.CLASS_NAME,'tabs')[0].find_elements(By.TAG_NAME,'span')


    body.send_keys(Keys.ESCAPE)
    time.sleep(2)
    try:
        for category in categories[1:]:
            try:
                time.sleep(2)
                category.click()
                items = driver.find_element(By.CLASS_NAME,'tab-item.done').find_element(By.CLASS_NAME,'flex').find_elements(By.CLASS_NAME,'services__item')
                for i in items:
                    studios = i.find_elements(By.TAG_NAME,'div')[1].text
                    if data[studios][-1] == "unknown":
                        data[studios][-1] = category.text.lower()
                    else:
                        data[studios][-1] += category.text.lower()
            except:
                logger.warning(f"ошибка на категории {category} : \n{e}")

                error_counter +=1
    except:
        pass
    end_time = time.time()
    elapsed_time = end_time - start_time
    text = f"Обновление завершено за {round(elapsed_time)} сек"
    if error_counter > 0:
        text += f'\nБыло обновлено {len(data)} студий\nБыло {error_counter} ошибок при выполнении\n'
    driver.close()
    driver.quit()

    return data, text
