import logging
from datetime import UTC, datetime

import httpx
from pydantic import ValidationError

from lambda_weather_air_archiver.config import (
    GIOS_AIR_QUALITY_INDEX,
    GIOS_ALL_STATIONS,
    GIOS_SENSOR_DATA,
    GIOS_SENSORS,
)
from lambda_weather_air_archiver.models import (
    GiosAirIndex,
    GiosAirIndexFields,
    GiosFields,
    GiosMeasuredPollutants,
    GiosSensor,
    GiosSensorFields,
    GiosSensorReading,
    GiosSensorReadingFields,
    GiosSnapshot,
    GiosStation,
)
from lambda_weather_air_archiver.utils import get_with_error_handling, save_to_json

logger = logging.getLogger(__name__)

class StationsNotFoundError(LookupError):
    pass

def get_gios_stations(city: str, client: httpx.Client, page_size: int = 20) -> list[GiosStation]:
    page_nr = 0
    total_pages = 1  # real value comes from the first response
    stations : list[GiosStation] = []
    
    while page_nr < total_pages:
        response = get_with_error_handling(client=client, url=GIOS_ALL_STATIONS, params={"page": page_nr, "size": page_size})
        logger.debug("Fetching GIOS stations for %s", city)
        if response:
            data = response.json()

            total_pages = data["totalPages"]

            page = data[GiosFields.STATIONS]
                    
            for station in page:
                city_name = station[GiosFields.CITY].lower()
                if city_name == city.lower():
                    logger.debug('Found GIOS station %s in %s', station[GiosFields.CODE],  station[GiosFields.CITY])
                    stations.append(GiosStation.model_validate(station))
            
        page_nr += 1
    if logger.isEnabledFor(logging.DEBUG):
        for station in stations:
            logger.debug("Id: %s Station code: %s City: %s",station.id, station.station_code, station.city, extra={"station_id": 69})

        
    return stations
        

def get_gios_sensors(client: httpx.Client, station: GiosStation, page_size: int = 100) -> list[GiosSensor]:
    gios_sensors :list[GiosSensor] = []
    stations : list[dict] = []
    page_nr = 0
    total_pages = 1  # real value comes from the first response

    while page_nr < total_pages:
        response = get_with_error_handling(client=client, url=GIOS_SENSORS+str(station.id), params={"page": page_nr, "size": page_size})
        if not response :
            logger.debug("Could not get sensor from URL: %s", GIOS_SENSORS+str(station.id))
            break
        data = response.json()
        total_pages = data.get("totalPages", 1)
        stations.extend(data[GiosSensorFields.MEASURMENT_STATIONS])
        page_nr += 1

    for measurment_station in stations:
        for pollutant in GiosMeasuredPollutants:
            if pollutant in measurment_station[GiosSensorFields.INDICATOR_CODE]:
                gios_sensors.append(GiosSensor.model_validate(measurment_station))
                logger.debug("Pollutant: %s matched to %s probe id %s", measurment_station[GiosSensorFields.INDICATOR_CODE], 
                             pollutant,  
                             measurment_station[GiosSensorFields.INDICATOR_ID])
                break 

    return gios_sensors

def get_gios_sensor_data(client: httpx.Client, sensor: GiosSensor, page_size: int = 100) -> list[GiosSensorReading]:
    sensor_readings : list[GiosSensorReading] = []
    measurments : list[dict] = []
    page_nr = 0
    total_pages = 1  # real value comes from the first response

    while page_nr < total_pages:
        response  = get_with_error_handling(client=client, url=GIOS_SENSOR_DATA+str(sensor.id), params={"page": page_nr, "size": page_size})
        if not response :
            logger.debug("Could not get sensor data from URL: %s", GIOS_SENSOR_DATA+str(sensor.id))
            break
        data = response.json()
        total_pages = data.get("totalPages", 1)
        measurments.extend(data[GiosSensorReadingFields.MEASURMENTS])
        page_nr += 1

    if page_nr == 0:  
        return sensor_readings
    for measurment in measurments:
        sensor_readings.append(GiosSensorReading.model_validate(measurment))
        
    sensor_readings.sort(key=lambda reading: reading.date)
    
    try:
        if logger.isEnabledFor(logging.DEBUG):
            oldest = sensor_readings[0]
            newest = sensor_readings[-1]
            logger.debug("Found: %s readings from %s to %s",len(sensor_readings), oldest.date, newest.date)
    except IndexError as e:
        logger.warning("Failed to get readings for sensor %s, %s", sensor.id, str(e)[:150])
    return sensor_readings
        
def get_gios_station_air_index(client: httpx.Client, station: GiosStation) -> GiosAirIndex | None:
    response  = get_with_error_handling(client=client, url=GIOS_AIR_QUALITY_INDEX+str(station.id))
    if not response:
        logger.debug("Could not get air index data from URL: %s", GIOS_AIR_QUALITY_INDEX+str(station.id))
        return None
    data = response.json()
    index =  GiosAirIndex.model_validate(data[GiosAirIndexFields.AIR_QUALITY_INDEX])
    logger.debug("Air quality reading for station %s PM10: %s PM2.5: %s O3: %s NO2: %s", 
                 station.id,
                 index.pm_10_index_reading,
                 index.pm_25_index_reading,
                 index.O3_index_reading,
                 index.NO2_index_reading
                 )
    return index

def _get_gios_redings(client: httpx.Client, station: GiosStation) ->  GiosStation:
    logger.debug("Fetching data for station %s", station.id)
    sensors = get_gios_sensors(client, station)
    readings : list[GiosSensorReading] = []
    for i, sensor in enumerate(sensors):
        try:
            logger.debug("Fetching data for sesnor %s %s/%s", sensor.id, i, len(sensors))
            readings = get_gios_sensor_data(client, sensor)
            sensor.readings = readings
        except (KeyError , ValidationError ):
                logger.warning("Fetching data for sensor %s FAILED", sensor.id)
    station.sensors = sensors
    
    logger.debug("Fetching air_index for station %s", station.id)
    try:
        air_indexes = get_gios_station_air_index(client, station)
        station.air_indexes = air_indexes
    except (KeyError , ValidationError ):
        logger.exception("Fetching air_index for station %s FAILED", station.id)    
        
    return station

def get_gios_data(city: str) -> None:
    stations: list[GiosStation] = []
    with httpx.Client(timeout=30) as client:
        stations = get_gios_stations(city=city, client=client)
        if not stations:
            logger.error("Fetching data for city %s FAILED, no stations were found", city)
            raise StationsNotFoundError("No stations found for city %s", city)
        for i, station in enumerate(stations):
            try:
                stations[i] = _get_gios_redings(client, station)
            except (KeyError , ValidationError ):
                logger.exception("Fetching data for station %s FAILED", station.id)    
    snapshot = GiosSnapshot(fetched_at=datetime.now(UTC), stations=stations)
    save_to_json(data=snapshot)
    if stations:
        logger.info("Successfuly saved values form GIOS")
