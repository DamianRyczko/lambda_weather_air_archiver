import boto3

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

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

s3 = boto3.resource('s3', region_name="eu-north-1")
