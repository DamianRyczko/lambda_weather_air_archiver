from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeFloat,
    NonNegativeInt,
    model_validator,
)

from lambda_weather_air_archiver.config import (
    GIOS_AIR_INDEX_BASE,
    GIOS_AIR_INDEX_DATE_BASE,
)


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
    
class GiosMeasuredPollutants(StrEnum):
    PM_10 = 'PM10'
    PM_25 = 'PM2.5'
    NO2 = 'NO2'
    O3 = 'O3'
    SO2 = 'SO2'
    
class GiosAirIndexFields(StrEnum):
    AIR_QUALITY_INDEX = "AqIndex"
    
    PM_10 = GIOS_AIR_INDEX_BASE + GiosMeasuredPollutants.PM_10
    PM_25 = GIOS_AIR_INDEX_BASE + GiosMeasuredPollutants.PM_25
    NO2 = GIOS_AIR_INDEX_BASE + GiosMeasuredPollutants.NO2
    O3 = GIOS_AIR_INDEX_BASE + GiosMeasuredPollutants.O3
    SO2 = GIOS_AIR_INDEX_BASE + GiosMeasuredPollutants.SO2
    
    PM_10_DATE = GIOS_AIR_INDEX_DATE_BASE + GiosMeasuredPollutants.PM_10
    PM_25_DATE = GIOS_AIR_INDEX_DATE_BASE + GiosMeasuredPollutants.PM_25
    NO2_DATE = GIOS_AIR_INDEX_DATE_BASE +  GiosMeasuredPollutants.NO2
    O3_DATE =GIOS_AIR_INDEX_DATE_BASE +  GiosMeasuredPollutants.O3
    SO2_DATE =GIOS_AIR_INDEX_DATE_BASE +  GiosMeasuredPollutants.SO2
    
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
    SO2_index_reading : NonNegativeInt | None = Field(title="SO2 Index", validation_alias=GiosAirIndexFields.SO2)
    pm_10_index_reading_date : str | None = Field(title="PM 10 Index measument date", validation_alias=GiosAirIndexFields.PM_10_DATE)
    pm_25_index_reading_date : str | None = Field(title="PM 2.5 Index measument date", validation_alias=GiosAirIndexFields.PM_25_DATE)
    NO2_index_reading_date : str | None = Field(title="NO2 Index measument date", validation_alias=GiosAirIndexFields.NO2_DATE)
    O3_index_reading_date : str | None = Field(title="O3 Index measument date", validation_alias=GiosAirIndexFields.O3_DATE)
    SO2_index_reading_date : str | None = Field(title="SO2 Index measument date", validation_alias=GiosAirIndexFields.SO2_DATE)
    
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
    
class OpenMeteoModes(StrEnum):
    CURRENT = "current"
    HOURLY = "hourly"
    
class OpenMeteoForecastVariables(StrEnum):
    TEMPERATURE = 'temperature_2m'
    RELATIVE_HUMIDITY = 'relative_humidity_2m'
    ATMOSPHERIC_PRESSURE = 'pressure_msl'
    PRECIPITATION = 'precipitation'
    WIND_SPEED = 'wind_speed_10m'
    WIND_DIRECTION = 'wind_direction_10m'
    WIND_GUSTS = 'wind_gusts_10m'
    SOIL_TEMPERATURE = 'soil_temperature_0_to_7cm'
    CLOUD_COVER = 'cloud_cover'

class OpenMeteoAirQualityVariables(StrEnum):
    PM_10 = 'pm10'
    PM_25 = 'pm2_5'
    NO2 = 'nitrogen_dioxide'
    O3 = 'ozone'
    SO2 = 'sulphur_dioxide'

class OpenMeteoHourly(BaseModel):
    time : list[datetime] = Field(title="Hour timestamps (UTC)")

    @model_validator(mode="after")
    def check_lengths(self) -> Self:
        expected = len(self.time)
        for name, values in self:
            if len(values) != expected:
                raise ValueError(f"{name} has {len(values)} values, expected {expected}")
        return self
    
class OpenMeteoCurrent(BaseModel):
    time : datetime = Field(title="Hour timestamp (UTC)")

class OpenMeteoHourlyForecast(OpenMeteoHourly):
    temperature : list[float | None] = Field(title="Temperature 2m", validation_alias=OpenMeteoForecastVariables.TEMPERATURE)
    relative_humidity : list[float | None] = Field(title="Relative humidity 2m", validation_alias=OpenMeteoForecastVariables.RELATIVE_HUMIDITY)
    atmospheric_pressure : list[float | None] = Field(title="Sea level pressure", validation_alias=OpenMeteoForecastVariables.ATMOSPHERIC_PRESSURE)
    precipitation : list[float | None] = Field(title="Precipitation", validation_alias=OpenMeteoForecastVariables.PRECIPITATION)
    wind_speed : list[float | None] = Field(title="Wind speed 10m", validation_alias=OpenMeteoForecastVariables.WIND_SPEED)
    wind_direction : list[float | None] = Field(title="Wind direction 10m", validation_alias=OpenMeteoForecastVariables.WIND_DIRECTION)
    wind_gusts : list[float | None] = Field(title="Wind gusts 10m", validation_alias=OpenMeteoForecastVariables.WIND_GUSTS)
    soil_temperature : list[float | None] = Field(title="Soil temperature 0-7cm", validation_alias=OpenMeteoForecastVariables.SOIL_TEMPERATURE)
    cloud_cover : list[float | None] = Field(title="Cloud cover total", validation_alias=OpenMeteoForecastVariables.CLOUD_COVER)


class OpenMeteoHourlyCurrentWether(OpenMeteoCurrent):
    temperature : float | None = Field(title="Temperature 2m", validation_alias=OpenMeteoForecastVariables.TEMPERATURE)
    relative_humidity : float | None = Field(title="Relative humidity 2m", validation_alias=OpenMeteoForecastVariables.RELATIVE_HUMIDITY)
    atmospheric_pressure : float | None = Field(title="Sea level pressure", validation_alias=OpenMeteoForecastVariables.ATMOSPHERIC_PRESSURE)
    precipitation : float | None = Field(title="Precipitation", validation_alias=OpenMeteoForecastVariables.PRECIPITATION)
    wind_speed : float | None = Field(title="Wind speed 10m", validation_alias=OpenMeteoForecastVariables.WIND_SPEED)
    wind_direction : float | None = Field(title="Wind direction 10m", validation_alias=OpenMeteoForecastVariables.WIND_DIRECTION)
    wind_gusts : float | None = Field(title="Wind gusts 10m", validation_alias=OpenMeteoForecastVariables.WIND_GUSTS)
    cloud_cover : float | None = Field(title="Cloud cover total", validation_alias=OpenMeteoForecastVariables.CLOUD_COVER)
    
class OpenMeteoHourlyAirQuality(OpenMeteoHourly):
    pm_10 : list[float | None] = Field(title="PM 10", validation_alias=OpenMeteoAirQualityVariables.PM_10)
    pm_25 : list[float | None] = Field(title="PM 2.5", validation_alias=OpenMeteoAirQualityVariables.PM_25)
    NO2 : list[float | None] = Field(title="NO2", validation_alias=OpenMeteoAirQualityVariables.NO2)
    O3 : list[float | None] = Field(title="O3", validation_alias=OpenMeteoAirQualityVariables.O3)
    SO2 : list[float | None] = Field(title="SO2", validation_alias=OpenMeteoAirQualityVariables.SO2)
    
class OpenMeteoHourlyCurrentAirQuality(OpenMeteoCurrent):
    pm_10 : float | None = Field(title="PM 10", validation_alias=OpenMeteoAirQualityVariables.PM_10)
    pm_25 : float | None = Field(title="PM 2.5", validation_alias=OpenMeteoAirQualityVariables.PM_25)
    NO2 : float | None = Field(title="NO2", validation_alias=OpenMeteoAirQualityVariables.NO2)
    O3 : float | None = Field(title="O3", validation_alias=OpenMeteoAirQualityVariables.O3)
    SO2 : float | None = Field(title="SO2", validation_alias=OpenMeteoAirQualityVariables.SO2)

class OpenMeteoLocation(BaseModel):
    latitude : float = Field(title="Grid latitude")
    longitude : float = Field(title="Grid longitude")
    elevation : float | None = Field(default=None, title="Grid elevation")

class OpenMeteoWeather(OpenMeteoLocation):
    hourly_forecast : OpenMeteoHourlyForecast = Field(title="Hourly forecast")
    weather_current : OpenMeteoHourlyCurrentWether = Field(title="Current wather reading")
    
class OpenMeteoAirQuality(OpenMeteoLocation):
    hourly_air : OpenMeteoHourlyAirQuality = Field(title="Hourly air quality forecast")
    air_current : OpenMeteoHourlyCurrentAirQuality = Field(title="Current air quality")

class OpenMeteoSnapshot(BaseModel):
    source: str = "openmeteo"
    fetched_at: datetime
    weather: OpenMeteoWeather | None
    air_quality: OpenMeteoAirQuality | None
