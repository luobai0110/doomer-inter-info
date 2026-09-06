from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
import requests

from app.schema.metro import MetroArrivalRecordCreate
from app.service.metro_arrival import create_metro_arrival_record_from_json

date_url = "https://data.hangzhou.gov.cn/dop/dataOpen/dataDetail.action"
file_url = "https://data.hangzhou.gov.cn/dop/dataOpen/dataFileList.action"

logger = get_logger(__name__)


def metro_update_info() -> str | None:
    ## 获取更新时间 ##
    params = {
        "source_id": "70387",
        "file_id": "",
        "source_type": "DATA",
        "pageSplit": {
            "pageNumber": 1,
            "pageSize": 10
        }
    }
    logger.info("请求地址", url=date_url, params=params)
    response = requests.post(url=date_url, data=params)
    if response.status_code == 200:
        data = response.json()
        return data['data_update_date']
    return None


def get_metro_info():
    update_date = metro_update_info()
    params = {
        "type": "ALL",
        "resId": 85055,
        "source_type_str": "A",
        "version": "",
        "source_code": "",
        "data_update_date": update_date,
        "pageSplit": {"pageNumber": 1, "pageSize": 10}
    }
    logger.info("请求地址", url=date_url, params=params)
    response = requests.post(url=file_url, data=params)
    logger.info("响应内容", url=file_url, params=params)
    json_file = []
    if response.status_code == 200:
        data = response.json()
        file_list = data['fileList']
        for file in file_list:
            if file['fileType'] == 'Json':
                json_file.append(file)

    for url in json_file:
        download_file(url['downloadPath'], url['fileName'] + '.json')


def download_file(url, filename, db: Session = Depends(get_db)):
    logger.info("下载文件", url=url, filename=filename)
    try:
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()
        if isinstance(data, list):
            for item in data[1:]:
                create_metro_arrival_record_from_json(db=db, data=item)
    except Exception as e:
        logger.error("异常", exinfo=e)
