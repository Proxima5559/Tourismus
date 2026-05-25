from urllib.parse import quote
from loguru import logger
from utils.extensions import cache, http_session
from consonants_cs.constants import COUNTRY_NAMES_HY, COUNTRY_CAPITALS_HY
from consonants_cs.country_details import (
    COUNTRY_MAJOR_CITIES, COUNTRY_LANGUAGES_HY, 
    COUNTRY_NEIGHBORS_HY, CONTINENT_NAMES_HY
)
from consonants_cs.safety_rate import SAFETY_RATE
from consonants_cs.adt_details import INFRA_RATE, CLEAN_RATE, HOTTEST_RATE, EMERGENCY_NUMBERS, HOSPITALITY_RATE

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
        code = country_code.upper()
        try:
            response = http_session.get(f"https://restcountries.com/v3.1/alpha/{code}", timeout=5)
            response.raise_for_status()
            data = response.json()[0]
            idd = data.get('idd', {})
            dial_code = idd.get('root', '') + (idd.get('suffixes', [''])[0] if idd.get('suffixes') else '')
            
            return {
                "country_name_en": data.get('name', {}).get('common', code),
                "population": data.get('population', 'N/A'),
                "area": data.get('area', 'N/A'),
                "continent": data.get('region', 'N/A'),
                "timezones": data.get('timezones', []),
                "flag_url": data.get('flags', {}).get('png'),
                "dialing_code": dial_code,
                "currencies": [f"{v.get('name')} ({k})" for k, v in data.get('currencies', {}).items()]
            }
        except Exception as e:
            logger.error(f"API Error for {code}: {e}")
            return {
                "country_name_en": code,
                "population": "N/A", "area": "N/A", "continent": "N/A",
                "timezones": [], "currencies": [], "dialing_code": "N/A",
                "flag_url": f"https://flagcdn.com/w320/{code.lower()}.png"
            }

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
            **api_data
        }