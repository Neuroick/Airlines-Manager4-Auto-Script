import threading
import auto_depart
import fuel_monitor
import time
import logging
import auto
import cmd
import traceback
from logger_setup import get_logger
import argparse


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
        "Initialize the driver and launch relative threads. Add '-s' to launch with a browser"
        if arg.strip() == "-s":
            show = True
        else:
            show = False

        if self.launched:
            auto.restart_driver(show=show)
        else:
            self.depart_thread = threading.Thread(
                target=auto_depart.auto_depart, daemon=True
            )
            self.fuel_thread = threading.Thread(
                target=fuel_monitor.fuel_monitor, daemon=True
            )

            # initialize driver
            with auto.driver_lock:
                auto.get_driver(show=show)

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
        "Get the route info"
        if self.launched:
            try:
                logger.info("loading...")
                auto.get_routes_info()
            except Exception as e:
                logger.error(e)
                logger.error("Traceback: %s", traceback.format_exc())

        else:
            logger.info("Driver has not been launched\n")

    def do_cal(self, arg):
        "Cal command: cal [ticket|seat]"
        try:
            parser = argparse.ArgumentParser(
                prog="cal",
                description="Cal command with ticket or seat mode",
                add_help=False,
                exit_on_error=False,
                allow_abbrev=True,
            )
            subparsers = parser.add_subparsers(dest="mode", help="Modes of cal command")

            # ticket mode
            parser_ticket = subparsers.add_parser(
                "ticket", help="Calculate the proper ticket price"
            )

            # seat mode
            parser_seat = subparsers.add_parser(
                "seat", help="Calculate the proper seat layout"
            )

            args = parser.parse_args(arg.split())

            try:
                if args.mode == "ticket":
                    auto.cal_proper_price()
                elif args.mode == "seat":
                    auto.cal_seats_dist()
                else:
                    parser.print_help()
            except Exception as e:
                logger.error(e)
                logger.error("Traceback: %s", traceback.format_exc())
        except (SystemExit, argparse.ArgumentError) as e:
            # logger.error(e)
            print("Error: unvalid command\n")
            pass

    def complete_cal(self, text, line, begidx, endidx):
        "Completion for cal command"
        subcommands = ["ticket", "seat"]
        completions = [cmd for cmd in subcommands if cmd.startswith(text)]
        return completions

    def do_check(self, arg):
        "Check command: check [fuel|account]"

        if self.launched:
            try:
                parser = argparse.ArgumentParser(
                    prog="check",
                    description="Check command with fuel or account mode",
                    add_help=False,
                    exit_on_error=False,
                    allow_abbrev=True,
                )
                subparsers = parser.add_subparsers(
                    dest="mode", help="Modes of check command"
                )

                # fuel mode
                parser_fuel = subparsers.add_parser(
                    "fuel", help="Check the current fuel price"
                )

                # account mode
                parser_account = subparsers.add_parser(
                    "account", help="Check the current account"
                )

                args = parser.parse_args(arg.split())

                try:
                    if args.mode == "fuel":
                        fuel_monitor.check_event.set()
                    elif args.mode == "account":
                        auto.display_account()
                    else:
                        parser.print_help()
                except Exception as e:
                    logger.error(e)
                    logger.error("Traceback: %s", traceback.format_exc())
            except (SystemExit, argparse.ArgumentError) as e:
                # logger.error(e)
                print("Error: unvalid command\n")
                pass
        else:
            logger.info("Driver has not been launched\n")

    def complete_check(self, text, line, begidx, endidx):
        "Completion for check command"
        subcommands = ["fuel", "account"]
        completions = [cmd for cmd in subcommands if cmd.startswith(text)]
        return completions

    def do_update_id(self, arg):
        "Update the planes_info.json which records the Ids of planes"
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
                auto.ground_carry_few()
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

    def do_game(self, arg):
        "Launch a separated driver running the game"
        auto.get_new_driver()

    def do_exit(self, arg):
        "Exit the application"
        if self.launched:
            logger.info("Stopping threads...")

            # Set stop events to signal threads to stop
            auto_depart.pause_event.set()
            auto_depart.stop_event.set()
            fuel_monitor.stop_event.set()

            # Wait for threads to complete
            self.depart_thread.join()
            self.fuel_thread.join()

            self.driver = auto.get_driver()
            self.driver.quit()

            logger.info("ALL THREADS HAVE BEEN STOPPED.")
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
