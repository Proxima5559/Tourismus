from app import app
from utils.extensions import db
from models import Category  

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

with app.app_context():
    try:
        for cat_name in tourist_categories:
            exists = Category.query.filter_by(name=cat_name).first()
            if not exists:
                new_category = Category(name=cat_name)
                db.session.add(new_category)
        
        db.session.commit()
        print("Successfully added 10 tourist categories!")
    except Exception as e:
        db.session.rollback()
        print(f"An error occurred: {e}")
