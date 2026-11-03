import logging
from datetime import UTC, datetime

import httpx
from pydantic import ValidationError

from lambda_weather_air_archiver.config import (
    IMGW_METEO_DATA,
    IMGW_SYNOPTIC_DATA,
)
from lambda_weather_air_archiver.models import (
    ImgwMeteoFields,
    ImgwMeteoReading,
    ImgwSnapshot,
    ImgwStation,
    ImgwSynopFields,
    ImgwSynopReading,
)
from lambda_weather_air_archiver.utils import get_with_error_handling, save_to_json

logger = logging.getLogger(__name__)

def get_imgw_stations(client: httpx.Client, url: str, name_field: str,  city: str ) -> list[ImgwStation]:
    stations : list[ImgwStation] =[]
    
    response = get_with_error_handling(client=client,url=url)
    if not response :
            logger.debug("Could not get station data from URL: %s", url)
            return stations
        
    page = response.json()


    for station in page:
        city_name = station[name_field].lower()
        if city_name == city.lower():
            imgw_station = ImgwStation.model_validate(station)
            stations.append(imgw_station)
            logger.info("Found IMGW station %s in %s", imgw_station.id, imgw_station.station_name)
            
    if logger.isEnabledFor(logging.DEBUG):
        for station in stations:
            logger.debug("Id: %s city: %s ", station.id, station.station_name)

    return stations

def get_imgw_synop_data(client: httpx.Client, station: ImgwStation) -> ImgwSynopReading | None:
    url: str = IMGW_SYNOPTIC_DATA+str(station.id)
    response = get_with_error_handling(client=client, url=url)
    if not response:
        logger.debug("Could not get station data from URL: %s", url)
        return None
    
    data = response.json()
    logger.debug("Got data for %s", station.id, extra=data)
    return ImgwSynopReading.model_validate(data)

def get_imgw_meteo_data(client: httpx.Client, station: ImgwStation) -> ImgwMeteoReading | None:
    url: str = IMGW_METEO_DATA+str(station.id)
    response = get_with_error_handling(client=client, url=url)
    if not response:
        logger.debug("Could not get station data from URL: %s", url)
        return None
        
    try:
        data = response.json()[0]
        logger.debug("Got data for %s", station.id, extra=data)
    except IndexError as e:
            logger.warning("Failed to get meteo data from station %s, %s", station.id, str(e)[:150])
            return None
    return ImgwMeteoReading.model_validate(data)

def get_imgw_data(city: str) -> None:
    meteo_stations : list[ImgwStation] = []
    synop_stations : list[ImgwStation] = []
    with httpx.Client(timeout=30) as client:
        meteo_stations = get_imgw_stations(client, IMGW_METEO_DATA, ImgwMeteoFields.NAME, city=city)
        synop_stations = get_imgw_stations(client, IMGW_SYNOPTIC_DATA, ImgwSynopFields.NAME, city=city)
        
        logger.debug("Fetching meteo data")

        for i, meteo_station in enumerate(meteo_stations, start=1):
            try: 
                logger.debug("Fetching data for station %s %s/%s", meteo_station.id, i, len(meteo_stations))
                meteo_reading  = get_imgw_meteo_data(client, meteo_station)
                meteo_station.reading = meteo_reading 
            except (KeyError , ValidationError ):
                logger.exception("Fetching data for station %s FAILED", meteo_station.id)
           
        logger.debug("Fetching synop data") 
        for i, synop_station in enumerate(synop_stations, start=1):
            try: 
                logger.debug("Fetching data for station %s %s/%s", synop_station.id, i, len(synop_stations))
                synop_reading = get_imgw_synop_data(client, synop_station)
                synop_station.reading = synop_reading
            except (KeyError , ValidationError ):
                logger.exception("Fetching data for station %s FAILED", synop_station.id)
                    
    snapshot = ImgwSnapshot(fetched_at=datetime.now(UTC), meteo_stations=meteo_stations, synop_stations=synop_stations)
    save_to_json(data=snapshot)
    if meteo_stations and synop_stations:
        logger.info("Successfuly saved values form IMGW")
