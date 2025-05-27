import requests
import time
import logging
from typing import Tuple, Optional
from dataclasses import dataclass
import os
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderQuotaExceeded
from dotenv import load_dotenv
from supabase import create_client, Client  # Add this import

load_dotenv()

GOOGLE_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Coordinates:
    latitude: float
    longitude: float
    accuracy: str = "unknown"

class GeocodingService:
    def __init__(self):
        # Initialize Supabase client
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("Supabase URL and Key must be set in environment variables.")
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.google_api_key = GOOGLE_API_KEY
        logger.info("Geocoding service initialized with Supabase")

    def get_outlets_without_coordinates(self):
        """Get outlets from Supabase that don't have coordinates yet"""
        response = self.supabase.table("outlets").select("id, name, address").is_("latitude", None).execute()
        outlets = response.data or []
        logger.info(f"Found {len(outlets)} outlets without coordinates")
        return outlets

    def geocode_with_google(self, address: str) -> Optional[Coordinates]:
        """Geocode address using Google Maps Geocoding API"""
        if not self.google_api_key:
            return None
        try:
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                'address': f"{address}",
                'key': self.google_api_key
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            print(data)
            if data['status'] == 'OK' and data['results']:
                result = data['results'][0]
                location = result['geometry']['location']
                return Coordinates(
                    latitude=location['lat'],
                    longitude=location['lng'],
                    accuracy="google"
                )
            return None
        except requests.RequestException as e:
            logger.warning(f"Google geocoding request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error with Google geocoding: {e}")
            return None

    def clean_address(self, address: str) -> str:
        """Clean and standardize address format"""
        if not address:
            return ""
        cleaned = ' '.join(address.split())
        replacements = {
            'Jln': 'Jalan',
            'Taman': 'Taman',
            'KL': 'Kuala Lumpur',
            'PJ': 'Petaling Jaya'
        }
        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)
        return cleaned

    def update_outlet_coordinates(self, outlet_id: int, coordinates: Coordinates):
        """Update outlet coordinates in Supabase"""
        try:
            update_data = {
                "latitude": coordinates.latitude,
                "longitude": coordinates.longitude
            }
            response = self.supabase.table("outlets").update(update_data).eq("id", outlet_id).execute()
            if response.data:
                logger.info(f"Updated coordinates for outlet ID {outlet_id}")
            else:
                logger.error(f"Failed to update coordinates for outlet ID {outlet_id}: {response}")
        except Exception as e:
            logger.error(f"Error updating coordinates for outlet {outlet_id}: {e}")

    def geocode_all_outlets(self):
        """Geocode all outlets without coordinates using Google Maps only"""
        outlets = self.get_outlets_without_coordinates()
        if not outlets:
            logger.info("All outlets already have coordinates")
            return
        successful_geocodes = 0
        failed_geocodes = 0
        for outlet in outlets:
            outlet_id = outlet['id']
            name = outlet['name']
            address = outlet['address']
            try:
                logger.info(f"Processing outlet: {name}")
                cleaned_address = self.clean_address(address)
                coordinates = self.geocode_with_google(cleaned_address)
                if coordinates:
                    self.update_outlet_coordinates(outlet_id, coordinates)
                    successful_geocodes += 1
                else:
                    failed_geocodes += 1
                    logger.warning(f"Failed to geocode outlet: {name}")
                time.sleep(2)
            except Exception as e:
                logger.error(f"Error processing outlet {name}: {e}")
                failed_geocodes += 1
                continue
        logger.info(f"Geocoding completed. Success: {successful_geocodes}, Failed: {failed_geocodes}")

    def cleanup(self):
        logger.info("Geocoding service cleanup completed")

def main():
    """Main function to run geocoding"""
    geocoder = GeocodingService()
    try:
        geocoder.geocode_all_outlets()
    except Exception as e:
        logger.error(f"Error during geocoding: {e}")
    finally:
        geocoder.cleanup()

if __name__ == "__main__":
    main()