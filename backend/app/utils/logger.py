"""
文化DNA —— 非遗作品确权溯源系统
日志配置模块
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask


def setup_logger(app: Flask) -> None:
    """
    配置应用日志系统

    - 控制台输出：开发环境使用
    - 文件输出：按大小轮转，单文件最大10MB，保留5个备份
    - 格式：时间 | 级别 | 模块 | 消息

    Args:
        app: Flask 应用实例
    """
    log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO"))
    log_file = app.config.get("LOG_FILE", "logs/app.log")

    # 确保日志目录存在
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # 日志格式
    formatter = logging.Formatter(
        "[%(asctime)s] | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 文件处理器（按大小轮转）
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # 清除默认处理器，设置自定义处理器
    app.logger.handlers.clear()
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(log_level)

    app.logger.info("日志系统初始化完成，级别: %s", logging.getLevelName(log_level))