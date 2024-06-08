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
import json
import math
import os


# 设置日志
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


driver = None
driver_lock = threading.Lock()

plane_json = None
with open("planes.json", "r") as f:
    plane_json = json.load(f)

plane_id_json = None
with open("planes_info.json", "r") as f:
    plane_id_json = json.load(f)


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
    # options.add_argument("--start-minimized")  # 最小化打开浏览器
    options.add_experimental_option("detach", True)
    options.add_argument("--log-level=3")  # 设置日志级别为3，隐藏错误信息

    driver = webdriver.Edge(options=options)
    driver.minimize_window()
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
    logger.info("loading...")

    # WebDriverWait(driver, 120).until(
    #     EC.element_to_be_clickable((By.XPATH, '//*[@id="welcomeContent"]/div[1]/span'))
    # ).click()  # 关闭欢迎

    # logger.info("driver 已初始化完成")


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

    if "No routes departed" in response:
        return False, response
    else:
        return True, response


def get_depart_planes_info(response):
    # TODO 为什么每种机型只显示一架
    # 正则表达式匹配所有acId和routeReg
    acId_pattern = re.compile(r"acId:\s*(\d+)")
    routeReg_pattern = re.compile(r"routeReg:\s*'([^']*)'")

    # 搜索所有匹配项
    acId_matches = acId_pattern.findall(response)
    routeReg_matches = routeReg_pattern.findall(response)

    departed_num = len(acId_matches)
    # 遍历 "pax" 数组，找到匹配目标 ID 的对象
    message = f"""
    {departed_num} Planes Departed:

    """
    global plane_json
    for pax_plane in plane_json["pax"]:
        for acId, routeReg in zip(acId_matches, routeReg_matches):
            if str(pax_plane["id"]) == acId:
                plane_name = pax_plane["model"]
                message += "\t" + routeReg + "  " + plane_name + "\n"

    # logger.info(message)
    return message


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
    soup = BeautifulSoup(html, "html.parser")
    fuel_price = soup.find("div", class_="col-6 p-2").find("b").text
    fuel_holding = soup.find("span", class_="font-weight-bold").text

    script = """
    return fetch('https://www.airlinemanager.com/co2.php?undefined&fbSig=false', {
    method: 'GET',
    credentials: 'same-origin'
    })
    .then(response => response.text())
    .then(data => {
        return data;
    });
    """

    html = driver.execute_script(script)
    soup = BeautifulSoup(html, "html.parser")
    co2_price = soup.find("div", class_="col-6 p-2").find("b").text
    co2_holding = soup.find("span", class_="font-weight-bold text-success").text

    return fuel_price, fuel_holding, co2_price, co2_holding


def get_routes_info():
    global driver
    # https://www.airlinemanager.com/routes.php?start=10&sort=&fbSig=false

    submessage = """"""
    fleet_count = 0
    start = 0
    while True:
        script = f"""
        return fetch('https://www.airlinemanager.com/routes.php?start={start}&sort=&fbSig=false', {{
            method: 'GET',
            credentials: 'same-origin'
        }})
        .then(response => response.text())
        .then(data => {{
            return data;
        }});
        """
        with driver_lock:
            response = driver.execute_script(script)

        soup = BeautifulSoup(response, "html.parser")

        fleets = soup.findAll("div", class_="row bg-white p-2 m-text border classPAX")

        if len(fleets) == 0:
            break

        for fleet in fleets:
            frame1 = fleet.find("div", class_="col-10 text-center")
            W_no = frame1.find("b").text[1:]
            airport_from, airport_to = frame1.find("span").text.split(" - ")

            frame2 = fleet.find("div", class_="col-6")
            B_no, plane_name = frame2.find("a").text.split(" - ")

            Onboard = (
                frame2.find("span")
                .text.split(": ")[-1]
                .replace("\t", "")
                .split("\n")[0]
            )

            submessage += (
                "\t"
                + W_no
                + "\t  "
                + airport_from
                + " - "
                + airport_to
                + "\t  "
                + B_no
                + " - "
                + plane_name
                + "\t  "
                + Onboard
                + "\n"
            )
            fleet_count += 1

        start += 20
    message = (
        f"""
    Routes Info ({fleet_count}):

"""
        + submessage
    )
    logger.info(message)
    return message


def get_plane_id():
    start = 0
    planes_info = []
    while True:
        script = f"""
        return fetch('https://www.airlinemanager.com/routes.php?start={start}&sort=&fbSig=false', {{
            method: 'GET',
            credentials: 'same-origin'
        }})
        .then(response => response.text())
        .then(data => {{
            return data;
        }});
        """
        with driver_lock:
            global driver
            response = driver.execute_script(script)

        soup = BeautifulSoup(response, "html.parser")

        fleets = soup.findAll("div", class_="row bg-white p-2 m-text border classPAX")

        if len(fleets) == 0:
            break

        for fleet in fleets:
            frame2 = fleet.find("div", class_="col-6")
            B_no, plane_name = frame2.find("a").text.split(" - ")

            id_attr = fleet["id"]  # 含有飞机id信息
            # print(id_attr)
            id_pattern = re.compile(r"routeMainList(\d+)")
            id_match = id_pattern.search(id_attr)
            if id_match:
                id = int(id_match.group(1))
            else:
                id = None

            plane_info = [id, B_no, plane_name]
            planes_info.append(plane_info)

        start += 20

    # 将 planes_info 列表转换为字典列表
    new_planes_info_dict = {
        plane[1]: {"id": plane[0], "model": plane[2]} for plane in planes_info
    }

    # 定义 JSON 文件的路径
    json_file_path = "planes_info.json"

    # 将合并后的数据写入 JSON 文件
    global plane_id_json
    with open(json_file_path, "w", encoding="utf-8") as json_file:
        json.dump(new_planes_info_dict, json_file, ensure_ascii=False, indent=4)
    with open(json_file_path, "r") as f:
        plane_id_json = json.load(f)

    logger.info("Json updated")


def ground_over_carry():
    start = 0
    fleet_count = 0
    submessage = """"""
    while True:
        script = f"""
        return fetch('https://www.airlinemanager.com/routes.php?start={start}&sort=&fbSig=false', {{
            method: 'GET',
            credentials: 'same-origin'
        }})
        .then(response => response.text())
        .then(data => {{
            return data;
        }});
        """
        with driver_lock:
            global driver
            response = driver.execute_script(script)

        soup = BeautifulSoup(response, "html.parser")

        fleets = soup.findAll("div", class_="row bg-white p-2 m-text border classPAX")

        if len(fleets) == 0:
            break

        for fleet in fleets:
            frame2 = fleet.find("div", class_="col-6")
            B_no, plane_name = frame2.find("a").text.split(" - ")

            # Onboard = (
            #     frame2.find("span")
            #     .text.split(": ")[-1]
            #     .replace("\t", "")
            #     .split("\n")[0]
            # )
            Y_num, J_num, F_num = map(
                int, re.findall(pattern="\d+", string=frame2.find("span").text)
            )
            Y_weight, J_weight, F_weight = 1, 2.5, 4

            onboard_index = Y_num * Y_weight + J_num * J_weight + F_num * F_weight

            if onboard_index < 12:
                try:
                    id = plane_id_json[B_no]["id"]
                except Exception as e:
                    logger.error(e)
                ground_status = ground(id)
                if ground_status == 1:
                    submessage += f"\t{B_no} - {plane_name}\t\t {Y_num} / {J_num} / {F_num}\n"
                    fleet_count += 1
                elif ground_status == 2:
                    logger.info(f"\t{B_no} - {plane_name}\t\t {Y_num} / {J_num} / {F_num}\t\thaving been grounded")
                elif ground_status == 0:
                    logger.info(
                        f"{B_no} - {plane_name}\t\t {Y_num} / {J_num} / {F_num} but failed to ground"
                    )

        start += 20
    message = f"""
    Ground {fleet_count} Planes:

"""
    message += submessage
    logger.info(message)


def cal_proper_price():
    try:
        Y_price, J_price, F_price = map(
            float, input("Enter the auto prices of Y, J, F:\n").split()
        )
    except Exception as e:
        logger.error(e)
        return False

    Y_price = math.floor(Y_price * 1.1)
    J_price = math.floor(J_price * 1.08)
    F_price = math.floor(F_price * 1.06)

    message = f"""

        Y : {Y_price}
        J : {J_price}
        F : {F_price}
    """

    logger.info(message)


def plan_bulk_check(wear_threshold):
    pass


def ground(id):
    """
    Return:
        - 1: ground
        - 2: misground
        - 0: error
    """
    # https://www.airlinemanager.com/fleet_ground.php?id=118659681&fbSig=false
    global driver
    script = f"""
    return fetch('https://www.airlinemanager.com/fleet_ground.php?id={id}&fbSig=false', {{
        method: 'GET',
        credentials: 'same-origin'
    }})
    .then(response => response.text())
    .then(data => {{
        return data;
    }});
    """
    with driver_lock:
        try:
            response = driver.execute_script(script)
            # logger.info(response)
            if "add_content('maxDepart',1);" in response:
                # logger.info("switch the ground status wrongly, now switch again...")
                driver.execute_script(script)
                return 2
            return 1
        except Exception as e:
            logger.error(e)
    return 0
