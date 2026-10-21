
import httpx

from lambda_weather_air_archiver.config import (
    OPEN_METEO_AIR_QUALITY_URL,
    OPEN_METEO_FORECAST_URL,
)
from lambda_weather_air_archiver.utils import get_with_error_handling


def get_open_meteo_forecast_data(client: httpx.Client, latitude: float, longitude: float):
    forecast_params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "pressure_msl",
            "precipitation",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
            "soil_temperature_0cm",
            "cloud_cover",
        ],
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "pressure_msl",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
            "cloud_cover",
        ],
        "wind_speed_unit": "ms",
        "timezone": "Europe/Berlin",
    }
    response = get_with_error_handling(
        client=client, url=OPEN_METEO_FORECAST_URL, params=forecast_params
    )
    if response:
        data = response.json()
        print(data)


def get_open_meteo_air_quality_data(client: httpx.Client, latitude: float, longitude: float):
    air_params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ["pm10", "pm2_5", "sulphur_dioxide", "ozone", "nitrogen_dioxide"],
        "timezone": "Europe/Berlin",
    }

    response = get_with_error_handling(
        client=client, url=OPEN_METEO_AIR_QUALITY_URL, params=air_params
    )
    if response:
        data = response.json()
        print(data)


if __name__ == "__main__":
    with httpx.Client(timeout=30) as client:
        get_open_meteo_forecast_data(client=client, latitude=51.107885, longitude=17.038538)
