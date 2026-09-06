import json

from sqlalchemy.orm import Session

from app.core.logging import get_logger
import requests

from app.schema.metro import MetroArrivalRecordCreate
from app.service.metro_arrival import create_metro_arrival_records

date_url = "https://data.hangzhou.gov.cn/dop/dataOpen/dataDetail.action"
file_url = "https://data.hangzhou.gov.cn/dop/dataOpen/dataFileList.action"

logger = get_logger(__name__)

headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}


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
    post_data_str = json.dumps(params, ensure_ascii=False)
    logger.info("请求地址", url=date_url, params=post_data_str)
    response = requests.post(url=date_url, data=f'postData={post_data_str}', headers=headers)
    logger.info("响应内容", url=date_url,resp=response.text)
    if response.status_code == 200:
        data = response.json()
        res_info = data.get("resInfo") or {}
        return res_info.get("data_update_date")
    return None


def get_metro_info(db: Session) -> int:
    update_date = metro_update_info()
    if update_date is None:
        raise ValueError("地铁数据详情接口未返回 data_update_date")

    params = {
        "type": "ALL",
        "resId": 85055,
        "source_type_str": "A",
        "version": "4",
        "source_code": "nQBNV/20220415170440338797",
        "data_update_date": update_date,
        "pageSplit": {"pageNumber": 1, "pageSize": 10}
    }
    json_data = json.dumps(params)
    logger.info("请求地址", url=date_url, params=json_data)
    response = requests.post(url=file_url, data=f'postData={json_data}')
    logger.info("响应内容", url=file_url, params=response.text)
    inserted = 0
    response.raise_for_status()
    data = response.json()
    file_list = data['fileList']
    for file in file_list:
        if file['fileType'] == 'Json':
            inserted += download_file(
                url=file['downloadPath'],
                filename=file['fileName'] + '.json',
                db=db,
            )
    logger.info("执行完成")
    return inserted


def download_file(url: str, filename: str, db: Session) -> int:
    logger.info("下载文件", url=url, filename=filename)
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    data = response.json()
    if not isinstance(data, list):
        return 0

    # 公共数据平台导出的 JSON 第一行是字段说明，不是数据。
    record_list = [
        MetroArrivalRecordCreate.model_validate(item)
        for item in data[1:]
    ]
    return len(create_metro_arrival_records(db=db, data_list=record_list))
