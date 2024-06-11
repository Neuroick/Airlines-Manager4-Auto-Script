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
from logger_setup import get_logger


logger = get_logger(__name__)

# #设置日志
# logger = logging.getLogger(__name__)
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s - %(name)s - %(levelname)s : %(message)s",
#     datefmt="%Y-%m-%d %H:%M:%S"
# )


driver = None
driver_lock = threading.Lock()

plane_json = None
with open("planes.json", "r") as f:
    plane_json = json.load(f)

plane_id_json = None
with open("planes_info.json", "r") as f:
    plane_id_json = json.load(f)


def get_email_password():
    with open(file="user_info.txt", mode="r") as f:
        email, password = f.readlines()
    email = email.split("\n")[0]
    return email, password


def setup_driver():
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

    return driver


def login():
    url = "https://airline4.net/"

    email, password = get_email_password()

    driver = setup_driver()
    driver.minimize_window()

    try:
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
            
        logger.info("Login successfully")
        logger.info("Loading...")
        return True
    except Exception as e:
        logger.error(e)
        return False


def get_driver():
    global driver
    if driver is None:
        logger.info("Initializing driver...")
        login()
    return driver


def restart_driver():
    """get a new driver

    with lock
    """
    global driver
    with driver_lock:
        try:
            driver.quit()
            driver = None
            logger.info("The previous driver has quit, now launch a new one")
            return get_driver()
        except Exception as e:
            logger.error(e)


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
    try:
        response = driver.execute_script(script)
    except Exception as e:
        logger.error(e)

    # logger.info(response)

    if "No routes departed" in response:
        return False, response
    else:
        return True, response


def get_depart_planes_info(response):
    """
    Args:
        response : response of depart requests

    Returns:
        - depart info message
        - a list of B_nos of departed planes
    """

    # onboard_pattern = re.compile(r"toastDepart\((?:\d+,\s*){5}(\d+),\s*(\d+),\s*(\d+)")
    # onboard_matches = onboard_pattern.findall(response)

    # 正则表达式匹配所有routeId
    routeId_pattern = re.compile(r"routeId:\s*(\d+)")

    # 搜索所有匹配项
    routeId_matches = routeId_pattern.findall(response)

    departed_num = len(routeId_matches)
    # 遍历 "pax" 数组，找到匹配目标 ID 的对象
    message = f"\n\t{departed_num} Planes Departed:\n\n"
    B_nos = []
    global plane_id_json
    for key, value in zip(plane_id_json.keys(), plane_id_json.values()):
        for routeId in routeId_matches:
            if routeId == str(value["routeId"]):
                B_no = key
                model = value["model"]
                message += "\t\t" + B_no + "  " + model + "\n"
                B_nos.append(B_no)

    # logger.info(message)
    return message, B_nos


def get_fuel_price():
    global driver

    # fuel
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
    try:
        html = driver.execute_script(script)
    except Exception as e:
        logger.error(e)

    soup = BeautifulSoup(html, "html.parser")
    fuel_price = soup.find("div", class_="col-6 p-2").find("b").text
    fuel_holding = soup.find("span", class_="font-weight-bold").text

    # co2
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
    try:
        html = driver.execute_script(script)
    except Exception as e:
        logger.error(e)

    soup = BeautifulSoup(html, "html.parser")
    co2_price = soup.find("div", class_="col-6 p-2").find("b").text
    co2_holding = soup.find("span", class_="font-weight-bold text-success").text

    return fuel_price, fuel_holding, co2_price, co2_holding


def get_routes_info():
    global driver
    # https://www.airlinemanager.com/routes.php?start=10&sort=&fbSig=false

    submessage = ""
    ground_fleet_count = 0
    unground_fleet_count = 0
    start = 0

    while True:
        ground_fleets, unground_fleets, fleets = get_fleets_info(start)
        fleets_num = len(fleets)
        if fleets_num == 0:
            break

        for fleet in ground_fleets:
            frame1 = fleet.find("div", class_="col-10 text-center")
            W_no = frame1.find("b").text[1:]
            airport_from, airport_to = frame1.find("span", class_="s-text").text.split(
                " - "
            )

            frame2 = fleet.find("div", class_="col-6")
            B_no, plane_name = frame2.find("a").text.split(" - ")
            Demand = (
                frame2.find("span", class_="s-text")
                .text.split(": ")[-1]
                .replace("\t", "")
                .split("\n")[0]
            )

            submessage += (
                "\t\t"
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
                + Demand
                + "\t X"
                + "\n"
            )
            ground_fleet_count += 1

        for fleet in unground_fleets:
            frame1 = fleet.find("div", class_="col-10 text-center")
            W_no = frame1.find("b").text[1:]
            airport_from, airport_to = frame1.find("span", class_="s-text").text.split(
                " - "
            )

            frame2 = fleet.find("div", class_="col-6")
            B_no, plane_name = frame2.find("a").text.split(" - ")

            Onboard = (
                frame2.find("span")
                .text.split(": ")[-1]
                .replace("\t", "")
                .split("\n")[0]
            )
            logger.debug(submessage)
            submessage += (
                "\t\t"
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
            unground_fleet_count += 1

        start += 20

    logger.debug(submessage)
    message = f"\n\tRoutes Info ({unground_fleet_count}/{ground_fleet_count+unground_fleet_count}):\n\n{submessage}"

    logger.info(message)


def get_fleets_info(start):
    """
    Args:
        start: start page index

    Returns:
        ResultSet: three ResultSet of fleets: ground, unground, all

    with lock
    """

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
        try:
            response = driver.execute_script(script)
        except Exception as e:
            logger.error(e)

    soup = BeautifulSoup(response, "html.parser")
    fleets_ground = soup.findAll(
        "div",
        class_=re.compile(r"row bg-white p-2 m-text classPAX border\s*"),
    )
    fleets_unground = soup.findAll(
        "div",
        class_=re.compile(r"row bg-white p-2 m-text border classPAX"),
    )
    fleets_all = soup.findAll(
        "div",
        class_=re.compile(
            r"row bg-white p-2 m-text (border classPAX|classPAX border\s*)"
        ),
    )

    return fleets_ground, fleets_unground, fleets_all


def update_plane_info():
    """get information of my planes and record in json
    - key: B_no
    - values:
        - routeId: id used for departing and grounding
        - checkId: id used for checking
        - model
        - origin
        - destination
    """

    start = 0
    planes_info = []
    while True:
        _, _, fleets = get_fleets_info(start)

        if len(fleets) == 0:
            break

        for fleet in fleets:
            # routeId
            routeId_match = re.compile(r"routeMainList(\d+)").search(fleet["id"])
            if routeId_match:
                routeId = int(routeId_match.group(1))
            else:
                routeId = None

            # B_no, model
            frame2 = fleet.find("div", class_="col-6")
            B_no, model = frame2.find("a").text.split(" - ")

            # checkId
            checkId_match = re.compile(r"id=(\d+)").search(frame2.find("a")["onclick"])
            if checkId_match:
                checkId = int(checkId_match.group(1))
            else:
                checkId = None

            # origin, destination
            # print(fleet.find("span", class_="s-text").text)
            origin, destination = (
                fleet.find("div", class_="col-10 text-center")
                .find("span", class_="s-text")
                .text.split(" - ")
            )

            plane_info = [B_no, routeId, checkId, model, origin, destination]
            planes_info.append(plane_info)

        start += 20

    # 将 planes_info 列表转换为字典列表
    new_planes_info_dict = {
        plane[0]: {
            "routeId": plane[1],
            "checkId": plane[2],
            "model": plane[3],
            "origin": plane[4],
            "destination": plane[5],
        }
        for plane in planes_info
    }

    for key, value in new_planes_info_dict.items():
        plane_id_json[key] = value

    # 定义 JSON 文件的路径
    json_file_path = "planes_info.json"

    # 将合并后的数据写入 JSON 文件
    with open(json_file_path, "w", encoding="utf-8") as json_file:
        json.dump(plane_id_json, json_file, ensure_ascii=False, indent=4)

    logger.info(f"Json updated, with {len(plane_id_json)} records \n")


def ground_over_carry():
    global plane_id_json
    to_ground_count = 0
    is_grounded_count = 0
    submessage_to_ground = ""
    submessage_is_grounded = ""

    low_onboard_info = check_low_onboard()

    for B_no, Y_num, J_num, F_num in low_onboard_info:
        id = plane_id_json[B_no]["routeId"]
        model = plane_id_json[B_no]["model"]
        origin = plane_id_json[B_no]["origin"]
        destination = plane_id_json[B_no]["destination"]
        route = origin + " - " + destination

        ground_status = ground(id)
        if ground_status == 1:
            submessage_to_ground += (
                f"\t\t{route}\t{B_no} - {model}\t  {Y_num} / {J_num} / {F_num}\n"
            )
            to_ground_count += 1
        elif ground_status == 2:
            submessage_is_grounded += (
                f"\t\t{route}\t{B_no} - {model}\t  {Y_num} / {J_num} / {F_num}\n"
            )
            is_grounded_count += 1
        elif ground_status == 0:
            logger.info(
                f"\t\t{route}\t{B_no} - {model}\t  {Y_num} / {J_num} / {F_num} but failed to ground"
            )

    if to_ground_count > 0:
        message = f"\n\tGround {to_ground_count} Planes:\n\n"
        message += submessage_to_ground
    else:
        message = "\n\tNo planes carrying few passangers\n"
    if is_grounded_count > 0:
        message += (
            "\n\r\tThese planes carrying few passangers have been grounded:\n\n"
            + submessage_is_grounded
        )

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


def plan_bulk_check(wear_threshold=40):
    """plan bulk check for planes with wear rates above given threshold

    Args:
        wear_threshold (int, optional): wear rate threshold. Defaults to 40.

    with lock
    """

    # https://www.airlinemanager.com/maint_plan_do.php?type=bulkRepair&id=77097970&mode=do&pct=40&fbSig=false&_=1717860277369
    # https://www.airlinemanager.com/maint_plan_repair_bulk.php?pct=30&fbSig=false&_=1718026919369
    script = f"""
    return fetch('https://www.airlinemanager.com/maint_plan_repair_bulk.php?pct={wear_threshold}&fbSig=false', {{
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
        except Exception as e:
            logger.error(e)

    soup = BeautifulSoup(response, "html.parser")
    first_B_no = soup.find("td").text[1:]
    checkId = plane_id_json[first_B_no]["checkId"]

    script = f"""
    return fetch('https://www.airlinemanager.com/maint_plan_do.php?type=bulkRepair&id={checkId}&mode=do&pct={wear_threshold}&fbSig=false', {{
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
        except Exception as e:
            logger.error(e)

    # TODO 解析结果
    # logger.info("")


def ground(routeId):
    """ground A plane
    Return:
        - 1: ground
        - 2: misground
        - 0: error

    with lock
    """

    # https://www.airlinemanager.com/fleet_ground.php?id=118659681&fbSig=false
    global driver
    script = f"""
    return fetch('https://www.airlinemanager.com/fleet_ground.php?id={routeId}&fbSig=false', {{
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


# def check_depart_and_ground(low_onboard_info):
#     pass
#     global plane_id_json
#     routeIds = [plane_id_json[B_no]["routeId"] for B_no in B_nos]
#     models = [plane_id_json[B_no]["model"] for B_no in B_nos]
#     routes = [
#         plane_id_json[B_no]["origin"] + " - " + plane_id_json[B_no]["destination"]
#         for B_no in B_nos
#     ]

#     submessage = ""
#     for routeId, model, route, B_no in zip(routeIds, models, routes, B_nos):
#         ground(routeId)
#         submessage += f"\t\t{route}\t{B_no} - {model}\n"

#     messages = f"\n\tThese planes are grounded:\n\n" + submessage
#     logger.info(messages)
#     for B_no,Y_num,J_num,F_num in low_onboard_info:
#         id = plane_id_json[B_no]["routeId"]
#         model = plane_id_json[B_no]["model"]
#         origin = plane_id_json[B_no]["origin"]
#         destination = plane_id_json[B_no]["destination"]
#         route = origin + " - " + destination
#         ground(id)


def recall_some(B_nos):
    pass


def check_low_onboard(B_nos=None):
    """undone
    Arg :
        B_nos: if None, check all
    Return: [[B_no, Y_num, J_num, F_num],...]
    """

    Y_weight, J_weight, F_weight = 1, 2.5, 4
    if B_nos is None:
        start = 0
        low_onboard_info = []
        while True:
            _, fleets_unground, _ = get_fleets_info(start)

            if len(fleets_unground) == 0:
                break

            for fleet in fleets_unground:
                frame2 = fleet.find("div", class_="col-6")
                B_no, model = frame2.find("a").text.split(" - ")

                Y_num, J_num, F_num = map(
                    int, re.findall(pattern="\d+", string=frame2.find("span").text)
                )

                onboard_index = Y_num * Y_weight + J_num * J_weight + F_num * F_weight

                if onboard_index < 12:
                    low_onboard_info.append([B_no, Y_num, J_num, F_num])

            start += 20
        return low_onboard_info
    else:
        # TODO
        pass


def get_fleet_detail(checkId):
    """undone

    Args:
        checkId (_type_): _description_

    Returns:
        _type_: _description_
    """

    script = f"""
    return fetch('https://www.airlinemanager.com/fleet_details.php?id={checkId}&fbSig=false', {{
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
        except Exception as e:
            logger.error(e)

    soup = BeautifulSoup(response, "html.parser")

    # TODO
    # onboard
    last_onboard = (
        soup.find("div", class_="row bg-light m-text p-1 border")
        .find("div", class_="col-3")
        .findAll()
    )
    # seat layout
    # today demand
