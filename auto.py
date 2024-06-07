from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging
import threading
from bs4 import BeautifulSoup
import re

# 设置日志
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s : %(message)s")


driver = None
driver_lock = threading.Lock()


def login():
    url = "https://airline4.net/"

    # 从该目录下 user_info.txt 读取账号密码
    with open(file="user_info.txt", mode="r") as f:
        email, password = f.readlines()
        email = email.split("\n")[0]

    global driver

    options = Options()
    options.page_load_strategy = "eager"  # 可选: "normal", "eager", "none"
    options.add_argument("--start-maximized")  # 启动时最大化窗口
    # options.add_argument("--disable-gpu")  # 禁用GPU加速
    options.add_argument("--disable-infobars")  # 禁用信息栏
    options.add_argument("--disable-extensions")  # 禁用扩展
    options.add_experimental_option("detach", True)
    options.add_argument("--log-level=3")  # 设置日志级别为3，隐藏错误信息

    driver = webdriver.Edge(options=options)

    driver.get(url)  # 登录页面

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

    WebDriverWait(driver, 120).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="welcomeContent"]/div[1]/span'))
    ).click()  # 关闭欢迎

    logger.info("driver 已初始化完成")


def get_driver():
    with driver_lock:
        global driver
        if driver is None:
            logger.info("正在初始化 driver...")
            login()
    return driver


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
        EC.element_to_be_clickable((By.XPATH, '//*[@id="listDepartAll"]/div/button[2]'))
    ).click()

def depart_all():
    global driver

    script = """
    return fetch('https://www.airlinemanager.com/route_depart.php?mode=all&ref=list&hasCostIndex=1&costIndex=200&ids=x&fbSig=false', {
    method: 'GET',
    credentials: 'same-origin'
    })
    .then(response => response.text())
    .then(data => {
        return data;
    });
    """

    response = driver.execute_script(script)
    # logger.info(response)

    if 'No routes departed' in response:
        return False
    else:
        return True
    


def get_fuel_price():
    global driver

    script = """
    return fetch('https://www.airlinemanager.com/fuel.php?undefined&fbSig=false', {
    method: 'GET',
    credentials: 'same-origin'
    })
    .then(response => response.text())
    .then(data => {
        return data;
    });
    """

    html = driver.execute_script(script)
    soup = BeautifulSoup(html,'html.parser')
    fuel = soup.find('div', class_='col-6 p-2').find('b').text

    return fuel
