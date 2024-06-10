import auto
import time
import logging
from datetime import datetime, timedelta
import threading

# 设置日志
logger = logging.getLogger(__name__)

stop_event = threading.Event()
check_event = threading.Event()


def fuel_monitor():
    logger.info("THREAD START")

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

        logger.info(
            f"Next Auto Check: after {time_to_wait.seconds // 60}m{time_to_wait.seconds % 60}s\n"
        )

        time_to_wait = time_to_wait.total_seconds()
        # Sleep in short intervals and check for stop_event
        while time_to_wait > 0 and not stop_event.is_set() and not check_event.is_set():
            sleep_time = min(time_to_wait, 1)  # 每次睡眠1秒，或剩余的时间
            time.sleep(sleep_time)
            time_to_wait -= sleep_time

    while not stop_event.is_set():
        try:
            with auto.driver_lock:
                fuel_price, fuel_holding, co2_price, co2_holding = auto.get_fuel_price()
            message = (
                "\n\n"
                f"\tfuel price: {fuel_price}\n"
                f"\tfuel holding: {fuel_holding}\n"
                f"\tCo2  price: {co2_price}\n"
                f"\tCo2  holding: {co2_holding}\n"
            )
            logger.info(message)
            check_event.clear()
        except Exception as e:
            logger.info("Failed to check fuel price\n")
            logger.error(e)
            time.sleep(10)
            continue
        wait_until_next_interval()

    logger.info("THREAD EXIT")


if __name__ == "__main__":
    fuel_monitor()
