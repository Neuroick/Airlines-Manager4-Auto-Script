import auto
import time
import logging
from datetime import datetime, timedelta
import threading

# 设置日志
logger = logging.getLogger(__name__)

stop_event = threading.Event()


def fuel_monitor():
    logger.info("线程启动")

    def wait_until_next_interval():
        # Get the current time
        now = datetime.now()

        # Determine the next whole hour or half-hour
        if now.minute < 30:
            next_interval = now.replace(minute=31, second=0, microsecond=0)
        else:
            next_interval = (now + timedelta(hours=1)).replace(
                minute=1, second=0, microsecond=0
            )

        # Calculate the time difference
        time_to_wait = next_interval - now

        logger.info(f"下次查询油价在{time_to_wait}后")

        time_to_wait = time_to_wait.total_seconds()
        # Sleep in short intervals and check for stop_event
        while time_to_wait > 0 and not stop_event.is_set():
            sleep_time = min(time_to_wait, 1)  # 每次睡眠1秒，或剩余的时间
            time.sleep(sleep_time)
            time_to_wait -= sleep_time

    while not stop_event.is_set():
        try:
            logger.info("查询油价...")
            with auto.driver_lock:
                fuel_price = auto.get_fuel_price()
            message = f"当前油价：{fuel_price}"
            logger.info(message)

        except Exception as e:
            logger.info("查询油价失败")
            logger.error(e)
            time.sleep(10)
            continue
        wait_until_next_interval()

    logger.info("线程已退出")


if __name__ == "__main__":
    fuel_monitor()
