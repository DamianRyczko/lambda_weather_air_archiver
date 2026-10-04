import logging

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

logger = logging.getLogger(__name__)


#gios_stations_ids = [114, 115, 117, 122, 129]

GIOS_BASE_URL = "https://api.gios.gov.pl/pjp-api/v1/rest"
    
GIOS_ALL_STATIONS = GIOS_BASE_URL+"/station/findAll"
GIOS_MEASURING_STATIONS = GIOS_BASE_URL+"/station/sensors/"
GIOS_AIR_QUALITY_INDEX =  GIOS_BASE_URL+"/aqindex/getIndex/"

IMGW_BASE_URL = "https://danepubliczne.imgw.pl/api/data"

IMGW_SYNOPTIC_DATA = IMGW_BASE_URL+"/synop/id/" #eg. 12105 # more impoertnat one 
IMGW_METEO_DATA = IMGW_BASE_URL+"/meteo/id/"


@retry(wait=wait_exponential_jitter(initial=1, max=10), stop=stop_after_attempt(5))
def _get_stations(client: httpx.Client, url:str, params=None) -> httpx.Response:
    response = client.get(url, params=params)
    return response

def get_gios_stations(client: httpx.Client, page_size: int = 20, city: str = "Wrocław") -> list[dict]:
    page_nr = 0
    total_pages = 1  # real value comes from the first response
    stations_in_wroclaw = []
    
    while page_nr < total_pages:
        response = _get_stations(client=client, url=GIOS_ALL_STATIONS, params={"page": page_nr, "size": page_size})
        logger.debug("Fetching GIOS stations for %s", city)
        response.raise_for_status()
        data = response.json()

        total_pages = data["totalPages"]

        page = data["Lista stacji pomiarowych"]
        for i in range (len(page)):
            city_name = page[i]["Nazwa miasta"].lower()
            if city_name == city.lower():
                logger.debug('Found GIOS station %s in %s', page[i]["Kod stacji"],  page[i]["Nazwa miasta"])
                stations_in_wroclaw.append(page[i])
            
        page_nr += 1
    if logger.isEnabledFor(logging.DEBUG):
        for station in stations_in_wroclaw:
            logger.debug("Id: %s Station code: %s City: %s",station['Identyfikator stacji'], station['Kod stacji'], station['Nazwa miasta'], extra={"station_id": 69})

        
    return stations_in_wroclaw
        
def get_imgw_stations(client: httpx.Client, city: str = "Wrocław") -> list[dict]:
    stations_in_wroclaw = []
    
    response = _get_stations(client=client,url=IMGW_SYNOPTIC_DATA)
    response.raise_for_status()
    page = response.json()

    for i in range (len(page)):
        city_name = page[i]["stacja"].lower()
        if city_name == city.lower():
            logger.info(f'Found IMGW station {page[i]["id_stacji"]} in {page[i]["stacja"]}')
            stations_in_wroclaw.append(page[i])
            
    if logger.isEnabledFor(logging.DEBUG):
        for station in stations_in_wroclaw:
            logger.debug("Id: %s city: %s ", station['id_stacji'], station['stacja'])

    return stations_in_wroclaw

def get_imgw_meteo_stations(client: httpx.Client, city: str = "Wrocław") -> list[dict]:
    stations_in_wroclaw = []
    
    response = _get_stations(client=client,url=IMGW_METEO_DATA)
    response.raise_for_status()
    page = response.json()

    for i in range (len(page)):
        city_name = page[i]["nazwa_stacji"].lower()
        if city_name == city.lower():
            logger.info(f'Found IMGW station {page[i]["kod_stacji"]} in {page[i]["nazwa_stacji"]}')
            stations_in_wroclaw.append(page[i])
            
    if logger.isEnabledFor(logging.DEBUG):
        for station in stations_in_wroclaw:
            logger.debug("Id: %s city: %s ", station['kod_stacji'], station['nazwa_stacji'])

    return stations_in_wroclaw

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)  
    logger.setLevel(logging.DEBUG) 
    with httpx.Client(timeout=30) as client:
        get_gios_stations(client)
        get_imgw_stations(client)
        get_imgw_meteo_stations(client)
