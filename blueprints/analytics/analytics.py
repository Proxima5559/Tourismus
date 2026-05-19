
from flask import Blueprint, render_template
from services.analytics_service import AnalyticsService


analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')


@analytics_bp.route('/<string:slug>')
def analytics_dashboard(slug):
    context = AnalyticsService.get_dashboard_context(slug)
    
    return render_template('analytics/analytics_dashboard.html', **context)