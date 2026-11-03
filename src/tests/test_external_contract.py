

from math import asin, cos, radians, sin, sqrt

import httpx

from lambda_weather_air_archiver.config import IMGW_METEO_DATA, IMGW_SYNOPTIC_DATA
from lambda_weather_air_archiver.gios import (
    get_gios_sensor_data,
    get_gios_sensors,
    get_gios_station_air_index,
    get_gios_stations,
)
from lambda_weather_air_archiver.imgw import (
    get_imgw_meteo_data,
    get_imgw_stations,
    get_imgw_synop_data,
)
from lambda_weather_air_archiver.models import (
    GiosAirIndex,
    GiosSensor,
    GiosSensorReading,
    GiosStation,
    ImgwMeteoFields,
    ImgwMeteoReading,
    ImgwStation,
    ImgwSynopFields,
    ImgwSynopReading,
    OpenMeteoAirQuality,
    OpenMeteoWeather,
)
from lambda_weather_air_archiver.openmeteo import (
    get_open_meteo_air_quality_data,
    get_open_meteo_forecast_data,
)

TEST_CITY = "Wrocław"
LATITUDE = 51.107885
LONGITUDE = 17.038538
 
def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371 * asin(sqrt(a))    # 6371 km = Earth's radius

def _get_gios_station() -> list[GiosStation]:
    stations = []
    with httpx.Client(timeout=30) as client:
        stations = get_gios_stations(client=client, city=TEST_CITY)
        
    return stations

def _get_gios_sensor() -> list[GiosSensor]:
    sensors = []
    with httpx.Client(timeout=30) as client:
        for station in _get_gios_station():
            sensors.extend(get_gios_sensors(client=client, station=station))
        
    return sensors

def _get_air_index() -> GiosAirIndex | None:
    air_data = None
    with httpx.Client(timeout=30) as client:
        for station in _get_gios_station():
            air_data = get_gios_station_air_index(client=client, station=station)
            
            if air_data is not None:
                break
            
    return air_data 

def _get_gios_sensor_readout() -> list[GiosSensorReading] | None:
    sensor_data = None
    with httpx.Client(timeout=30) as client:
        for sensor in _get_gios_sensor():
            sensor_data = get_gios_sensor_data(client=client, sensor=sensor)
            
            if sensor_data is not None:
                break
            
    return sensor_data

def _get_imgw_meteo_station() -> list[ImgwStation]:
    stations = []
    with httpx.Client(timeout=30) as client:
        stations = get_imgw_stations(client, IMGW_METEO_DATA, ImgwMeteoFields.NAME, city=TEST_CITY)

    return stations

def _get_imgw_synop_station() -> list[ImgwStation]:
    stations = []
    with httpx.Client(timeout=30) as client:
        stations = get_imgw_stations(client, IMGW_SYNOPTIC_DATA, ImgwSynopFields.NAME, city=TEST_CITY)

    return stations

def _get_imgw_meteo_readout() -> ImgwMeteoReading | None:
    meteo_data = None
    with httpx.Client(timeout=30) as client:
        for station in _get_imgw_meteo_station():
            meteo_data = get_imgw_meteo_data(client=client, station=station)

            if meteo_data is not None:
                break

    return meteo_data

def _get_imgw_synop_readout() -> ImgwSynopReading | None:
    synop_data = None
    with httpx.Client(timeout=30) as client:
        for station in _get_imgw_synop_station():
            synop_data = get_imgw_synop_data(client=client, station=station)

            if synop_data is not None:
                break

    return synop_data

def _get_open_meteo_weather() -> OpenMeteoWeather | None:
    data = None
    with httpx.Client(timeout=30) as client:
        data = get_open_meteo_forecast_data(client=client, latitude=LATITUDE, longitude=LONGITUDE)

    return data

def _get_open_meteo_air() -> OpenMeteoAirQuality | None:
    data = None
    with httpx.Client(timeout=30) as client:
        data = get_open_meteo_air_quality_data(client=client, latitude=LATITUDE, longitude=LONGITUDE)

    return data


    
def test_gios_stations():
    assert len(_get_gios_station()) > 0 
    
def test_gios_sensor():
    assert len(_get_gios_sensor()) > 0 
    
def test_gios_air_index():
    assert _get_air_index() is not None 

def test_gios_sensor_data():
    assert _get_gios_sensor_readout() is not None 

def test_imgw_meteo_stations():
    assert len(_get_imgw_meteo_station()) > 0

def test_imgw_synop_stations():
    assert len(_get_imgw_synop_station()) > 0

def test_imgw_meteo_data():
    assert _get_imgw_meteo_readout() is not None

def test_imgw_synop_data():
    assert _get_imgw_synop_readout() is not None

def test_openmeteo_weather():
    data = _get_open_meteo_weather()

    assert data is not None
    assert _distance_km(data.latitude, data.longitude, LATITUDE, LONGITUDE) < 10

def test_openmeteo_air():
    data = _get_open_meteo_air()

    assert data is not None
    assert _distance_km(data.latitude, data.longitude, LATITUDE, LONGITUDE) < 10