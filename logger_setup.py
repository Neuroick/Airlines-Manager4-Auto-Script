import logging

def setup_logger(log_file):
    # 创建一个基础的日志配置，只需设置一次
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)  # 设置基础日志记录器的级别

    # 如果基础日志记录器已有处理器，则返回以避免重复添加处理器
    if not logger.handlers:
        # 创建一个文件处理器并设置级别
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)

        # 创建一个控制台处理器并设置级别
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 创建一个格式器并将其添加到处理器
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s : %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 将处理器添加到基础日志记录器
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

def get_logger(name):
    return logging.getLogger(name)

# 在模块导入时设置基础日志配置
setup_logger('AM4.log')
