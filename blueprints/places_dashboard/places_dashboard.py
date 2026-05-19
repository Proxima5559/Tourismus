from flask import Blueprint, render_template
from dotenv import load_dotenv

from services.places_service import PlacesService



load_dotenv(".env")

places_dashboard_bp = Blueprint('places_dashboard', __name__, template_folder='templates', url_prefix='/places_dashboard')

# @places_dashboard_bp.route('/dashboard/historic')
# def get_historic():
#     data = PlacesService.get_dashboard_data()
#     return render_template("places_dashboard/historic.html", 
#                            historic_countries=data['historic_countries'])
    
# @places_dashboard_bp.route('/dashboard/the_safest')
# def get_the_safest():
#     data = PlacesService.get_dashboard_data()
#     return render_template("places_dashboard/the_safest.html", 
#                            safe_countries=data['safe_countries'])

@places_dashboard_bp.route('/dashboard/dangerous')
def get_dangerous():
    data = PlacesService.get_dashboard_data()
    return render_template("places_dashboard/dangerous.html", 
                           dangerous_countries=data['dangerous_countries'])

@places_dashboard_bp.route('/')
def places_dashboard():
    dashboard_data = PlacesService.get_dashboard_data()
    return render_template('places_dashboard/places_dashboard.html', **dashboard_data)

@places_dashboard_bp.route('/country/<country_code>')
def country_page(country_code):
    context = PlacesService.get_full_country_context(country_code)
    return render_template('places_dashboard/country_page/country_page.html', **context)
# GDP_API_KEY = os.getenv("GDP_API_KEY")
# TRAVELS_API_KEY = os.getenv("TRAVELS_API_KEY")

# @places_dashboard_bp.route('/')
# def places_dashboard_page():
#     return render_template('places_dashboard/places_dashboard.html')