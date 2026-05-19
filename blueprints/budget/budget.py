from flask import Blueprint, render_template, request, redirect, url_for, make_response
from loguru import logger
from models import  Budget,  Expense, Category
from services.pdf_service import PDFService
from utils.extensions import db
from services.budget_service import BudgetService
from utils.decorators import confirmed_required
from utils.forms import BudgetForm
from flask import flash
from flask_login import current_user, login_required



budget_bp = Blueprint('budget', __name__, url_prefix='/budget')



@budget_bp.route('/create', methods=['GET'])
@login_required
@confirmed_required
def create_budget_page():
    form = BudgetForm()
    return render_template('budget/create_budget.html', form=form)

@budget_bp.route('/', methods=['GET', 'POST'])
@login_required
@confirmed_required
def budget_dashboard():
    user = current_user 
    budget = user.budget

    form = BudgetForm()
    error = None

    
    if form.validate_on_submit():
        budget = Budget(
            user_id=user.id, 
            amount=form.amount.data, 
            name=form.name.data,
            currency=form.currency.data.strip(),
            start_date=form.start_date.data, 
            end_date=form.end_date.data,
        )
        db.session.add(budget)
        db.session.commit()

     
        if request.headers.get('HX-Request'):
            return redirect(url_for('budget.budget_dashboard'))

    
    if form.is_submitted() and not form.validate():
        first_error_field = list(form.errors.keys())[0]
        error_msg = form.errors[first_error_field][0]
        flash(error_msg, "error")
        return render_template('budget/create_budget.html', form=form)
        
    page = request.args.get('page', 1, type=int)
    per_page = 6
    
    pagination = BudgetService.get_user_budgets_paginated(user.id, page=page, per_page=per_page)
        
    budgets = pagination.items
    return render_template('budget/budget_dashboard.html', budgets=budgets, form=form, error=error, pagination=pagination, current_page=page)

@budget_bp.route('/<string:slug>/details')
@login_required
@confirmed_required
def view_budget_details(slug):
    try:
        page = request.args.get('page', 1, type=int)
        
        context = BudgetService.get_budget_details_context(
            slug=slug, 
            user_id=current_user.id, 
            page=page
        )
        
        return render_template('budget/budget_details.html', **context)
                             
    except Exception as e:
        logger.error(f"ERROR in view_budget_details: {e}")
        return f"Error: {e}", 500

@budget_bp.route('/<string:slug>', methods=['DELETE'])
@login_required
@confirmed_required
def delete_budget(slug):
    budget = Budget.get_by_slug_or_404(slug, current_user.id)
    
    try:
        db.session.delete(budget)
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Delete failed: {e}")
        return "Internal Server Error", 500
    
    if request.headers.get('HX-Request'):
        return "", {"HX-Redirect": url_for('budget.budget_dashboard')}

    budgets = Budget.query.filter_by(user_id=current_user.id).all()
    return render_template('budget/budget_innerPart.html', budgets=budgets, form=BudgetForm())


@budget_bp.route('/delete-all', methods=['DELETE'])
@login_required
@confirmed_required
def delete_all_budgets():
    user_id = current_user.id
    try:
        Budget.query.filter(Budget.user_id == user_id).delete(synchronize_session=False)
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to delete all budgets: {e}")
        return "Failed to clear data", 500

    return render_template('/budget/budget_innerPart.html', budgets=[], form=BudgetForm(), error=None)


@budget_bp.route('/<string:slug>/edit', methods=['GET'])
@login_required
@confirmed_required
def edit_budget_page(slug):
    budget = Budget.get_by_slug_or_404(slug, current_user.id)
    return render_template('budget/edit_budget_page.html', budget=budget, form=BudgetForm(obj=budget), error=None)


@budget_bp.route('/update/<string:slug>', methods=['GET', 'POST'])
@login_required
@confirmed_required
def update_budget(slug):
    budget = Budget.get_by_slug_or_404(slug, current_user.id)
    form = BudgetForm(obj=budget)

    if form.validate_on_submit():
        success, message, category = BudgetService.update_budget_logic(budget, form)
        flash(message, category)
        
        if success:
            return redirect(url_for('budget.budget_dashboard'))

    if form.is_submitted() and not form.validate():
        first_error_field = list(form.errors.keys())[0]
        error_msg = form.errors[first_error_field][0]
        flash(f"{first_error_field.capitalize()}: {error_msg}", "error")

    return render_template(
        "budget/edit_budget_page.html",
        budget=budget,
        form=form
    )

@budget_bp.route('/<string:slug>/download-pdf')
@login_required
@confirmed_required
def download_budget_pdf(slug):
    budget = Budget.get_by_slug_or_404(slug, current_user.id)
    expenses = Expense.query.filter_by(budget_id=budget.id).all()
    
    used_category_ids = set(e.category_id for e in expenses)
    categories = Category.query.filter(Category.id.in_(used_category_ids)).all()
    category_names = {cat.id: cat.name for cat in categories}

    pdf_buffer = PDFService.generate_budget_report(budget, expenses, category_names)

    response = make_response(pdf_buffer.read())
    response.headers.set('Content-Type', 'application/pdf')
    filename = f'reconciliation_report_{budget.id}.pdf'
    response.headers.set('Content-Disposition', 'attachment', filename=filename)
    return response


@budget_bp.route('/budget/<string:slug>/view_actuals')
@login_required
@confirmed_required
def view_actuals(slug):
    budget = Budget.get_by_slug_or_404(slug, current_user.id)

    page = request.args.get('page', 1, type=int)
    per_page = 10  

    pagination = BudgetService.get_actuals_paginated(budget.id, page=page, per_page=per_page)
    expenses = pagination.items
    
    total_planned = sum(e.amount for e in expenses)
    total_actual = sum(e.actual_amount or 0 for e in expenses)
    remaining = total_planned - total_actual
    
    percent = (total_actual / total_planned * 100) if total_planned > 0 else 0
    context = {
        'budget': budget, 
        'expenses': expenses,
        'pagination': pagination,
        'total_planned': total_planned,
        'total_actual': total_actual,
        'remaining': remaining,
        'percent': round(percent, 1)
    }

    if request.headers.get('HX-Request'):
        return render_template('budget/actuals_table_fragment.html', **context)

    return render_template('budget/view_actuals.html', **context)

@budget_bp.route('/expense/set_actual/<string:slug>', methods=['POST'])
@login_required
@confirmed_required
def set_expense_actual(slug):
    expense = Expense.query.filter_by(slug=slug).first_or_404()
    budget = expense.budget
    
    try:
        val = request.form.get('actual_amount', 0)
        expense.actual_amount = float(val) if val else 0.0
        db.session.commit()

        if request.headers.get('HX-Request'):
            row_html = render_template('budget/actual_row.html', expense=expense, budget=expense.budget)
            response = make_response(row_html)
            response.headers['HX-Trigger'] = 'refreshStats'
            return response

    except Exception as e:
        db.session.rollback()
        return "Error saving amount", 400
    
@budget_bp.route('/budget/stats/<string:slug>')
@login_required
@confirmed_required
def get_stats(slug):
    budget = Budget.get_by_slug_or_404(slug, current_user.id)
    expenses = Expense.query.filter_by(budget_id=budget.id).all()
    
    total_planned = sum(e.amount for e in expenses)
    total_actual = sum(e.actual_amount or 0 for e in expenses)
    remaining = total_planned - total_actual
    percent = round((total_actual / total_planned * 100), 1) if total_planned > 0 else 0

    return render_template('budget/_stats_partial.html', 
                           budget=budget, 
                           total_planned=total_planned,
                           total_actual=total_actual,
                           remaining=remaining,
                           percent=percent)


 # all_expenses = Expense.query.filter_by(budget_id=budget.id).all()
        # total_planned = sum(e.amount for e in all_expenses)
        # total_actual = sum(e.actual_amount or 0 for e in all_expenses)
        # remaining = total_planned - total_actual
        # percent = round((total_actual / total_planned * 100), 1) if total_planned > 0 else 0
