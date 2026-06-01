from flask import Flask
from config import Config
from models import Expense, Budget, Category, User
from utils.admin_views import CategoryAdminView, SecureModelView, UserAdminView
from utils.extensions import db, login_manager, babel, csrf, cache, migrate, mail, limiter, admin
from utils.utils import format_currency_custom, format_date_custom
from lucide.jinja import lucide
from logger_config import setup_app_logging

from routes import main_blueprint
from blueprints.auth.auth import auth_bp
from blueprints.budget.budget import budget_bp
from blueprints.expenses.expenses import expenses_bp
from blueprints.categories.categories import category_bp
from blueprints.currency.currency import currency_bp
from blueprints.analytics.analytics import analytics_bp
from blueprints.visa.visa import visa_bp
from blueprints.places_dashboard.places_dashboard import places_dashboard_bp
from blueprints.profile.profile import profile_bp
from blueprints.plans_dash.plans_dash import plans_dash_bp
from blueprints.history.history import history_bp

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    babel.init_app(app)
    csrf.init_app(app)
    cache.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    setup_app_logging()
    
    app.jinja_env.globals.update({
        "lucide": lucide,
        "icon": lucide
    })
    app.jinja_env.filters['money'] = format_currency_custom
    app.jinja_env.filters['smart_date'] = format_date_custom

    login_manager.login_view = 'auth.login'

    if 'admin' not in app.blueprints:
        admin.init_app(app)
        admin._views = [] 
        
      
        admin.add_view(UserAdminView(User, db.session, 
                       name="Users", endpoint="admin_user", category="System"))
        
        admin.add_view(CategoryAdminView(Category, db.session, 
                       name="Categories", endpoint="admin_category", category="System"))
        
        admin.add_view(SecureModelView(Budget, db.session, 
                       name="Budgets", endpoint="admin_budget", category="Finance"))
        
        admin.add_view(SecureModelView(Expense, db.session, 
                       name="Expenses", endpoint="admin_expense", category="Finance"))
        
    app.register_blueprint(main_blueprint)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(budget_bp, url_prefix='/budget')
    app.register_blueprint(expenses_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(currency_bp, url_prefix="/currency")
    app.register_blueprint(analytics_bp)
    app.register_blueprint(visa_bp, url_prefix="/visa")
    app.register_blueprint(places_dashboard_bp, url_prefix="/places_dashboard")
    app.register_blueprint(profile_bp, url_prefix="/profile")
    app.register_blueprint(plans_dash_bp, url_prefix="/plans_dash")
    app.register_blueprint(history_bp, url_prefix="/history")

    return app