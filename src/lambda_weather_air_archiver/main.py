import logging
from datetime import datetime, timezone, UTC
from enum import StrEnum

import botocore
import httpx
from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeFloat,
    NonNegativeInt,
    JsonValue,
)
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)
import argparse
import boto3
from types_boto3_s3 import S3ServiceResource

logger = logging.getLogger(__name__)
s3 = boto3.resource('s3', region_name="eu-central-1")

RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}

GIOS_BASE_URL = "https://api.gios.gov.pl/pjp-api/v1/rest"
    
GIOS_ALL_STATIONS = GIOS_BASE_URL+"/station/findAll"
GIOS_SENSORS = GIOS_BASE_URL+"/station/sensors/" #{stationId}
GIOS_SENSOR_DATA = GIOS_BASE_URL+"/data/getData/" #{sensorId}
GIOS_AIR_QUALITY_INDEX =  GIOS_BASE_URL+"/aqindex/getIndex/" #{stationId}

GIOS_AIR_INDEX_BASE = "Wartość indeksu dla wskaźnika "
GIOS_AIR_INDEX_DATE_BASE ="Data danych źródłowych, z których policzono wartość indeksu dla wskaźnika "

IMGW_BASE_URL = "https://danepubliczne.imgw.pl/api/data"

IMGW_SYNOPTIC_DATA = IMGW_BASE_URL+"/synop/id/" #eg. 12105 # more impoertnat one 
IMGW_METEO_DATA = IMGW_BASE_URL+"/meteo/id/" # not the same as synop 

# ==================================== Enums =======================================
class GiosFields(StrEnum):
    STATIONS = 'Lista stacji pomiarowych'
    CITY = 'Nazwa miasta'
    CODE = 'Kod stacji'
    ID = 'Identyfikator stacji'
    NAME = 'Nazwa stacji'
    
   
class GiosSensorFields(StrEnum):
    MEASURMENT_STATIONS = 'Lista stanowisk pomiarowych dla podanej stacji'
    INDICATOR = 'Wskaźnik'
    INDICATOR_CODE = 'Wskaźnik - kod'
    INDICATOR_ID = 'Identyfikator stanowiska'
    
class GiosSensorReadingFields(StrEnum):
    MEASURMENTS = 'Lista danych pomiarowych'
    DATE = 'Data'
    VALUE = 'Wartość'
    
class MeasuredPollutants(StrEnum):
    PM_10 = 'PM10'
    PM_25 = 'PM2.5'
    NO2 = 'NO2'
    O3 = 'O3'
    
class GiosAirIndexFields(StrEnum):
    AIR_QUALITY_INDEX = "AqIndex"
    
    PM_10 = GIOS_AIR_INDEX_BASE + MeasuredPollutants.PM_10
    PM_25 = GIOS_AIR_INDEX_BASE + MeasuredPollutants.PM_25
    NO2 = GIOS_AIR_INDEX_BASE + MeasuredPollutants.NO2
    O3 = GIOS_AIR_INDEX_BASE + MeasuredPollutants.O3
    
    PM_10_DATE = GIOS_AIR_INDEX_DATE_BASE + MeasuredPollutants.PM_10
    PM_25_DATE = GIOS_AIR_INDEX_DATE_BASE + MeasuredPollutants.PM_25
    NO2_DATE = GIOS_AIR_INDEX_DATE_BASE +  MeasuredPollutants.NO2
    O3_DATE =GIOS_AIR_INDEX_DATE_BASE +  MeasuredPollutants.O3
    
class ImgwMeteoFields(StrEnum):
    NAME = 'nazwa_stacji'
    CODE = 'kod_stacji'
    
    GROUND_TEMEPRATIRE = 'temperatura_gruntu'
    GROUND_TEMEPRATIRE_DATE ='temperatura_gruntu_data'
    AIR_TEMEPRATIRE = 'temperatura_powietrza'
    AIR_TEMEPRATIRE_DATE = 'temperatura_powietrza_data'
    WIND_DIRECTION = 'wiatr_kierunek'
    WIND_DIRECTION_DATE = 'wiatr_kierunek_data'
    AVG_WIND_SPEED = 'wiatr_srednia_predkosc'
    AVG_WIND_SPEED_DATE = 'wiatr_srednia_predkosc_data'
    MAX_WIND_SPEED = 'wiatr_predkosc_maksymalna'
    MAX_WIND_SPEED_DATE = 'wiatr_predkosc_maksymalna_data'
    RELATIVE_HUMIDITY = 'wilgotnosc_wzgledna'
    RELATIVE_HUMIDITY_DATE = 'wilgotnosc_wzgledna_data'
    MAX_WIND_SPEED_10MIN = 'wiatr_poryw_10min'
    MAX_WIND_SPEED_10MIN_DATE = 'wiatr_poryw_10min_data'
    PRECIPITATION_10MIN = 'opad_10min'
    PRECIPITATION_10MIN_DATE = 'opad_10min_data'

class ImgwSynopFields(StrEnum):
    NAME = 'stacja'
    ID = 'id_stacji'
    READING_DATE ='data_pomiaru'
    READING_HOUR ='godzina_pomiaru'
    TEMEPRATURE = 'temperatura'
    WIND_SPEED = 'predkosc_wiatru'
    WIND_DIRECTION ='kierunek_wiatru'
    RELATIVE_HUMIDITY ='wilgotnosc_wzgledna'
    TOTAL_PRECIPITATION='suma_opadu'
    ATMOSPHERIC_PRESSURE ='cisnienie'
    

# ==================================== MODELS =======================================
class GiosSensorReading(BaseModel):
    date : datetime = Field(title="Date", validation_alias=GiosSensorReadingFields.DATE)
    value : float | None = Field(default=None, title="Sensor Reading", validation_alias=GiosSensorReadingFields.VALUE)
    
class GiosSensor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id : NonNegativeInt = Field(title="Sensor ID", validation_alias=GiosSensorFields.INDICATOR_ID)
    indicator_name : str | None = Field(default=None, title="Indicator Name", validation_alias=GiosSensorFields.INDICATOR)
    indicator_code : str | None = Field(default=None, title="Indicator Code", validation_alias=GiosSensorFields.INDICATOR_CODE)
    readings: list[GiosSensorReading] | None = Field(default=None, title="Station readings")
    
class GiosAirIndex(BaseModel):
    pm_10_index_reading : NonNegativeInt | None = Field(title="PM 10 Index", validation_alias=GiosAirIndexFields.PM_10)
    pm_25_index_reading : NonNegativeInt | None = Field(title="PM 2.5 Index", validation_alias=GiosAirIndexFields.PM_25)
    NO2_index_reading : NonNegativeInt | None = Field(title="NO2 Index", validation_alias=GiosAirIndexFields.NO2)
    O3_index_reading : NonNegativeInt | None = Field(title="O3 Index", validation_alias=GiosAirIndexFields.O3)
    pm_10_index_reading_date : str | None = Field(title="PM 10 Index measument date", validation_alias=GiosAirIndexFields.PM_10_DATE)
    pm_25_index_reading_date : str | None = Field(title="PM 2.5 Index measument date", validation_alias=GiosAirIndexFields.PM_25_DATE)
    NO2_index_reading_date : str | None = Field(title="NO2 Index measument date", validation_alias=GiosAirIndexFields.NO2_DATE)
    O3_index_reading_date : str | None = Field(title="O3 Index measument date", validation_alias=GiosAirIndexFields.O3_DATE)
    
class GiosStation(BaseModel):
    id : NonNegativeInt = Field(title="Station ID", validation_alias=GiosFields.ID)
    station_code : str | None = Field(default=None, title="Station Code", min_length=3, validation_alias=GiosFields.CODE)
    station_name : str | None = Field(default=None, title="Station Name", min_length=3, validation_alias=GiosFields.NAME)
    city: str | None = Field(default=None, title="City", min_length=3,  validation_alias=GiosFields.CITY)
    sensors: list[GiosSensor] | None = Field(default=None, title="Avialble sensors")
    air_indexes: GiosAirIndex | None = Field(default=None, title="Air inedexes")
    
class GiosSnapshot(BaseModel):
    source: str = "gios"
    fetched_at: datetime
    stations: list[GiosStation]
    
class ImgwSynopReading(BaseModel):
    date : datetime = Field(title="Date of measurment", validation_alias=ImgwSynopFields.READING_DATE)
    hour : str = Field(title="Hour of measurment", validation_alias=ImgwSynopFields.READING_HOUR)
    temperature : float = Field(title="Temperature", validation_alias=ImgwSynopFields.TEMEPRATURE)
    wind_speed : NonNegativeFloat = Field(title="Wind speed", validation_alias=ImgwSynopFields.WIND_SPEED)
    wind_direction : float = Field(title="Wind Direction", validation_alias=ImgwSynopFields.WIND_DIRECTION)
    relative_humidity : NonNegativeFloat = Field(title="Relative humidity", validation_alias=ImgwSynopFields.RELATIVE_HUMIDITY)
    total_precipitation : NonNegativeFloat = Field(title="Total precipitation", validation_alias=ImgwSynopFields.TOTAL_PRECIPITATION)
    atmospheric_pressure : NonNegativeFloat = Field(title="Atmospheric pressure", validation_alias=ImgwSynopFields.ATMOSPHERIC_PRESSURE)
    
    
class ImgwMeteoReading(BaseModel):
    ground_temperature : float | None = Field(title="Ground temperature", validation_alias=ImgwMeteoFields.GROUND_TEMEPRATIRE)
    air_temperature : float | None = Field(title="Air temperature", validation_alias=ImgwMeteoFields.AIR_TEMEPRATIRE)
    wind_direction : float | None = Field(title="Wind direction", validation_alias=ImgwMeteoFields.WIND_DIRECTION)
    wind_avg_speed : NonNegativeFloat | None = Field(title="Wind avrage speed", validation_alias=ImgwMeteoFields.AVG_WIND_SPEED)
    wind_max_speed : NonNegativeFloat | None = Field(title="Wind max speed", validation_alias=ImgwMeteoFields.MAX_WIND_SPEED)
    relative_humidity : float | None = Field(title="Relative humidity", validation_alias=ImgwMeteoFields.RELATIVE_HUMIDITY)
    wind_max_speed_10min : NonNegativeFloat | None = Field(title="Wind max speed 10min", validation_alias=ImgwMeteoFields.MAX_WIND_SPEED_10MIN)
    precipitation_10min : NonNegativeFloat | None = Field(title="Precipitation 10min", validation_alias=ImgwMeteoFields.PRECIPITATION_10MIN)
    ground_temperature_date : datetime | None = Field(title="Date of measurment - ground temperature", validation_alias=ImgwMeteoFields.GROUND_TEMEPRATIRE_DATE)
    air_temperature_date : datetime | None = Field(title="Date of measurment - air temperature", validation_alias=ImgwMeteoFields.AIR_TEMEPRATIRE_DATE)
    wind_direction_date : datetime | None = Field(title="Date of measurment - wind direction", validation_alias=ImgwMeteoFields.WIND_DIRECTION_DATE)
    wind_avg_speed_date : datetime | None = Field(title="Date of measurment - wind avg speed", validation_alias=ImgwMeteoFields.AVG_WIND_SPEED_DATE)
    wind_max_speed_date : datetime | None = Field(title="Date of measurment - wubd max speed", validation_alias=ImgwMeteoFields.MAX_WIND_SPEED_DATE)
    relative_humidity_date : datetime | None = Field(title="Date of measurment - relative humdity", validation_alias=ImgwMeteoFields.RELATIVE_HUMIDITY_DATE)
    wind_max_speed_10min_date : datetime | None = Field(title="Date of measurment - wind max speed 10 min", validation_alias=ImgwMeteoFields.MAX_WIND_SPEED_10MIN_DATE)
    precipitation_10min_date : datetime | None = Field(title="Date of measurment - precipitation 10 min", validation_alias=ImgwMeteoFields.PRECIPITATION_10MIN_DATE)

class ImgwStation(BaseModel):
    id : NonNegativeInt = Field(title="Station ID", validation_alias=AliasChoices(ImgwMeteoFields.CODE, ImgwSynopFields.ID))
    station_name : str | None = Field(default=None, title="Station Name", min_length=3, validation_alias=AliasChoices(ImgwMeteoFields.NAME, ImgwSynopFields.NAME))
    reading: ImgwMeteoReading | ImgwSynopReading | None = Field(default=None, title="Station data")
    
class ImgwSnapshot(BaseModel):
    source: str = "imgw"
    fetched_at: datetime
    meteo_stations: list[ImgwStation]
    synop_stations: list[ImgwStation]

def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRYABLE_STATUS
    else:
        return isinstance(exc, (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError))
    
def _save_to_json(data: ImgwSnapshot | GiosSnapshot, s3: S3ServiceResource = s3, bucket_path:str = "weather-air-data-885427126159-eu-north-1-an") -> None :
    if data:
        ts = data.fetched_at
        filepath = f"{data.source}/date={ts:%Y-%m-%d}/{ts:%H-%M-%S}.json"
        try:
            s3.Bucket(bucket_path).put_object(Key=filepath, Body=data.model_dump_json(indent=2))
        except botocore.exceptions.ClientError as e:
            logger.error("Uploading json to aws s3 %s failed: %r", filepath, e)
# ==================================== DECORATORS ===================================
@retry(
    wait=wait_exponential_jitter(initial=1, max=10), 
    stop=stop_after_attempt(5), 
    retry=retry_if_exception(_is_retryable), 
    reraise=True,
    before_sleep=before_sleep_log(logger, logging.WARNING)) # type: ignore[arg-type]
def _get_with_retry(client: httpx.Client, url:str, params=None) -> httpx.Response:
    response = client.get(url, params=params)
    response.raise_for_status()
    return response

def _get_with_error_handling(client: httpx.Client, url:str, params=None) -> httpx.Response | None:
    try:
        response = _get_with_retry(client=client, url=url, params=params)
    except httpx.HTTPStatusError as e:
        logger.error("HTTP %s for %s: %s", e.response.status_code, url, e.response.text[:100])
        return None
    except httpx.RequestError as e:
        logger.error("Request to %s failed: %r", url, e)
        return None
    
    return response 
# ==================================== CLASSES =======================================
def get_gios_stations(city: str, client: httpx.Client, page_size: int = 20) -> list[GiosStation]:
    page_nr = 0
    total_pages = 1  # real value comes from the first response
    stations : list[GiosStation] = []
    
    while page_nr < total_pages:
        response = _get_with_error_handling(client=client, url=GIOS_ALL_STATIONS, params={"page": page_nr, "size": page_size})
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
        

def get_gios_sensors(client: httpx.Client, station: GiosStation) -> list[GiosSensor]:
    gios_sensors :list[GiosSensor] = []
    response = _get_with_error_handling(client=client, url=GIOS_SENSORS+str(station.id))
    if not response :
        logger.debug("Could not get sensor from URL: %s", GIOS_SENSORS+str(station.id))
        return gios_sensors
    data = response.json()
    stations = data[GiosSensorFields.MEASURMENT_STATIONS]
    for measurment_station in stations:
        for pollutant in MeasuredPollutants:
            if pollutant in measurment_station[GiosSensorFields.INDICATOR_CODE]:
                gios_sensors.append(GiosSensor.model_validate(measurment_station))
                logger.debug("Pollutant: %s matched to %s probe id %s", measurment_station[GiosSensorFields.INDICATOR_CODE], 
                             pollutant,  
                             measurment_station[GiosSensorFields.INDICATOR_ID])
                break 

    return gios_sensors

def get_gios_sensor_data(client: httpx.Client, sensor: GiosSensor) -> list[GiosSensorReading]:
    sensor_readings : list[GiosSensorReading] = []
    response  = _get_with_error_handling(client=client, url=GIOS_SENSOR_DATA+str(sensor.id))
    if not response :
        logger.debug("Could not get sensor data from URL: %s", GIOS_SENSOR_DATA+str(sensor.id))
        return sensor_readings
    data = response.json()
    measurments = data[GiosSensorReadingFields.MEASURMENTS]
    for measurment in measurments:
        sensor_readings.append(GiosSensorReading.model_validate(measurment))
        
    sensor_readings.sort(key=lambda reading: reading.date)
    
    if logger.isEnabledFor(logging.DEBUG):
        oldest = sensor_readings[0]
        newest = sensor_readings[len(sensor_readings)-1]
        logger.debug("Found: %s readings from %s to %s",len(sensor_readings), oldest.date, newest.date)
    
    return sensor_readings
        
def get_gios_station_air_index(client: httpx.Client, station: GiosStation) -> GiosAirIndex | None:
    response  = _get_with_error_handling(client=client, url=GIOS_AIR_QUALITY_INDEX+str(station.id))
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
    

def get_imgw_stations(client: httpx.Client, url: str, name_field: str,  city: str ) -> list[ImgwStation]:
    stations : list[ImgwStation] =[]
    
    response = _get_with_error_handling(client=client,url=url)
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
    response = _get_with_error_handling(client=client, url=url)
    if not response:
        logger.debug("Could not get station data from URL: %s", url)
        return None
    
    data = response.json()
    logger.debug("Got data for %s", str(station.id), extra=data)
    return ImgwSynopReading.model_validate(data)

def get_imgw_meteo_data(client: httpx.Client, station: ImgwStation) -> ImgwMeteoReading | None:
    url: str = IMGW_METEO_DATA+str(station.id)
    response = _get_with_error_handling(client=client, url=url)
    if not response:
        logger.debug("Could not get station data from URL: %s", url)
        return None
        
    data = response.json()[0]
    logger.debug("Got data for %s", str(station.id), extra=data)
    return ImgwMeteoReading.model_validate(data)

def get_gios_data(city: str) -> None:
    stations : list[GiosStation] = []
    with httpx.Client(timeout=30) as client:
        stations = get_gios_stations(city=city, client=client)
        sensors : list[GiosSensor] = []
        for station in stations:
            logger.debug("Fetching data for station %s", str(station.id))
            sensors = get_gios_sensors(client, station)
            readings : list[GiosSensorReading] = []
            sensor_index = 1
            for sensor in sensors:
                logger.debug("Fetching data for sesnor %s %s/%s", str(station.id), sensor_index, len(sensors))
                readings = get_gios_sensor_data(client, sensor)
                sensor.readings = readings
                sensor_index += 1
            station.sensors = sensors
            
            logger.debug("Fetching air_index for station %s", str(station.id))
            air_indexes = get_gios_station_air_index(client, station)
            station.air_indexes = air_indexes
            
    snapshot = GiosSnapshot(fetched_at=datetime.now(UTC), stations=stations)
    _save_to_json(data=snapshot)
    print(snapshot.model_dump_json(indent=2))
            

def get_imgw_data(city: str) -> None:
    meteo_stations : list[ImgwStation] = []
    synop_stations : list[ImgwStation] = []
    with httpx.Client(timeout=30) as client:
        meteo_stations = get_imgw_stations(client, IMGW_METEO_DATA, ImgwMeteoFields.NAME, city=city)
        synop_stations = get_imgw_stations(client, IMGW_SYNOPTIC_DATA, ImgwSynopFields.NAME, city=city)
        
        logger.debug("Fetching meteo data")
        meteo_index = 1
        for meteo_station in meteo_stations:
            logger.debug("Fetching data for station %s %s/%s", str(meteo_station.id), meteo_index, len(meteo_stations))
            meteo_reading  = get_imgw_meteo_data(client, meteo_station)
            meteo_station.reading = meteo_reading 
            meteo_index += 1
           
        logger.debug("Fetching synop data") 
        synop_index = 1
        for synop_station in synop_stations:
            logger.debug("Fetching data for station %s %s/%s", str(synop_station.id), synop_index, len(synop_stations))
            synop_reading = get_imgw_synop_data(client, synop_station)
            synop_station.reading = synop_reading
            synop_index += 1
                    
    snapshot = ImgwSnapshot(fetched_at=datetime.now(UTC), meteo_stations=meteo_stations, synop_stations=synop_stations)
    _save_to_json(data=snapshot)
    print(snapshot.model_dump_json(indent=2))
        
def main():
    parser = argparse.ArgumentParser(description="Get data from wether or air quality stations and upload them to S3")
    
    parser.add_argument("-i", "--imgw", action="store_true", help="get data from IMGW stations")
    parser.add_argument("-g", "--gios", action="store_true", help="get data from GIOS stations")
    parser.add_argument("city", nargs="?", default="Wrocław", help="city for which to gather data")

    args = parser.parse_args()
    
    if args.imgw:
        get_imgw_data(args.city)
        
    if args.gios:
        get_gios_data(args.city)
        
    if not args.gios and not args.imgw:
        logger.error("Plese pick at least one of the services, -i or -imgw for IMGW and -g or -gios for GIOS")
        
        
    

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)  
    logger.setLevel(logging.DEBUG) 
    main()
    # with httpx.Client(timeout=30) as client:
    #     # stations = get_gios_stations(client)
    #     get_imgw_stations(client, IMGW_SYNOPTIC_DATA, ImgwSynopFields.NAME)
    #     get_imgw_stations(client, IMGW_METEO_DATA, ImgwMeteoFields.NAME)
    #     # get_gios_sensors(client, stations[2])
    #     # get_gios_station_air_index(client, stations[0])
        
