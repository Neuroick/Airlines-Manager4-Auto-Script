import auto
import time
import logging
import threading


# 设置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(message)s")
logger = logging.getLogger('auto_depart')

stop_event = threading.Event()


def auto_depart():

    logger.info("获取driver...")
    driver = auto.get_driver()
    logger.info("获取driver成功")

    while not stop_event.is_set():
        try:
            auto.close_popup()
            try:
                auto.click_landed()
            except:
                logger.info("未打开导航页")
                auto.open_navigation_and_click_landed()
            auto.click_depart()
        except Exception as e:
            logger.info("暂无空闲飞机")
        time.sleep(10)

    with auto.driver_lock:
        driver.quit()
    logger.info("driver 已退出")


if __name__ == "__main__":
    auto_depart()
