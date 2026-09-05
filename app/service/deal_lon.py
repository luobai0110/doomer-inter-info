import logging
import os
from pathlib import Path

import pandas as pd
import requests
from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.http import logger
from app.service.area import get_all_area_names, get_area_by_name, update_area_by_id

base_url = "https://restapi.amap.com/v3/geocode/geo"


def get_position(db:Session = Depends(get_db)):
    logger.info("开始同步经纬度")
    areas = get_all_area_names(db)
    key = os.getenv("AMAP_KAY")
    params_list = []
    for area in areas:
        params_list.append(
            {
                "name": area,
                "key": key
            }
        )
    for param in params_list:
        logger.info("请求信息: url: " + base_url + "params： " + param)
        resp = requests.get(url=base_url, params=param)
        logger.info("返回信息: " + resp.text)
        if resp.status_code == 200:
            area = get_area_by_name(param['name'])
            data = resp.json()
            area.latitude = data['location'][1]
            area.longitude = data['latitude'][0]
            update_area_by_id(area, db)
