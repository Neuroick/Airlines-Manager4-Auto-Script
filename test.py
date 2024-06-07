import threading
import auto_depart
import fuel_monitor
import time
import logging
import auto

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Create threads for monitoring fuel price and auto departure
    depart_thread = threading.Thread(target=auto_depart.auto_depart, daemon=True)
    fuel_thread = threading.Thread(target=fuel_monitor.fuel_monitor, daemon=True)

    driver = auto.get_driver()

    auto_depart.pause_event.set()
    # Start threads
    depart_thread.start()
    fuel_thread.start()

    try:
        while True:
            command = input("enter your command...\n")
            if command == "pause":
                auto_depart.pause_event.clear()
                logger.info("auto_depart 已暂停")
            if command == "restart":
                auto_depart.pause_event.set()
                logger.info("auto_depart 已恢复")
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Stopping threads...")

        # Set stop events to signal threads to stop
        auto_depart.stop_event.set()
        fuel_monitor.stop_event.set()

        # Wait for threads to complete
        depart_thread.join()
        fuel_thread.join()

        logger.info("Threads have been stopped.")
