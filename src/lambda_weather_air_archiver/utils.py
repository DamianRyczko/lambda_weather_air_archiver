from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import botocore
import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from lambda_weather_air_archiver.config import RETRYABLE_STATUS, s3
from lambda_weather_air_archiver.models import GiosSnapshot, ImgwSnapshot

if TYPE_CHECKING:
    from types_boto3_s3 import S3ServiceResource

logger = logging.getLogger(__name__)

def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRYABLE_STATUS
    else:
        return isinstance(exc, (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError))
    
def save_to_json(data: ImgwSnapshot | GiosSnapshot, s3: S3ServiceResource = s3, bucket_path:str = "weather-air-data-885427126159-eu-north-1-an") -> None :
    if data:
        ts = data.fetched_at
        filepath = f"{data.source}/date={ts:%Y-%m-%d}/{ts:%H-%M-%S}.json"
        try:
            s3.Bucket(bucket_path).put_object(Key=filepath, Body=data.model_dump_json(indent=2))
        except (botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError) as e:
            logger.error("Uploading json to aws s3 %s failed: %r", filepath, e)
            raise
            
            
@retry(
    wait=wait_exponential_jitter(initial=1, max=10), 
    stop=stop_after_attempt(5), 
    retry=retry_if_exception(_is_retryable), 
    reraise=True,
    before_sleep=before_sleep_log(logger, logging.WARNING)) # type: ignore[arg-type]
def get_with_retry(client: httpx.Client, url:str, params=None) -> httpx.Response:
    response = client.get(url, params=params)
    response.raise_for_status()
    return response

def get_with_error_handling(client: httpx.Client, url:str, params=None) -> httpx.Response | None:
    try:
        response = get_with_retry(client=client, url=url, params=params)
    except httpx.HTTPStatusError as e:
        logger.error("HTTP %s for %s: %s", e.response.status_code, url, e.response.text[:100])
        return None
    except httpx.RequestError as e:
        logger.error("Request to %s failed: %r", url, e)
        return None
    
    return response 