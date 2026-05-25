from flask import Flask, Blueprint, render_template, request, jsonify
from consonants_cs.constants import COUNTRY_NAMES_HY 
from utils.extensions import cache, http_session
import os
from dotenv import load_dotenv

load_dotenv()


visa_bp = Blueprint('visa', __name__, template_folder='templates', url_prefix='/visa')

@visa_bp.route('/')
def visa_page():
    return render_template('visa/visa_free.html')

def make_visa_key():
    code = request.form.get('country_code', 'default')
    return f"visa_data_{code}"

@visa_bp.route('/get_map', methods=['POST'])
@cache.cached(timeout=24, make_cache_key=make_visa_key)
def get_map():
    country = request.form.get('country_code')
    FLAG_BASE = os.getenv('FLAG_BASE', 'https://flagcdn.com/w40')
    DEFAULT_FLAG = f"{FLAG_BASE}/un.png"
    categories = {
        'VF': {'name': 'Առանց վիզայի', 'color': '#2ecc71', 'list': []},
        'VOA': {'name': 'Մուտքի արտոնագիր ժամանելիս', 'color': '#f1c40f', 'list': []},
        'EV': {'name': 'Էլեկտրոնային վիզա (e-Visa)', 'color': '#9b59b6', 'list': []}
    }

    try:
        response = http_session.get(f"https://rough-sun-2523.fly.dev/country/{country}", timeout=5)
        data = response.json()
        
        home_names = {"RU": "Russia", "AM": "Armenia", "GE": "Georgia", "US": "United States"}
        targets = [country, home_names.get(country)]

        for cat_key in categories.keys():
            raw_list = data.get(cat_key, [])
            current_category_items = []
            for item in raw_list:
                code = item.get('code')
                if not code or len(code) != 2:
                    continue
                
                targets.append(code)
                flag_url = f"{FLAG_BASE}/{code.lower()}.png"
                
                current_category_items.append({
                    'code': code.lower(),
                    'name': COUNTRY_NAMES_HY.get(code, item.get('name', code)),
                    'flag_url': flag_url
                })
            current_category_items.sort(key=lambda x: x['name'])
            categories[cat_key]['list'] = current_category_items

    except Exception as e:
        print(f"Error: {e}")
        targets = []

    return render_template('visa/map_partial.html', 
                           targets=targets, 
                           categories=categories,
                           default_flag=DEFAULT_FLAG)