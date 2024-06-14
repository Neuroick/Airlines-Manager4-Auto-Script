import auto
import time
import threading
from logger_setup import get_logger


logger = get_logger(__name__)

stop_event = threading.Event()
pause_event = threading.Event()


def auto_depart():
    logger.info("THREAD START")
    no_planes_count = 0
    fail_count = 0
    while not stop_event.is_set():
        pause_event.wait()
        try:
            with auto.driver_lock:
                is_plane, response = auto.depart_all()
            fail_count = 0
            if not is_plane:
                no_planes_count += 1
                if no_planes_count == 6:
                    logger.info("No planes landed\n")  # remind once a minute
            else:
                depart_info, B_nos = auto.get_depart_planes_info(response)
                logger.info(depart_info)
                no_planes_count = 0
                # auto.check_low_onboard()
                auto.ground_over_carry()
        except Exception as e:
            logger.error(e)
            fail_count += 1
            if fail_count >= 3:
                # TODO
                logger.warning(
                    f"Failed to depart for {fail_count} times. Now get a new driver."
                )
                auto.restart_driver()

        # time.sleep(10)
        time_to_wait = 10  # sleep while receiving stop event
        while time_to_wait > 0 and not stop_event.is_set():
            sleep_time = min(time_to_wait, 1)
            time.sleep(sleep_time)
            time_to_wait -= sleep_time

    logger.info("THREAD EXIT")


if __name__ == "__main__":
    auto_depart()
