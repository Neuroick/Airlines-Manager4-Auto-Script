import auto
import time
import logging


# 设置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)


def auto_depart():
    
    auto.login()
    while True:
        try:
            auto.close_popup()
            try:
                auto.click_landed()
            except:
                logger.info("未打开导航页，现在打开")
                auto.open_navigation_and_click_landed()
            auto.click_depart()
        except Exception as e:
            logger.info("暂无飞机到达")
        time.sleep(10)


if __name__=='__main__':
    auto_depart()