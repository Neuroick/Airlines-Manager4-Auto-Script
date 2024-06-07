import auto
import time
import logging
import threading


# 设置日志
logger = logging.getLogger(__name__)

stop_event = threading.Event()
pause_event = threading.Event()

def auto_depart():
    logger.info("线程启动")

    while not stop_event.is_set():
        pause_event.wait()
        try:
            with auto.driver_lock:
                is_plane,response = auto.depart_all()
            if not is_plane:
                logger.info("No planes landed")
            else:
                depart_info = auto.get_depart_planes_info(response)
                logger.info(depart_info)
        except Exception as e:
            logger.error(e)

        # time.sleep(10)
        time_to_wait = 10  # 一边等待一边监控结束命令
        while time_to_wait > 0 and not stop_event.is_set():
            sleep_time = min(time_to_wait, 1)  # 每次睡眠1秒，或剩余的时间
            time.sleep(sleep_time)
            time_to_wait -= sleep_time


    logger.info("线程已退出")


if __name__ == "__main__":
    auto_depart()
