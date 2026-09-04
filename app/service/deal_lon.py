from pathlib import Path

import pandas as pd


def get_data_dir() -> Path:
    """获取项目根目录下的 data 目录。"""
    return Path(__file__).resolve().parents[2] / "data"


def read_excel() -> pd.DataFrame:
    """读取默认行政区划 Excel。"""
    return pd.read_excel(get_data_dir() / "xzqh2020-03.xlsx")
