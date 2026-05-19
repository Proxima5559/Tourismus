from flask import redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_babel import Babel
from flask_wtf.csrf import CSRFProtect
from flask_caching import Cache
from flask_migrate import Migrate
from sqlalchemy import MetaData
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from flask_admin import Admin, AdminIndexView
import requests

class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, 'is_admin', False)

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('auth.login'))

metadata = MetaData(naming_convention={
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
})

db = SQLAlchemy(metadata=metadata)
admin = Admin(name="Budget Manager", index_view=MyAdminIndexView())
limiter = Limiter(key_func=get_remote_address, 
                  default_limits=["200 per day", "50 per hour"],
                  storage_uri="memory://", 
                  strategy="fixed-window")
login_manager = LoginManager()
login_manager.session_protection = "strong"
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"
babel = Babel()
csrf = CSRFProtect()
cache = Cache(config={'CACHE_TYPE': 'SimpleCache'})
migrate = Migrate()
mail = Mail()


http_session = requests.Session()
retries = Retry(
    total=3,
    backoff_factor=0.3,
    status_forcelist=[500, 502, 503, 504] 
)
adapter = HTTPAdapter(max_retries=retries)
http_session.mount('https://', adapter)
http_session.mount('http://', adapter)