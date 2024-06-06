import threading
import auto_depart
import fuel_monitor
import time

if __name__ == "__main__":
    # Create threads for monitoring fuel price and auto departure
    depart_thread = threading.Thread(target=auto_depart.auto_depart)
    fuel_thread = threading.Thread(target=fuel_monitor.fuel_monitor)

    # Start threads
    depart_thread.start()
    fuel_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping threads...")

        # Set stop events to signal threads to stop
        auto_depart.stop_event.set()
        fuel_monitor.stop_event.set()

        # Wait for threads to complete
        depart_thread.join()
        fuel_thread.join()

        print("Threads have been stopped.")
