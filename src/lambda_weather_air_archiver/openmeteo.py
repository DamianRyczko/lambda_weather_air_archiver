
import logging
from datetime import UTC, datetime

import httpx
from pydantic import ValidationError

from lambda_weather_air_archiver.config import (
    OPEN_METEO_AIR_QUALITY_URL,
    OPEN_METEO_FORECAST_URL,
)
from lambda_weather_air_archiver.models import (
    OpenMeteoAirQuality,
    OpenMeteoAirQualityVariables,
    OpenMeteoForecastVariables,
    OpenMeteoHourlyAirQuality,
    OpenMeteoHourlyCurrentAirQuality,
    OpenMeteoHourlyCurrentWether,
    OpenMeteoHourlyForecast,
    OpenMeteoModes,
    OpenMeteoSnapshot,
    OpenMeteoWeather,
)
from lambda_weather_air_archiver.utils import get_with_error_handling, save_to_json

_METEO_FORECAST = [
    OpenMeteoForecastVariables.TEMPERATURE,
    OpenMeteoForecastVariables.RELATIVE_HUMIDITY,
    OpenMeteoForecastVariables.ATMOSPHERIC_PRESSURE,
    OpenMeteoForecastVariables.PRECIPITATION,
    OpenMeteoForecastVariables.WIND_SPEED,
    OpenMeteoForecastVariables.WIND_DIRECTION,
    OpenMeteoForecastVariables.WIND_GUSTS,
    OpenMeteoForecastVariables.SOIL_TEMPERATURE,
    OpenMeteoForecastVariables.CLOUD_COVER,
        ]

_METEO_WEATHER_CURRENT= [
    OpenMeteoForecastVariables.TEMPERATURE,
    OpenMeteoForecastVariables.RELATIVE_HUMIDITY,
    OpenMeteoForecastVariables.ATMOSPHERIC_PRESSURE,
    OpenMeteoForecastVariables.PRECIPITATION,
    OpenMeteoForecastVariables.WIND_SPEED,
    OpenMeteoForecastVariables.WIND_DIRECTION,
    OpenMeteoForecastVariables.WIND_GUSTS,
    OpenMeteoForecastVariables.CLOUD_COVER,
    ]

_METEO_AIR = [
    OpenMeteoAirQualityVariables.PM_10, 
    OpenMeteoAirQualityVariables.PM_25, 
    OpenMeteoAirQualityVariables.SO2, 
    OpenMeteoAirQualityVariables.O3, 
    OpenMeteoAirQualityVariables.NO2,
    ]

_METEO_AIR_CURRENT = [
    OpenMeteoAirQualityVariables.PM_10, 
    OpenMeteoAirQualityVariables.PM_25, 
    OpenMeteoAirQualityVariables.SO2, 
    OpenMeteoAirQualityVariables.O3, 
    OpenMeteoAirQualityVariables.NO2,
    ]

_TIME_FORMAT = "unixtime"

_WIND_SPEED_UNIT = "ms"

_FORECAST_HOURS = 72

logger = logging.getLogger(__name__)

def get_open_meteo_forecast_data(client: httpx.Client, latitude: float, longitude: float) -> OpenMeteoWeather | None:
    forecast_params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": _METEO_FORECAST,
        "current": _METEO_WEATHER_CURRENT,
        "wind_speed_unit": _WIND_SPEED_UNIT,
        "timeformat": _TIME_FORMAT,
        "forecast_hours": _FORECAST_HOURS
    }
    logger.debug("Fetching weather data from open-meteo %s", OPEN_METEO_FORECAST_URL)
    response = get_with_error_handling(
        client=client, url=OPEN_METEO_FORECAST_URL, params=forecast_params
    )
    
    if not response:
        logger.debug("Could not get data from URL: %s", OPEN_METEO_FORECAST_URL, extra=forecast_params)
        return None
    

    data = response.json()
    logger.debug("Fetching got weather data from open-meteo", extra=data)
    hourly_forecast = OpenMeteoHourlyForecast.model_validate(data[OpenMeteoModes.HOURLY])
    weather_current = OpenMeteoHourlyCurrentWether.model_validate(data[OpenMeteoModes.CURRENT])
    weather_data = OpenMeteoWeather(
        latitude=data["latitude"], 
        longitude=data["longitude"], 
        elevation = data["elevation"],
        hourly_forecast=hourly_forecast, 
        weather_current=weather_current,
        )
    return weather_data


def get_open_meteo_air_quality_data(client: httpx.Client, latitude: float, longitude: float) -> OpenMeteoAirQuality | None :
    air_params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": _METEO_AIR,
        "current": _METEO_AIR_CURRENT,
        "timeformat": _TIME_FORMAT,
        "forecast_hours": _FORECAST_HOURS
    }
    logger.debug("Fetching air data from open-meteo %s", OPEN_METEO_AIR_QUALITY_URL)
    response = get_with_error_handling(
        client=client, url=OPEN_METEO_AIR_QUALITY_URL, params=air_params
    )
    
    if not response:
        logger.debug("Could not get data from URL: %s", OPEN_METEO_AIR_QUALITY_URL, extra=air_params)
        return None

    
    data = response.json()
    logger.debug("Fetching got air data from open-meteo", extra=data)
    hourly_air = OpenMeteoHourlyAirQuality.model_validate(data[OpenMeteoModes.HOURLY])
    air_current = OpenMeteoHourlyCurrentAirQuality.model_validate(data[OpenMeteoModes.CURRENT])
    air_data = OpenMeteoAirQuality(
        latitude=data["latitude"], 
        longitude=data["longitude"], 
        elevation = data["elevation"],
        hourly_air=hourly_air, 
        air_current=air_current,
        )
    return air_data

def get_open_meteo_data(latitude: float, longitude: float):
    weather_data: OpenMeteoWeather | None = None
    air_data: OpenMeteoAirQuality | None = None
    with httpx.Client(timeout=30) as client:
        try:
            weather_data = get_open_meteo_forecast_data(client=client, latitude=latitude, longitude=longitude)
        except (KeyError , ValidationError ):
            logger.exception("Fetching weather data from open-meteo FAILED")
        try:
            air_data = get_open_meteo_air_quality_data(client=client, latitude=latitude, longitude=longitude)
        except (KeyError , ValidationError ):
            logger.exception("Fetching air data from open-meteo FAILED")
                        
        
    snapshot = OpenMeteoSnapshot(fetched_at=datetime.now(UTC), weather=weather_data, air_quality=air_data)
    save_to_json(data=snapshot)
    if weather_data and air_data:
        time_weather = weather_data.hourly_forecast.time
        time_air = air_data.hourly_air.time
        logger.info("Successfuly saved %s values from %s to %s ", min(len(time_weather),len(time_air)), min(time_weather[0],time_air[0]) , max(time_weather[-1],time_air[-1]))

