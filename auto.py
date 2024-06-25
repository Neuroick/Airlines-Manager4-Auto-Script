from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time
import threading
from bs4 import BeautifulSoup
import re
import json
import math
from logger_setup import get_logger


logger = get_logger(__name__)


driver = None
driver_lock = threading.Lock()


plane_id_json = None
with open("planes_info.json", "r") as f:
    plane_id_json = json.load(f)


def get_email_password():
    with open(file="user_info.txt", mode="r") as f:
        email, password = f.readlines()
    email = email.split("\n")[0]
    return email, password


def setup_driver(show=False):
    global driver

    options = Options()
    options.page_load_strategy = "eager"  # optional: "normal", "eager", "none"
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    # options.add_argument("--start-minimized")
    options.add_experimental_option("detach", True)
    options.add_argument("--log-level=3")

    if show is False:
        options.add_argument("--headless")

    driver = webdriver.Edge(options=options)

    return driver


def login(show=False):
    url = "https://airline4.net/"

    email, password = get_email_password()
    driver = setup_driver(show=show)

    try:
        driver.get(url)  # login page

        for _ in range(2):  # for a unknown reason, operate twice
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "/html/body/div[4]/div/div[2]/div[1]/div/button[2]")
                )
            ).click()
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


def get_driver(show=False):
    global driver
    if driver is None:
        logger.info("Initializing driver...")
        login(show=show)
    return driver


def restart_driver(show=False):
    """get a new driver

    with lock
    """
    global driver
    with driver_lock:
        try:
            driver.quit()
            driver = None
            logger.info("The previous driver has quit, now launch a new one")
            return get_driver(show=show)
        except Exception as e:
            logger.error(e)


def get_new_driver():
    """open game with a separated browser"""

    options = Options()
    options.add_argument("--log-level=3")
    options.add_experimental_option("detach", True)
    new_driver = webdriver.Edge(options=options)

    url = "https://airline4.net/"
    email, password = get_email_password()

    try:
        new_driver.get(url)  # login page

        for _ in range(2):  # for a unknown reason, operate twice
            WebDriverWait(new_driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "/html/body/div[4]/div/div[2]/div[1]/div/button[2]")
                )
            ).click()
            new_driver.find_element(By.XPATH, '//*[@id="lEmail"]').send_keys(email)
            new_driver.find_element(By.XPATH, '//*[@id="lPass"]').send_keys(password)
            new_driver.find_element(By.XPATH, '//*[@id="btnLogin"]').click()
            time.sleep(2)

        return True
    except Exception as e:
        logger.error(e)
        return False


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
        - infos of low onboard: [[B_no, Y_num, J_num, F_num], ...]
    """

    routeId_pattern = re.compile(r"routeId:\s*(\d+)")
    routeId_matches = routeId_pattern.findall(response)

    departed_num = len(routeId_matches)
    # Find planes in json by the given routeId
    message = f"\n\t{departed_num} Planes Departed:\n\n"
    B_nos = []
    low_onboard_infos = []

    global plane_id_json
    for key, value in zip(plane_id_json.keys(), plane_id_json.values()):
        for routeId in routeId_matches:
            if routeId == str(value["routeId"]):
                B_no = key
                origin = value["origin"]
                destination = value["destination"]
                route = origin + " - " + destination
                model = value["model"]
                _, onboard = check_onboard([B_no])
                B_no, Y_num, J_num, F_num = onboard[0]

                onboard_str = str(Y_num) + " / " + str(J_num) + " / " + str(F_num)
                message += (
                    "\t\t"
                    + route
                    + "\t"
                    + B_no
                    + " - "
                    + model
                    + "\t"
                    + onboard_str
                    + "\n"
                )
                B_nos.append(B_no)
                if is_low_onboard(Y_num, J_num, F_num):
                    low_onboard_infos.append(onboard[0])

    # logger.info(message)
    return message, B_nos, low_onboard_infos


def is_low_onboard(Y_num, J_num, F_num):
    Y_weight, J_weight, F_weight = 1, 2.5, 4
    onboard_thrd = 12

    Y_num = int(Y_num)
    J_num = int(J_num)
    F_num = int(F_num)

    onboard_index = Y_num * Y_weight + J_num * J_weight + F_num * F_weight
    if onboard_index < onboard_thrd:
        return True
    else:
        return False


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
    fuel_capacity = soup.find("span", id="remCapacity").text

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
    co2_capacity = soup.find("span", id="remCapacity").text

    return fuel_price, fuel_holding, fuel_capacity, co2_price, co2_holding, co2_capacity


def get_routes_info():
    global driver

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

            origin, destination = (
                fleet.find("div", class_="col-10 text-center")
                .find("span", class_="s-text")
                .text.split(" - ")
            )

            plane_info = [B_no, routeId, checkId, model, origin, destination]
            planes_info.append(plane_info)

        start += 20

    # convert planes_info list into dictionary list
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

    # json path
    json_file_path = "planes_info.json"

    # write down on the json
    with open(json_file_path, "w", encoding="utf-8") as json_file:
        json.dump(plane_id_json, json_file, ensure_ascii=False, indent=4)

    logger.info(f"Json updated, with {len(plane_id_json)} records \n")


def ground_carry_few(B_nos=None, low_onboard_infos=None):
    """ground those planes carrying too few passengers
    
    Args:
        B-nos : A list of B_nos. If None, check all.
        low_onboard_infos : [[B_no, Y_num, J_num, F_num], ...] recording the low onboard infos. If None, check among the given B_nos.
    """
    global plane_id_json
    to_ground_count = 0
    is_grounded_count = 0
    submessage_to_ground = ""
    submessage_is_grounded = ""
    if low_onboard_infos is None:
        low_onboard_infos, _ = check_onboard(B_nos)

    for B_no, Y_num, J_num, F_num in low_onboard_infos:
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
        message = "\n\tNo planes carrying too few passangers\n"
    if is_grounded_count > 0:
        message += (
            "\n\r\tThese planes carrying too few passangers have already been grounded:\n\n"
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

    # TODO parse the response
    # logger.info("")


def ground(routeId):
    """ground A plane
    Return:
        - 1: ground
        - 2: misground
        - 0: error

    with lock
    """

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


def check_onboard(B_nos=None):
    """
    Arg :
        B_nos: if None, check all
    Return:
        low_onboard_info: [[B_no, Y_num, J_num, F_num],...]
        all_onboard_info: [[B_no, Y_num, J_num, F_num],...]
    """

    low_onboard_info = []
    all_onboard_info = []
    if B_nos is None:
        start = 0
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

                all_onboard_info.append([B_no, Y_num, J_num, F_num])
                if is_low_onboard(Y_num, J_num, F_num):
                    low_onboard_info.append([B_no, Y_num, J_num, F_num])

            start += 20
    else:
        for B_no in B_nos:
            check_id = plane_id_json[B_no]["checkId"]
            # detail page
            script = f"""
            return fetch('https://www.airlinemanager.com/fleet_details.php?id={check_id}&fbSig=false', {{
                method: 'GET',
                credentials: 'same-origin'
            }})
            .then(response => response.text())
            .then(data => {{
                return data;
            }});
            """
            try:
                with driver_lock:
                    response = driver.execute_script(script)
            except Exception as e:
                logger.error(e)

            soup = BeautifulSoup(response, "html.parser")
            try:
                # onboard of the latest record
                onboard_info = soup.find(
                    "div", class_="row bg-light m-text p-1 border"
                ).findAll("div", class_="col-3")[2]
                onboards = []
                for b_tag in onboard_info.find_all("b"):
                    next_element = b_tag.next_sibling
                    if next_element and isinstance(next_element, str):
                        number = next_element.strip().strip('"')
                        onboards.append(int(number))
                Y_num, J_num, F_num = onboards

                all_onboard_info.append([B_no, Y_num, J_num, F_num])
                if is_low_onboard(Y_num, J_num, F_num) < 12:
                    low_onboard_info.append([B_no, Y_num, J_num, F_num])
            except Exception as e:
                logger.error(e)

    return low_onboard_info, all_onboard_info


def get_fleet_detail(checkId):
    """uncompleted

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


def buy_fuels_if_low(fuel_price, co2_price, fuel_cap, co2_cap):
    """Buy fuels or Co2 if the price is low"""
    # set price threshold
    fuel_thrd = 500
    co2_thrd = 120
    has_bought = False

    fuel_price = int(fuel_price.replace("$", "").replace(",", "").strip())
    co2_price = int(co2_price.replace("$", "").replace(",", "").strip())
    fuel_cap = int(fuel_cap.replace("$", "").replace(",", "").strip())
    co2_cap = int(co2_cap.replace("$", "").replace(",", "").strip())

    if fuel_price <= fuel_thrd:
        logger.info("Fuel price is low enough, auto buying...")
        script = f"""
    return fetch('https://www.airlinemanager.com/fuel.php?mode=do&amount={fuel_cap}&fbSig=false', {{
        method: 'GET',
        credentials: 'same-origin'
    }})
    .then(response => response.text())
    .then(data => {{
        return data;
    }});
    """
        try:
            with driver_lock:
                response = driver.execute_script(script)
            has_bought = True
            # logger.info(response)
            bought_fuel_amount = re.search(r"([\d,]+) Lbs purchased", response).group(1)
            logger.info(f"Buy {bought_fuel_amount} fuel")
        except Exception as e:
            logger.error(e)

    if co2_price <= co2_thrd:
        logger.info("Co2 price is low enough, auto buying...")

        script = f"""
    return fetch('https://www.airlinemanager.com/co2.php?mode=do&amount={co2_cap}&fbSig=false', {{
        method: 'GET',
        credentials: 'same-origin'
    }})
    .then(response => response.text())
    .then(data => {{
        return data;
    }});
    """
        try:
            with driver_lock:
                response = driver.execute_script(script)
            has_bought = True
            # logger.info(response)
            bought_co2_amount = re.search(r"([\d,]+) quotas purchased", response).group(
                1
            )
            logger.info(f"Buy {bought_co2_amount} co2")
        except Exception as e:
            logger.error(e)

    if has_bought:
        display_fuels_info(*get_fuel_price())
        display_account()


def display_fuels_info(
    fuel_price, fuel_holding, fuel_capacity, co2_price, co2_holding, co2_capacity
):
    message = (
        "\n\n"
        f"\tfuel price:\t {fuel_price}\n"
        f"\tfuel holding:\t {fuel_holding}\n"
        f"\tfuel capacity:\t {fuel_capacity}\n\n"
        f"\tCo2  price:\t {co2_price}\n"
        f"\tCo2  holding:\t {co2_holding}\n"
        f"\tCo2  capacity:\t {co2_capacity}\n"
    )
    logger.info(message)


def cal_seats_dist():
    try:
        demand_Y, demand_J, demand_F, pax = map(
            float,
            input("Enter the demand of Y, J, F, and the pax of your plane:\n").split(),
        )
    except Exception as e:
        logger.error(e)
        return False

    factor = pax / (demand_Y + 2 * demand_J + 3 * demand_F)
    seats_Y = int(factor * demand_Y)
    seats_J = int(factor * demand_J)
    seats_F = int(factor * demand_F)
    diff = pax - (seats_Y + 2 * seats_J + 3 * seats_F)
    message = (
        "\n\n"
        f"\tY:\t{seats_Y}\n"
        f"\tJ:\t{seats_J}\n"
        f"\tF:\t{seats_F}\n\n"
        f"\tRemaining:\t{diff}\n"
        f"\tFactor:\t\t{round(1/factor,2)}\n"
    )
    logger.info(message)


def display_account():
    script = f"""
    return fetch('https://www.airlinemanager.com/banking.php?undefined&fbSig=false', {{
        method: 'GET',
        credentials: 'same-origin'
    }})
    .then(response => response.text())
    .then(data => {{
        return data;
    }});
    """

    try:
        with driver_lock:
            response = driver.execute_script(script)
    except Exception as e:
        logger.error(e)

    soup = BeautifulSoup(response, "html.parser")
    account = soup.find("td", class_="text-success").text

    message = f"Current Account: {account}\n"
    logger.info(message)
