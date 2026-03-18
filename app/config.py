# config.py - 配置加载模块
import os
import yaml
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CONFIG_FILE = BASE_DIR / "config.yaml"

__all__ = ["config", "BASE_DIR", "load_config", "ensure_directories"]


def load_config():
    """加载配置文件"""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"配置文件不存在: {CONFIG_FILE}")

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 处理路径为绝对路径
    config["directories"]["input"] = BASE_DIR / config["directories"]["input"]
    config["directories"]["processed"] = BASE_DIR / config["directories"]["processed"]
    config["directories"]["database"] = BASE_DIR / config["directories"]["database"]
    config["directories"]["logs"] = BASE_DIR / config["directories"]["logs"]

    return config


def ensure_directories():
    """确保必要的目录存在"""
    cfg = load_config()
    for key, path in cfg["directories"].items():
        if key == "database":
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            path.mkdir(parents=True, exist_ok=True)


config = load_config()
