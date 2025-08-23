from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import selenium
from selenium.webdriver import Chrome
from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

def update_all_studios():
    url = "https://дк-яуза.рф/studii/"

    options = Options()
    # options.add_argument("--headless=new")
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



    elements_parent = driver.find_element(By.CLASS_NAME,'tabs-content').find_element(By.CLASS_NAME,'tab-item.tab-all').find_element(By.CLASS_NAME,'flex')
    items = elements_parent.find_elements(By.CLASS_NAME,f'services__item')
    data = {}
    counter = 0
    error_counter = 0

    for item in items:
        counter+=1

        body = driver.find_element(By.TAG_NAME,'body')
        body.send_keys(Keys.ESCAPE)
        time.sleep(1)

        try:  #----------GET img link / is_free and  clicking for details
            img = item.find_element(By.CLASS_NAME,'services__item-image').find_element(By.TAG_NAME,'img').get_attribute('src')

            is_free = item.find_elements(By.TAG_NAME,'div')[-1].text
            is_free = is_free.lower() == 'платно'

            item.find_element(By.CLASS_NAME,'services__item-info').click()

        except:
            error_counter +=1
            print(f'crushed on {counter} iteration on base page')
            continue
        time.sleep(2)

        try: # -------- GET name
            title = driver.find_element(By.CLASS_NAME,'title').text
        except:
            error_counter +=1
            print(f'crushed on {counter} iteration on title')
            continue
        try: # ------- GET description
            description = driver.find_element(By.CLASS_NAME,'modal_more_text').text
        except:
            error_counter +=1
            print(f'crushed on {counter} iteration on description')
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
                print('error with age')
                continue
        except:
            error_counter +=1
            print(f'crushed on {counter} iteration on getting teacher')
            continue
        try: #--------------Get QR_img
            qr_img = driver.find_element(By.CLASS_NAME,'about__slider').find_elements(By.TAG_NAME,'a')[0].get_attribute('href')
        except:
            error_counter += 1
            print('crushed on qr_img')
        category = 'unknown'

        time.sleep(0.5)

        try:
            studio_info = [description,cost,age,img,qr_img,teacher, category]
            data[title] = studio_info
        except:
            error_counter +=1
            print(f'crushed on {counter} iteration on recording')

    categories = driver.find_element(By.CLASS_NAME,'tabs-wrapper').find_elements(By.CLASS_NAME,'tabs')[0].find_elements(By.TAG_NAME,'span')


    body.send_keys(Keys.ESCAPE)
    time.sleep(2)
    try:
        for category in categories[1:-1]:
            try:
                time.sleep(2)
                category.click()
                print(category.text)
                items = driver.find_element(By.CLASS_NAME,'tab-item.done').find_element(By.CLASS_NAME,'flex').find_elements(By.CLASS_NAME,'services__item')
                for i in items:
                    studios = i.find_elements(By.TAG_NAME,'div')[1].text
                    if data[studios][-1] == "unknown":
                        data[studios][-1] = category.text.lower()
                    else:
                        data[studios][-1] += category.text.lower()
            except:
                print(f"Ошибка с добавлением категории {category.text}")
    except:
        pass
    text = f'Было обновлено {len(data)} студий\nБыло {error_counter} ошибок при выполнении'
    driver.close()
    return data, text
