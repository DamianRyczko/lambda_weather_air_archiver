import argparse
import logging

from lambda_weather_air_archiver.gios import get_gios_data
from lambda_weather_air_archiver.imgw import get_imgw_data
from lambda_weather_air_archiver.openmeteo import get_open_meteo_data

logger = logging.getLogger(__name__)
logging.getLogger("lambda_weather_air_archiver").setLevel(logging.INFO)

def main():
    parser = argparse.ArgumentParser(description="Get data from wether or air quality stations and upload them to S3")
    
    parser.add_argument("-i", "--imgw", action="store_true", help="get data from IMGW stations")
    parser.add_argument("-g", "--gios", action="store_true", help="get data from GIOS stations")
    parser.add_argument("-o", "--openmeteo", action="store_true", help="get data from OpenMeteo stations")
    parser.add_argument("--city", nargs="?", default="Wrocław", help="city for which to gather data")
    parser.add_argument("--latitude", type=float, default=51.107885, help="city for which to gather data")
    parser.add_argument("--longitude",type=float, default=17.038538, help="city for which to gather data")

    args = parser.parse_args()
    
    if args.imgw:
        try: 
            get_imgw_data(args.city)
        except Exception:
            logger.critical("Fetching IMGW data failed", exc_info=True)
            
        
    if args.gios:
        try: 
            get_gios_data(args.city)
        except Exception:
            logger.critical("Fetching GIOS data failed", exc_info=True)
        
        
    if args.openmeteo:
        try: 
            get_open_meteo_data(args.latitude, args.longitude)
        except Exception:
            logger.critical("Fetching OpenMeteo data failed", exc_info=True)
        
        
    if not args.gios and not args.imgw and not args.openmeteo:
        logger.error("Plese pick at least one of the services, -i or -imgw for IMGW, -g or -gios for GIOS and -o for OpenMeteo")
        
def lambda_handler(event, context):
    city = event.get("city", "Wrocław")
    latitude = event.get("latitude", 51.107885)
    longitude = event.get("longitude", 17.038538)
    if "imgw" in event["sources"]:
        try: 
            get_imgw_data(city)
        except Exception:
            logger.critical("Fetching IMGW data failed", exc_info=True)

    if "gios" in event["sources"]:
        try:
            get_gios_data(city)
        except Exception:
            logger.critical("Fetching GIOS data failed", exc_info=True)

    if "openmeteo" in event["sources"]:
        try:
            get_open_meteo_data(latitude, longitude)
        except Exception:
            logger.critical("Fetching OpenMeteo data failed", exc_info=True)
    

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)  
    main()

