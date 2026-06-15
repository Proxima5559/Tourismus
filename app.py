import os
from dotenv import load_dotenv

from utils.app_chunk import create_app
from utils.extensions import db, login_manager
from utils.error_handlers import register_error_handlers
from models import Category, User

load_dotenv(".env")

app = create_app()
register_error_handlers(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)

@app.context_processor
def inject_global_vars():
    from blueprints.budget.budget import BudgetForm
    return dict(form=BudgetForm())

test_password = os.getenv('TEST_PASSWORD', 'SmthIngWentWrong123!')
admin_password = os.getenv('ADMIN_PASSWORD', 'Admin_super_s12ergffg_sads')
with app.app_context():
    db.create_all()
    
    try:
        test_user = User.query.filter_by(username='test_user').first()
        if not test_user:
            test_user = User(
                username='test_user', 
                email='test@example.com',
                slug='test-user',
                currency='USD',
                is_confirmed=True,
                is_admin=False
            )
            test_user.set_password(test_password)
            db.session.add(test_user)
        
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@money.com',
                slug='admin-account',
                currency='USD',
                is_confirmed=True,
                is_admin=True 
            )
            admin_user.set_password(admin_password)
            db.session.add(admin_user)

        tourist_categories = [
            "Հյուրանոցներ",
            "Թռիչքներ",
            "Տրանսպորտ",
            "Սնունդ և ուտեստներ",
            "Տեսարժան վայրեր",
            "Գնումներ",
            "Ժամանց",
            "Հուշանվերներ",
            "Այլ",
            "Անձնական ծախսեր"
        ]

        for cat_name in tourist_categories:
            exists = Category.query.filter_by(name=cat_name).first()
            if not exists:
                new_category = Category(name=cat_name)
                db.session.add(new_category)
        
        db.session.commit()
        print("Database initialized successfully: Armenian tourist categories checked/added.")

    except Exception as e:
        db.session.rollback()
        print(f"An error occurred during database initialization: {e}")

if __name__ == '__main__':
    app.run(debug=True)