from flask import Blueprint, request, render_template, make_response
import flask
from models import Expense, Budget, Category, BudgetCategoryLimit
from utils.extensions import db
from utils.decorators import confirmed_required
from utils.forms import ExpenseForm, TransferForm
from sqlalchemy import func
from flask_login import current_user, login_required
from loguru import logger
import json
from sqlalchemy.orm import joinedload
from services.expense_service import ExpenseService


expenses_bp = Blueprint('expenses', __name__)


@expenses_bp.route('/budget/<string:slug>/add-expense', methods=['POST'])
@login_required
@confirmed_required
def add_expense(slug):
    budget = Budget.query.filter_by(slug=slug).first_or_404()
    form = ExpenseForm(budget_id=budget.id)
    form.category_id.choices = [(c.id, c.name) for c in Category.get_all_cached()]

    if form.validate_on_submit():
        try:
            expense = Expense(
                budget_id=budget.id,
                user_id=budget.user_id,
                description=form.description.data,
                amount=form.amount.data,
                category_id=form.category_id.data
            )
            db.session.add(expense)
            db.session.commit()
            return ExpenseService.render_budget_state(budget.id, page=1)
        except Exception as e:
            db.session.rollback()
            response = make_response(render_template('budget/expense/expense_result.html', error="Database error."), 500)
            response.headers['HX-Retarget'] = '#error-container'
            return response

    error_msg = list(form.errors.values())[0][0] if form.errors else "Invalid input"
    response = make_response(render_template('budget/expense/expense_result.html', error=error_msg), 200)
    response.headers['HX-Retarget'] = '#error-container'
    return response

@expenses_bp.route('/<int:expense_id>', methods=['DELETE'])
@login_required
@confirmed_required
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)

    if expense.user_id != current_user.id:
        return "Unauthorized", 403

    try:
        budget_id = expense.budget_id
        db.session.delete(expense)
        db.session.commit()

        logger.info("Expense deleted | id={} budget_id={}", expense_id, budget_id)

    except Exception as e:
        db.session.rollback()
        logger.exception("Failed to delete expense {}: {}", expense_id, e)
        return "Error deleting expense", 500

    return ExpenseService.render_budget_state(budget_id)


@expenses_bp.route('/delete_all/<int:budget_id>', methods=['DELETE'])
@login_required
@confirmed_required
def delete_all_expenses(budget_id):
    budget = Budget.query.get_or_404(budget_id)

    if budget.user_id != current_user.id:
        return "Unauthorized", 403

    try:
        deleted = Expense.query.filter_by(budget_id=budget_id).delete()
        db.session.commit()

        logger.warning(
            "All expenses deleted | budget_id={} count={}",
            budget_id, deleted
        )

    except Exception as e:
        db.session.rollback()
        logger.exception("Failed to delete all expenses for budget {}: {}", budget_id, e)
        return "Error deleting expenses", 500

    return ExpenseService.render_budget_state(budget_id)

@expenses_bp.get("/<string:slug>/filter")
@login_required
@confirmed_required
def filter_expenses(slug):
    try:
        category_id = request.args.get("category_id")
        page = request.args.get("page", 1, type=int) 

        budget = Budget.query.filter_by(slug=slug).first_or_404()
        categories = Category.get_all_cached()

        q = Expense.query.filter_by(budget_id=budget.id)

        selected_category = None

        if category_id and category_id.isdigit():
            selected_category = int(category_id)
            q = q.filter(Expense.category_id == selected_category)

        pagination = ExpenseService.paginate_expenses(budget.id, page=page, per_page=10, category_id=category_id)

        return render_template(
            "budget/expense/expenses_table.html",
            budget=budget,
            expenses=pagination.items,         
            total_pages=pagination.pages,      
            current_page=page,
            categories=categories,
            selected_category=selected_category 
        )
    except Exception as e:
        logger.error(f"Error filtering expenses: {e}")
        msg = f"Failed to load expenses: {str(e)}"
        oob = f"<div id=\"swal-oob\" hx-swap-oob=\"true\"><script>Swal.fire({{icon: 'error', title: 'Error fetching expenses', html: {json.dumps(msg)} }});</script></div>"
        return oob, 200


@expenses_bp.route('/expense/<string:slug>')
@login_required
@confirmed_required
def expense_details(slug):
    context = ExpenseService.get_expense_details_context(slug)
    
    return render_template('budget/expense/expenses_details.html', **context)
                           
@expenses_bp.route('/expense/<string:slug>/transfer', methods=['POST'])
@login_required
@confirmed_required
def transfer_balance(slug):
    source_expense = Expense.query.filter_by(slug=slug).first_or_404()
    form = TransferForm(source_expense=source_expense)
    
    other_expenses = ExpenseService.get_transfer_targets(source_expense)
    form.target_expense_id.choices = [(e.id, e.description) for e in other_expenses]
    return ExpenseService.handle_transfer(source_expense, form)

@expenses_bp.route('/expense/<string:slug>/rename', methods=['POST'])
def rename(slug):
    expense = Expense.query.filter_by(slug=slug).first_or_404()
    expense.description = request.form.get('new_name')
    db.session.commit()
    return expense.description

@expenses_bp.route('/expense/<string:slug>/toggle_closed', methods=['POST'])
def toggle_expense_closed(slug):
    expense = Expense.query.filter_by(slug=slug, user_id=current_user.id).first_or_404()
    expense.is_closed = not expense.is_closed 
    db.session.commit()
    
    budget = expense.budget
    page = request.args.get('page', 1, type=int)
    per_page = 10

    pagination = ExpenseService.paginate_expenses(budget.id, page=page, per_page=per_page)

    return render_template("budget/expense/expenses_table.html", 
                           expenses=pagination.items,  
                           budget=budget,
                           current_page=page,          
                           total_pages=pagination.pages, 
                           categories=Category.query.all())

@expenses_bp.route('/expense/<string:slug>/update_category', methods=['POST'])
def update_category(slug):
    expense = Expense.query.filter_by(slug=slug).first_or_404()
    new_category_id = request.form.get('category_id')
    
    if new_category_id:
        expense.category_id = new_category_id
        db.session.commit()
    
    return expense.category.name