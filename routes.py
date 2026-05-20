from flask import Flask, Blueprint, make_response, render_template, redirect, url_for
from flask_login import login_required

main_blueprint = Blueprint('main', __name__, template_folder='templates')
app = Flask(__name__)

@main_blueprint.route('/')
def home():
    return render_template('index.html')

@main_blueprint.route('/login')
def login():
    return render_template('login.html')

@main_blueprint.route('/go-to-login', methods=['POST'])
def go_to_login():
    response = make_response("", 200)
    response.headers['HX-Redirect'] = url_for('auth.login')
    return response

app.register_blueprint(main_blueprint)