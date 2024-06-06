import auto
import time
import logging
from datetime import datetime, timedelta
import threading

# 设置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(message)s")
logger = logging.getLogger('fuel_monitor')

stop_event = threading.Event()

def fuel_monitor():
    def wait_until_next_interval():
        # Get the current time
        now = datetime.now()

        # Determine the next whole hour or half-hour
        if now.minute < 30:
            next_interval = now.replace(minute=30, second=0, microsecond=0)
        else:
            next_interval = (now + timedelta(hours=1)).replace(
                minute=0, second=0, microsecond=0
            )

        # Calculate the time difference
        time_to_wait = (next_interval - now).total_seconds()

        logger.info(f"下次查询油价在{time_to_wait}s后")

        # Sleep in short intervals and check for stop_event
        while time_to_wait > 0 and not stop_event.is_set():
            sleep_time = min(time_to_wait, 1)  # 每次睡眠1秒，或剩余的时间
            time.sleep(sleep_time)
            time_to_wait -= sleep_time

    logger.info("获取driver...")
    driver = auto.get_driver()
    logger.info("获取driver成功")

    while not stop_event.is_set():
        try:
            logger.info("查询油价...")
            auto.get_fuel_price()
        except Exception as e:
            logger.info("查询油价失败")
            time.sleep(10)
            continue
        wait_until_next_interval()

    
    with auto.driver_lock:
        driver.quit()
    logger.info("driver 已退出")



if __name__ == "__main__":
    fuel_monitor()
