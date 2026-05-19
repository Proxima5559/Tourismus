from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, MetaData
from slugify import slugify
from utils.extensions import db, cache
import uuid

# metadata = MetaData(naming_convention={
#     "ix": "ix_%(column_0_label)s",
#     "uq": "uq_%(table_name)s_%(column_0_name)s",
#     "ck": "ck_%(table_name)s_%(constraint_name)s",
#     "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
#     "pk": "pk_%(table_name)s"
# })

# db = SQLAlchemy(metadata=metadata)

def generate_unique_slug(model_class, text):
    base_slug = slugify(text)
    slug = base_slug
    counter = 1
    while model_class.query.filter_by(slug=slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(50), nullable=False)
    slug = db.Column(db.String(60),nullable=False)
    password_hash = db.Column(db.String(255), nullable=False) 
    email = db.Column(db.String(120), nullable=False) 
    currency = db.Column(db.String(3), nullable=True, default='USD')
    is_confirmed = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    budget = db.relationship('Budget', backref='user', cascade="all, delete-orphan")   
    expenses = db.relationship('Expense', backref='user', lazy=True, cascade="all, delete-orphan")
    category_limits = db.relationship('BudgetCategoryLimit', backref='user', lazy=True, cascade="all, delete-orphan")
    daily_plans = db.relationship(
        'DailyPlan', 
        backref='user', 
        lazy=True, 
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        db.UniqueConstraint('username', name='uq_users_username'),
        db.UniqueConstraint('email', name='uq_users_email'),
        db.UniqueConstraint('slug', name='uq_users_slug'),
    )
    
    def __init__(self, *args, **kwargs):
        if 'username' in kwargs and 'slug' not in kwargs:
            kwargs['slug'] = generate_unique_slug(User, kwargs['username'])
        super(User, self).__init__(*args, **kwargs)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)  
    # expenses = db.relationship('Expense', backref='category') 
    
    @staticmethod
    @cache.cached(timeout=3600, key_prefix='all_categories_list')
    def get_all_cached():
        return Category.query.all()
    
    __table_args__ = (
        db.UniqueConstraint('name', name='uq_category_name'),
    )

class Budget(db.Model):
    __tablename__ = 'budgets'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    amount = db.Column(db.Float, nullable=False)  
    currency = db.Column(db.String(3), nullable=False, default='USD')  
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False) 

    expenses = db.relationship('Expense', backref='budget', lazy=True, cascade="all, delete-orphan")
    limits = db.relationship('BudgetCategoryLimit', backref='budget', lazy=True, cascade="all, delete-orphan")
    daily_plans = db.relationship(
        'DailyPlan', 
        backref='budget', 
        lazy=True, 
        cascade="all, delete-orphan"
    )
    __table_args__ = (
        db.UniqueConstraint('slug', name='uq_budgets_slug'),
    )
    
    def __init__(self, *args, **kwargs):
        if 'name' in kwargs and 'slug' not in kwargs:
            kwargs['slug'] = generate_unique_slug(Budget, kwargs['name'])
        super(Budget, self).__init__(*args, **kwargs)

    @staticmethod
    def get_by_slug_or_404(slug, user_id):
        return Budget.query.filter_by(slug=slug, user_id=user_id).first_or_404()    

    @property
    def spent_amount(self):
        result = db.session.query(func.sum(Expense.amount)).filter_by(budget_id=self.id).first()
        return result[0] if result[0] else 0.0
    @property
    def status(self):
        today = datetime.now().date()
        if today < self.start_date:
            return "Upcoming"
        elif today > self.end_date:
            return "Expired"
        else:
            return "In Progress"

    @property
    def days_until_start(self):
        today = datetime.now().date()
        delta = self.start_date - today
        return max(0, delta.days)

    @property
    def days_remaining(self):
        today = datetime.now().date()
        delta = self.end_date - today
        return max(0, delta.days)
    
    def get_category_financials(self):
        results = db.session.query(
            Expense.category_id, 
            func.sum(Expense.amount)
        ).filter(Expense.budget_id == self.id).group_by(Expense.category_id).all()

        return {row[0]: row[1] or 0 for row in results}
    
class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    slug = db.Column(db.String(36), default=lambda: str(uuid.uuid4())[:8])
    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    budget_id = db.Column(db.Integer, db.ForeignKey('budgets.id', ondelete="CASCADE"), nullable=False) 
    description = db.Column(db.String(100), nullable=False)  
    amount = db.Column(db.Float, nullable=False)  
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    is_closed = db.Column(db.Boolean, default=False) 
    actual_amount = db.Column(db.Float, default=0.0)

    category = db.relationship('Category', backref='expenses')
    __table_args__ = (
        db.UniqueConstraint('slug', name='uq_expenses_slug'),
    )

class BudgetCategoryLimit(db.Model):
    __tablename__ = 'budget_category_limits'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    budget_id = db.Column(db.Integer, db.ForeignKey('budgets.id', ondelete="CASCADE"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    limit_amount = db.Column(db.Float, nullable=True)
    
    # budget = db.relationship('Budget', backref='category_limits')
    category = db.relationship('Category', backref='budget_limits')
    
    __table_args__ = (db.UniqueConstraint('budget_id', 'category_id', name='uq_budget_category'),)


class DailyPlan(db.Model):
    __tablename__ = 'daily_plans'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    slug = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4())[:12])
    budget_id = db.Column(db.Integer, db.ForeignKey('budgets.id', ondelete="CASCADE"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    tag = db.Column(db.String(50))  

    items = db.relationship('PlanItem', backref='daily_plan', cascade="all, delete-orphan", lazy=True)

    @staticmethod
    def get_user_plans_paginated(user_id, page=1, per_page=10, budget_id=None):
        query = DailyPlan.query.filter_by(user_id=user_id)
        if budget_id is not None:
            query = query.filter_by(budget_id=budget_id)
        return query.order_by(DailyPlan.date.desc()).paginate(page=page, per_page=per_page, error_out=False)

    
    def get_expenses_for_day(self):
        return Expense.query.filter(
            Expense.budget_id == self.budget_id,
            db.func.date(Expense.created_at) == self.date
        ).all()
    
    def __init__(self, *args, **kwargs):
        if 'slug' not in kwargs:
            kwargs['slug'] = str(uuid.uuid4())[:12]
        super(DailyPlan, self).__init__(*args, **kwargs)

class PlanItem(db.Model):
    __tablename__ = 'plan_items'
    id = db.Column(db.Integer, primary_key=True)
    daily_plan_id = db.Column(db.Integer, db.ForeignKey('daily_plans.id', ondelete="CASCADE"), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    is_mandatory = db.Column(db.Boolean, default=True)  
    is_completed = db.Column(db.Boolean, default=False) 
