from flask_wtf import FlaskForm
from wtforms import DateField, MultipleFileField, PasswordField, StringField,  FloatField, DecimalField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, NumberRange, Regexp, ValidationError, Length
from flask_wtf.file import FileAllowed
from utils.extensions import db
from models import DailyPlan, Expense, Budget, Category, BudgetCategoryLimit, User
from sqlalchemy import func
from email_validator import validate_email, EmailNotValidError

class ExpenseForm(FlaskForm):
    description = StringField('Description', validators=[
        DataRequired(message="Description is required"),
        Length(min=2, max=32, message="Description must be between 2 and 32 characters")
    ])
    amount = DecimalField('Amount', validators=[
        DataRequired(message="Amount is required"),
        NumberRange(min=0.01, message="Amount must be positive")
    ])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired(message="Category is required")])

    def __init__(self, budget_id, *args, **kwargs):
        super(ExpenseForm, self).__init__(*args, **kwargs)
        self.budget_id = budget_id

    def validate_amount(self, field):
        budget = Budget.query.get(self.budget_id)
        
        total_spent = db.session.query(func.sum(Expense.amount)).filter_by(
            budget_id=self.budget_id
        ).scalar() or 0
        
        remaining_total = float(budget.amount) - float(total_spent)
        if float(field.data) > remaining_total:
            raise ValidationError(f"Exceeds total budget. Remaining: ${remaining_total:.2f}")

        category_limit = BudgetCategoryLimit.query.filter_by(
            budget_id=self.budget_id, 
            category_id=self.category_id.data
        ).first()

        if category_limit and category_limit.limit_amount:
            cat_spent = db.session.query(func.sum(Expense.amount)).filter_by(
                budget_id=self.budget_id, 
                category_id=self.category_id.data
            ).scalar() or 0
            
            remaining_cat = float(category_limit.limit_amount) - float(cat_spent)
            if float(field.data) > remaining_cat:
                raise ValidationError(f"Exceeds category limit. Remaining: ${remaining_cat:.2f}")


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email(message="Invalid email format.")])
    password = PasswordField('Password', validators=[DataRequired(), 
                                                     Length(min=6), 
                                                     Regexp( r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?":{}|<>]).+$',
            message="Password must contain uppercase, lowercase, number, and special character")])
    confirm_password = PasswordField('Confirm Password', 
                                    validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')
    def validate_email(self, field):
        email_data = field.data.lower().strip()
        try:
            valid = validate_email(email_data, check_deliverability=True)
            field.data = valid.email 
        except EmailNotValidError as e:
            raise ValidationError(str(e))

        user = User.query.filter_by(email=email_data).first()
        if user:
            raise ValidationError('Email already registered. Try logging in.')

    def validate_username(self, field):
        user = User.query.filter_by(username=field.data).first()
        if user:
            raise ValidationError('Username is already taken.')
        

class BudgetForm(FlaskForm):
    name = StringField('Budget Name', validators=[
        DataRequired(), 
        Length(min=3, max=100, message="Name must be between 3 and 100 characters")
    ])
    amount = DecimalField('Amount', validators=[
        DataRequired(), 
        NumberRange(min=0.01, message="Amount must be positive")
    ])
    currency = StringField('Currency', validators=[
        DataRequired(), 
        Length(max=10, message="Currency too long")
    ])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])

    def validate_end_date(self, field):
        if self.start_date.data and field.data:
            if self.start_date.data > field.data:
                raise ValidationError("End date must be after start date")
            
class CategoryLimitForm(FlaskForm):
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    limit_amount = DecimalField('Limit Amount', validators=[
        DataRequired(), 
        NumberRange(min=0.01, message="Limit must be a positive number")
    ])

    def __init__(self, budget_id, *args, **kwargs):
        super(CategoryLimitForm, self).__init__(*args, **kwargs)
        self.budget_id = budget_id

    def validate_limit_amount(self, field):
        budget = Budget.query.get(self.budget_id)
        if budget and float(field.data) > float(budget.amount):
            raise ValidationError(f"Category limit cannot exceed total budget (${budget.amount})")



class UpdateEmailForm(FlaskForm):
    email = StringField('New Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Update Email')


class PhotoUploadForm(FlaskForm):
    files = MultipleFileField('Photos', validators=[
        DataRequired(),
        FileAllowed(['jpg', 'png', 'jpeg', 'gif'], 'Images only!')
    ])
    description = StringField('Description', validators=[Length(max=255)])
    submit = SubmitField('Upload')



class DailyPlanForm(FlaskForm):
    date = DateField('Plan Date', validators=[DataRequired(message="Please select a date.")])
    tag = StringField('Tag', validators=[Length(max=50)])
    budget_id = SelectField('Linked Trip', coerce=int, validators=[DataRequired()])

    def validate_date(self, field):
        selected_budget = Budget.query.get(self.budget_id.data)
        # if not selected_budget:
        #     return

        if selected_budget:
            if field.data < selected_budget.start_date or field.data > selected_budget.end_date:
                raise ValidationError(f"Date must be between {selected_budget.start_date} and {selected_budget.end_date}.")
            
            duplicate = DailyPlan.query.filter_by(budget_id=self.budget_id.data, date=field.data).first()
            if duplicate:
                raise ValidationError("A plan for this date already exists.")
            
class TransferForm(FlaskForm):
    target_expense_id = SelectField(
        'Target Expense',
        coerce=int,
        validators=[DataRequired(message="Please select a target expense.")]
    )

    amount = FloatField( 
        'Amount',
        validators=[
            DataRequired(message="Amount is required"),
            NumberRange(min=0.01, message="Amount must be greater than zero")
        ]
    )

    def __init__(self, source_expense, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.source_expense = source_expense

    def validate_target_expense_id(self, field):
        target = Expense.query.get(field.data)
        if not target:
            raise ValidationError("Target expense not found.")
        if target.id == self.source_expense.id:
            raise ValidationError("Cannot transfer to the same expense.")
        if target.is_closed:
            raise ValidationError("Cannot transfer to a closed expense.")

    def validate_amount(self, field):
        if field.data > float(self.source_expense.amount):
            raise ValidationError(
                f"Insufficient funds! Max available: {self.source_expense.amount}"
            )