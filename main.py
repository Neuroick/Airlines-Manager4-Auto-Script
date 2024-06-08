import threading
import auto_depart
import fuel_monitor
import time_displayer
import time
import logging
import auto
import requests
import cmd

logger = logging.getLogger(__name__)


def get_driver():
    response = requests.get("http://127.0.0.1:5000/get_driver")
    return response.json()


def quit_driver():
    response = requests.post("http://127.0.0.1:5000/quit_driver")
    return response.json()


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

        Welcome to Airline Manager, your trusted partner in managing airline operations.

        Our system offers comprehensive tools to help you streamline your airline's
        operations, maximize efficiency, and enhance passenger satisfaction.

        Here are some of the things you can do:
        - Manage flights and schedules
        - Track fleet and maintenance
        - Analyze performance and generate reports
        - Optimize routes and pricing
        - And much more...

        Type 'help' or '?' to list all available commands.

    ==============================================================================================
    """

    def __init__(self):
        super().__init__(completekey="tab")
        self.launched = False
        auto_depart.pause_event.set()

    def do_launch(self, arg):
        "Initialize the driver and launch relative threads: LAUNCH"
        self.depart_thread = threading.Thread(
            target=auto_depart.auto_depart, daemon=True
        )
        self.fuel_thread = threading.Thread(
            target=fuel_monitor.fuel_monitor, daemon=True
        )
        # time_thread = threading.Thread(target=time_displayer.display_time,daemon=True)

        # time_thread.start()

        # initialize driver
        self.driver = auto.get_driver()
        self.launched = True

        # Start threads
        self.depart_thread.start()
        self.fuel_thread.start()

    def do_pause(self, arg):
        "Pause the auto_depart thread: PAUSE"
        if self.launched:
            auto_depart.pause_event.clear()
            logger.info("auto_depart PAUSED")
        else:
            logger.info("Driver has not been launched")

    def do_continue(self, arg):
        "Continue the auto_depart thread: CONTINUE"
        if self.launched:
            if not auto_depart.pause_event.is_set():
                auto_depart.pause_event.set()
                logger.info("auto_depart CONTINUE")
            else:
                logger.info("auto_depart has been working")
        else:
            logger.info("Driver has not been launched")

    def do_route_info(self, arg):
        "Get the route info: ROUTE INFO"
        if self.launched:
            try:
                logger.info("loading...")
                auto.get_routes_info()
            except Exception as e:
                logger.error(e)
        else:
            logger.info("Driver has not been launched")

    def do_cal_price(self, arg):
        "Calculate the proper ticket price: CAL PRICE"
        auto.cal_proper_price()

    def do_check_fuel(self, arg):
        "Check the fuel prices: CHECK FUEL"
        if self.launched:
            fuel_monitor.check_event.set()
        else:
            logger.info("Driver has not been launched")

    def do_update_id(self, arg):
        "Update the planes_info.json which record the Ids of planes"
        if self.launched:
            try:
                auto.get_plane_id()
            except Exception as e:
                logger.error(e)
        else:
            logger.info("Driver has not been launched")

    def do_ground_out(self,arg):
        "Ground planes carrying too few passengers"
        if self.launched:
            try:
                auto.ground_over_carry()
            except Exception as e:
                logger.error(e)

    def do_exit(self, arg):
        "Exit the application: EXIT"
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
            self.driver.quit()

            logger.info("THREADS HAVE BEEN STOPPED.")

        return True

    def default(self, line):
        logger.warning(f"Command '{line}' not found")


if __name__ == "__main__":
    try:
        AutoControl().cmdloop()
    except KeyboardInterrupt:
        exit()
