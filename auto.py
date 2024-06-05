from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)


def login():
    url = "https://airline4.net/"

    global driver
    driver = webdriver.Edge()
    driver.get(url)  # 登录页面

    # 输入账号密码
    email = "liunick264@gmail.com"
    password = "AM173426344"

    for _ in range(2):  # 未知原因，需要操作两遍
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, "/html/body/div[4]/div/div[2]/div[1]/div/button[2]")
            )
        ).click()  # 点击 'Login'
        driver.find_element(By.XPATH, '//*[@id="lEmail"]').send_keys(email)
        driver.find_element(By.XPATH, '//*[@id="lPass"]').send_keys(password)
        driver.find_element(By.XPATH, '//*[@id="btnLogin"]').click()
        time.sleep(2)

    logger.info("登录成功")
    WebDriverWait(driver, 60).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="welcomeContent"]/div[1]/span'))
    ).click()  # 关闭欢迎


def close_popup():
    global driver
    try:
        popup_close = driver.find_element(
            By.XPATH, '//*[@id="popup"]/div/div/div[1]/div/span'
        )
        popup_close.click()
        # logger.info("弹出窗口已关闭")
    except:
        pass


def click_landed():
    global driver
    landed = driver.find_element(By.XPATH, '//*[@id="flightStatusLanded"]/span[1]')
    landed.click()
    # logger.info("已点击‘已到达’按钮")


def open_navigation_and_click_landed():
    global driver

    flight_info = driver.find_element(By.XPATH, '//*[@id="flightInfoToggleIcon"]')
    flight_info.click()
    logger.info("导航页已打开")
    click_landed()


def click_depart():
    global driver
    WebDriverWait(driver, 0.5).until(
            EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="listDepartAll"]/div/button[2]')
            )
        ).click()
    logger.info("飞机全部起飞")


def get_fuel_price():
    global driver

    close_popup()
    driver.find_element(By.XPATH, '//*[@id="mapMaint"]/img').click()
    driver.implicitly_wait(1)
    fuel = driver.find_element(
        By.XPATH, '//*[@id="fuelMain"]/div/div[1]/span[2]/b'
    ).text
    close_popup()

    message = f"当前油价：{fuel}"
    logger.info(message)
    
    return fuel
