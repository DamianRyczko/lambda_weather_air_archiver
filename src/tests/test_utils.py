from datetime import UTC, datetime

import boto3
import httpx
import pytest
import respx
from botocore.exceptions import ClientError
from moto import mock_aws
from tenacity import wait_none

from lambda_weather_air_archiver.models import GiosSnapshot
from lambda_weather_air_archiver.utils import (
    get_with_error_handling,
    get_with_retry,
    save_to_json,
)

TEST_URL = "https://example.test/data"

@pytest.fixture(autouse=True)
def no_retry_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_with_retry.retry, "wait", wait_none())  # type: ignore[attr-defined]

@respx.mock
def test_temporary_error_is_retried():
    route = respx.get(TEST_URL).mock(side_effect=[
        httpx.Response(503),
        httpx.Response(200, json={}),
    ])

    with httpx.Client(timeout=30) as client:
        response = get_with_error_handling(client=client, url=TEST_URL)

    assert response is not None
    assert route.call_count == 2

@respx.mock
def test_permanent_error_is_not_retried():
    route = respx.get(TEST_URL).mock(return_value=httpx.Response(400))

    with httpx.Client(timeout=30) as client:
        response = get_with_error_handling(client=client, url=TEST_URL)

    assert response is None
    assert route.call_count == 1

@respx.mock
def test_request_that_keeps_failing_gives_up():
    respx.get(TEST_URL).mock(side_effect=httpx.ConnectTimeout)

    with httpx.Client(timeout=30) as client:
        response = get_with_error_handling(client=client, url=TEST_URL)

    assert response is None

@mock_aws
def test_failed_upload_raises():
    s3 = boto3.resource("s3", region_name="eu-north-1")
    snapshot = GiosSnapshot(fetched_at=datetime.now(UTC), stations=[])

    with pytest.raises(ClientError):
        save_to_json(data=snapshot, s3=s3, bucket_path="missing-bucket")
