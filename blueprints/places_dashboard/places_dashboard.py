from flask import Blueprint, render_template
from dotenv import load_dotenv
from consonants_cs.month_places import MONTHS_HY
from services.places_service import PlacesService
from datetime import datetime

load_dotenv(".env")

places_dashboard_bp = Blueprint('places_dashboard', __name__, template_folder='templates', url_prefix='/places_dashboard')

@places_dashboard_bp.route('/')
def places_dashboard():
    dashboard_data = PlacesService.get_dashboard_data()
    current_month_idx = datetime.now().month
    return render_template('places_dashboard/places_dashboard.html', months_hy=MONTHS_HY, current_month=current_month_idx, **dashboard_data)

@places_dashboard_bp.route('/dashboard/the_safest')
def get_the_safest():
    data = PlacesService.get_dashboard_data()
    return render_template("places_dashboard/the_safest.html", 
                           safe_countries=data['safe_countries'])

@places_dashboard_bp.route('/dashboard/dangerous')
def get_dangerous():
    data = PlacesService.get_dashboard_data()
    return render_template("places_dashboard/dangerous.html", 
                           dangerous_countries=data['dangerous_countries'])

@places_dashboard_bp.route('/country/<country_code>')
def country_page(country_code):
    context = PlacesService.get_full_country_context(country_code)
    return render_template('places_dashboard/country_page/country_page.html', **context)

@places_dashboard_bp.route('/seasonal/<int:month>')
def get_seasonal(month):
    countries = PlacesService.get_seasonal_recommendations(month)
    month_name = MONTHS_HY.get(month)
    return render_template("places_dashboard/seasonal_list.html", 
                           countries=countries, 
                           month_name=month_name)
