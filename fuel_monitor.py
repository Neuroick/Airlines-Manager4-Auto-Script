import auto
import time
from datetime import datetime, timedelta
import threading
from logger_setup import get_logger


logger = get_logger(__name__)

stop_event = threading.Event()
check_event = threading.Event()


def fuel_monitor():
    logger.info("THREAD START")

    def wait_until_next_interval():
        # Get the current time
        now = datetime.now()

        # Determine the next whole hour or half-hour, and check before the end of the current half-hour
        if now.minute < 29:
            next_interval = now.replace(
                minute=29, second=40, microsecond=0
            )  # check before end
        elif now.minute < 30:
            next_interval = now.replace(
                minute=30, second=10, microsecond=0
            )  # check after start
        elif now.minute < 59:
            next_interval = now.replace(
                minute=59, second=40, microsecond=0
            )  # check before end
        else:
            next_interval = (now + timedelta(hours=1)).replace(
                minute=0, second=10, microsecond=0  
            )  # check after start

        # Calculate the time difference
        time_to_wait = next_interval - now

        logger.info(
            f"Next Auto Check: after {time_to_wait.seconds // 60}m{time_to_wait.seconds % 60}s\n"
        )

        time_to_wait = time_to_wait.total_seconds()
        # Sleep in short intervals and check for stop_event
        while time_to_wait > 0 and not stop_event.is_set() and not check_event.is_set():
            sleep_time = min(time_to_wait, 1)
            time.sleep(sleep_time)
            time_to_wait -= sleep_time

    while not stop_event.is_set():
        try:
            with auto.driver_lock:
                fuel_price, fuel_holding, fuel_cap, co2_price, co2_holding, co2_cap = (
                    auto.get_fuel_price()
                )
        except Exception as e:
            logger.info("Failed to check fuel price\n")
            logger.error(e)
            time.sleep(10)
            continue

        auto.display_fuels_info(
            fuel_price, fuel_holding, fuel_cap, co2_price, co2_holding, co2_cap
        )
        check_event.clear()

        auto.buy_fuels_if_low(fuel_price, co2_price, fuel_cap, co2_cap)

        wait_until_next_interval()

    logger.info("THREAD EXIT")


if __name__ == "__main__":
    fuel_monitor()
