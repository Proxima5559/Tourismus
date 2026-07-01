from urllib.parse import quote
from loguru import logger
from consonants_cs.month_places import MONTHLY_DESTINATIONS
from utils.extensions import cache, http_session
from consonants_cs.constants import COUNTRY_NAMES_HY, COUNTRY_CAPITALS_HY
from consonants_cs.country_details import (
    COUNTRY_MAJOR_CITIES, COUNTRY_LANGUAGES_HY, 
    COUNTRY_NEIGHBORS_HY, CONTINENT_NAMES_HY
)
from consonants_cs.safety_rate import SAFETY_RATE
from consonants_cs.adt_details import INFRA_RATE, CLEAN_RATE, HOTTEST_RATE, EMERGENCY_NUMBERS, HOSPITALITY_RATE
from consonants_cs.description import COUNTRY_DESCRIPTIONS_HY
import os
from dotenv import load_dotenv

load_dotenv(".env")

SAFE_COUNTRY_CODES = {"IS", "IE", "NZ", "AT", "CH", "SG", "PT", "DK", "SI", "FI"}
DANGEROUS_COUNTRY_CODES = {"AF", "YE", "SY", "LY", "SO", "SD", "SS", "HT", "UA", "MM"}
ECO_COUNTRIES = {"CR", "NO", "IS", "NZ", "EC", "CL", "PE", "PW", "SI", "KE"}
GASTRO_COUNTRIES = {"IT", "TH", "JP", "ES", "FR", "MX", "PE", "PT", "VN", "BR"}
HISTORIC_COUNTRIES = {"IT", "EG", "GR", "CN", "GB", "ES", "FR", "IN", "GE", "MX"}

class PlacesService:
    
    @staticmethod
    def _get_country_list(codes):
        return [
            {"code": code.lower(), "name": COUNTRY_NAMES_HY[code]}
            for code in sorted(codes) 
            if code in COUNTRY_NAMES_HY
        ]

    @staticmethod
    @cache.memoize(timeout=3600)
    def get_dashboard_data():
        return {
            "safe_countries": PlacesService._get_country_list(SAFE_COUNTRY_CODES),
            "dangerous_countries": PlacesService._get_country_list(DANGEROUS_COUNTRY_CODES),
            "eco_countries": PlacesService._get_country_list(ECO_COUNTRIES),
            "gastro_countries": PlacesService._get_country_list(GASTRO_COUNTRIES),
            "historic_countries": PlacesService._get_country_list(HISTORIC_COUNTRIES)
        }

    @staticmethod
    def _format_emergency_val(val):
        if isinstance(val, list):
            val = " կամ ".join(str(v) for v in val if str(v).strip())
        return str(val).strip() if str(val).strip() else "Առկա չէ"

    @staticmethod
    @cache.memoize(timeout=86400) 
    def get_external_api_data(country_code):
        code = str(country_code).strip().upper()
        api_key = os.getenv("COUNTRY_INFO_API_KEY")
        try:
            url = f"https://api.restcountries.com/countries/v5/codes.alpha_2/{code}"
            response = http_session.get(
                url, 
                headers={"Authorization": f"Bearer {api_key}"}, 
                timeout=5
            )
            response.raise_for_status()
            
            response_json = response.json()
            data = response_json.get("data", {})
            
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
            elif isinstance(data, dict) and "objects" in data:
                data = data["objects"][0] if data["objects"] else {}
                
            names_block = data.get('names', {}) or data.get('name', {}) or {}
            
            calling_codes = data.get('calling_codes', [])
            if isinstance(calling_codes, list) and calling_codes:
                dial_code = str(calling_codes[0]).strip()
            else:
                dial_code = str(data.get('dialing_code', '')) or str(data.get('dialling_code', ''))

            if dial_code and not dial_code.startswith('+') and dial_code != 'N/A':
                dial_code = f"+{dial_code}"
            dial_code = dial_code.strip() if (dial_code and dial_code != '+') else "N/A"

            raw_currencies = data.get('currencies', {})
            parsed_currencies = []
            if isinstance(raw_currencies, dict):
                parsed_currencies = [f"{v.get('name', '')} ({k})" for k, v in raw_currencies.items() if isinstance(v, dict)]
            elif isinstance(raw_currencies, list):
                parsed_currencies = [f"{item.get('name', '')} ({item.get('code', '')})" for item in raw_currencies if isinstance(item, dict)]
            
          
            raw_area = data.get('area', {})
            if isinstance(raw_area, dict):
                area_value = raw_area.get('kilometers') or raw_area.get('value') or raw_area.get('total') or 'N/A'
            else:
                area_value = raw_area
                
            if area_value and str(area_value).replace('.', '', 1).isdigit():
                area_value = int(float(area_value))
            else:
                area_value = "N/A"

            flags_block = data.get('flags', {}) or {}
            flag_url = flags_block.get('png') or flags_block.get('url')
            if not flag_url:
                flag_url = f"https://flagcdn.com/w320/{code.lower()}.png"

            return {
                "country_name_en": names_block.get('common') or data.get('name', {}).get('common', code),
                "population": data.get('population', 'N/A'),
                "area": area_value,
                "continent": data.get('region', 'N/A'),
                "timezones": data.get('timezones', []),
                "flag_url": flag_url,
                "dialing_code": dial_code,
                "currencies": parsed_currencies
            }
        except Exception as e:
            logger.error(f"API Error for {code}: {e}")
            return {
                "country_name_en": code,
                "population": "N/A", "area": "N/A", "continent": "N/A",
                "timezones": [], "currencies": [], "dialing_code": "N/A",
                "flag_url": f"https://flagcdn.com/w320/{code.lower()}.png"
            }
        
    @staticmethod
    @cache.memoize(timeout=3600)
    def get_seasonal_recommendations(month_index):
        codes = MONTHLY_DESTINATIONS.get(int(month_index), [])
        return [
            {
                "code": code.lower(), 
                "name": COUNTRY_NAMES_HY.get(code, code)
            } 
            for code in codes
        ]

    @classmethod
    def get_full_country_context(cls, country_code):
        code = country_code.upper()
        api_data = cls.get_external_api_data(code)
        
        emerg = EMERGENCY_NUMBERS.get(code, ["", "", ""])
        while len(emerg) < 3: emerg.append("")

        cities = COUNTRY_MAJOR_CITIES.get(code, [])
        major_cities = [
            {
                **city,
                "map_link": f"https://www.google.com/maps?q={quote(f'{city.get('en')}, {api_data['country_name_en']}')}&output=embed"
            }
            for city in cities
        ]

        return {
            "country_code": code,
            "country_name": COUNTRY_NAMES_HY.get(code, code),
            "capital": COUNTRY_CAPITALS_HY.get(code, "Տվյալը առկա չէ"),
            "languages": COUNTRY_LANGUAGES_HY.get(code, []),
            "neighbors": COUNTRY_NEIGHBORS_HY.get(code, []),
            "safety_rate": SAFETY_RATE.get(code),
            "hospitality_rate": HOSPITALITY_RATE.get(code),
            "continent_hy": CONTINENT_NAMES_HY.get(api_data['continent'], "Անհայտ"),
            "major_cities": major_cities,
            "stats": {
                "infra": INFRA_RATE.get(code, 0),
                "clean": CLEAN_RATE.get(code, 0),
                "temp": HOTTEST_RATE.get(code, 0),
                "hospitality": HOSPITALITY_RATE.get(code, 0),
                "emerg_police": cls._format_emergency_val(emerg[0]),
                "emerg_ambulance": cls._format_emergency_val(emerg[1]),
                "emerg_fire": cls._format_emergency_val(emerg[2])
            },
            "description": COUNTRY_DESCRIPTIONS_HY.get(code, "Նկարագրությունը առկա չէ"),
            **api_data
        }