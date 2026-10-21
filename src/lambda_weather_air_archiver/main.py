import argparse
import logging

from lambda_weather_air_archiver.gios import get_gios_data
from lambda_weather_air_archiver.imgw import get_imgw_data

logger = logging.getLogger(__name__)

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
    logging.getLogger("lambda_weather_air_archiver").setLevel(logging.INFO)
    logger.setLevel(logging.DEBUG) 
    main()

