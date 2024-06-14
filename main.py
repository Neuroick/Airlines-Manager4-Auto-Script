import threading
import auto_depart
import fuel_monitor
import time
import logging
import auto
import cmd
import traceback
from logger_setup import get_logger


logger = get_logger(__name__)
# logger = logging.getLogger(__name__)


class AutoControl(cmd.Cmd):
    prompt = "(auto_control) "
    intro = """


         ___       __  .______       __       __  .__   __.  _______      _______.                                       
        /   \     |  | |   _  \     |  |     |  | |  \ |  | |   ____|    /       |                                       
       /  ^  \    |  | |  |_)  |    |  |     |  | |   \|  | |  |__      |   (----`                                       
      /  /_\  \   |  | |      /     |  |     |  | |  . `  | |   __|      \   \                                           
     /  _____  \  |  | |  |\  \----.|  `----.|  | |  |\   | |  |____ .----)   |                                          
    /__/     \__\ |__| | _| `._____||_______||__| |__| \__| |_______||_______/                                           
                                                                                                                     
                            .___  ___.      ___      .__   __.      ___        _______  _______ .______      
                            |   \/   |     /   \     |  \ |  |     /   \      /  _____||   ____||   _  \     
                            |  \  /  |    /  ^  \    |   \|  |    /  ^  \    |  |  __  |  |__   |  |_)  |    
                            |  |\/|  |   /  /_\  \   |  . `  |   /  /_\  \   |  | |_ | |   __|  |      /     
                            |  |  |  |  /  _____  \  |  |\   |  /  _____  \  |  |__| | |  |____ |  |\  \----.
                            |__|  |__| /__/     \__\ |__| \__| /__/     \__\  \______| |_______|| _| `._____|
                                                                                                                     

    =============================================================================================

        Welcome to Airlines Manager, your trusted partner in managing airline operations.

        Some basic functions are listed below:
        - Automatically depart your planes
        - Check fuel prices when they are updated, buy fuels if their prices are low
        - Calculate the proper ticket prices given the auto prices
        - ...

        Type 'help' or '?' to list all available commands.

    ==============================================================================================
    """

    def __init__(self):
        super().__init__(completekey="tab")
        # auto.setup_logger()
        self.launched = False
        auto_depart.pause_event.set()

    def do_launch(self, arg):
        "Initialize the driver and launch relative threads"
        if self.launched:
            logger.info("The program has been launched")
        else:
            self.depart_thread = threading.Thread(
                target=auto_depart.auto_depart, daemon=True
            )
            self.fuel_thread = threading.Thread(
                target=fuel_monitor.fuel_monitor, daemon=True
            )
            # time_thread = threading.Thread(target=time_displayer.display_time,daemon=True)

            # time_thread.start()

            # initialize driver
            with auto.driver_lock:
                auto.get_driver()
            self.launched = True

            # Start threads
            self.depart_thread.start()
            self.fuel_thread.start()

            auto.update_plane_info()

    def do_pause(self, arg):
        "Pause the auto_depart thread"
        if self.launched:
            auto_depart.pause_event.clear()
            logger.info("auto_depart PAUSED\n")
        else:
            logger.info("Driver has not been launched\n")

    def do_continue(self, arg):
        "Continue the auto_depart thread"
        if self.launched:
            if not auto_depart.pause_event.is_set():
                auto_depart.pause_event.set()
                logger.info("auto_depart CONTINUE\n")
            else:
                logger.info("auto_depart has been working\n")
        else:
            logger.info("Driver has not been launched\n")

    def do_route_info(self, arg):
        "Get the route info: ROUTE INFO"
        if self.launched:
            try:
                logger.info("loading...")
                auto.get_routes_info()
            except Exception as e:
                logger.error(e)
                logger.error("Traceback: %s", traceback.format_exc())

        else:
            logger.info("Driver has not been launched\n")

    def do_cal_price(self, arg):
        "Calculate the proper ticket price"
        auto.cal_proper_price()

    def do_check_fuel(self, arg):
        "Check the fuel prices: CHECK FUEL"
        if self.launched:
            fuel_monitor.check_event.set()
        else:
            logger.info("Driver has not been launched\n")

    def do_update_id(self, arg):
        "Update the planes_info.json which record the Ids of planes"
        if self.launched:
            try:
                auto.update_plane_info()
            except Exception as e:
                logger.error(e)
                logger.error("Traceback: %s", traceback.format_exc())

        else:
            logger.info("Driver has not been launched\n")

    def do_ground_out(self, arg):
        "Ground planes carrying too few passengers"
        if self.launched:
            try:
                auto.ground_over_carry()
            except Exception as e:
                logger.error(e)
                logger.error("Traceback: %s", traceback.format_exc())

    def do_bulk_check(self, arg):
        "Plan bulk check for given wear threshold"
        if self.launched:
            try:
                if arg == "":
                    auto.plan_bulk_check(wear_threshold=40)
                else:
                    if arg.isdigit():
                        auto.plan_bulk_check(arg)
            except Exception as e:
                logger.error(e)
                logger.error("Traceback: %s", traceback.format_exc())

    def do_exit(self, arg):
        "Exit the application"
        if self.launched:
            logger.info("Stopping threads...")

            # Set stop events to signal threads to stop
            auto_depart.pause_event.set()
            auto_depart.stop_event.set()
            fuel_monitor.stop_event.set()
            # time_displayer.stop_event.set()

            # Wait for threads to complete
            self.depart_thread.join()
            self.fuel_thread.join()
            # time_thread.join()

            # logger.info("Browser quit in 5 seconds...")
            # time.sleep(5)
            self.driver = auto.get_driver()
            self.driver.quit()

            logger.info("THREADS HAVE BEEN STOPPED.")
            self.launched = False

        return True

    def default(self, line):
        logger.warning(f"Command '{line}' not found\n")

    def emptyline(self):
        """Override the emptyline behavior to do nothing"""
        pass


if __name__ == "__main__":
    try:
        AutoControl().cmdloop()
    except KeyboardInterrupt:
        exit()
