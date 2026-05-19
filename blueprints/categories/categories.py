from flask import Blueprint, make_response, request, redirect, url_for, render_template
from flask_login import current_user, login_required
from models import BudgetCategoryLimit, Budget, Category
from utils.decorators import confirmed_required
from utils.extensions import db
from utils.forms import CategoryLimitForm
from sqlalchemy import func
from loguru import logger
from sqlalchemy.orm import joinedload

category_bp = Blueprint('category', __name__)

def build_budget_category_context(budget):
    categories = Category.get_all_cached()
    category_spent_totals = budget.get_category_financials()
    limits = BudgetCategoryLimit.query.options(
        joinedload(BudgetCategoryLimit.category)
    ).filter_by(budget_id=budget.id).all()
    
    
    return {
        "categories": categories,
        "category_spent_totals": category_spent_totals,
        "category_limits": {l.category_id: l for l in limits}
    }
@category_bp.route('/budget/<string:slug>/set-limit', methods=['POST'])
@login_required
@confirmed_required
def set_category_limit(slug):
    budget = Budget.query.filter_by(slug=slug).first_or_404()
    
    if budget.user_id != current_user.id:
        return "Unauthorized", 403

    form = CategoryLimitForm(budget_id=budget.id)
    form.category_id.choices = [(c.id, c.name) for c in Category.get_all_cached()]
    
    if form.validate_on_submit():
        try:
            limit = BudgetCategoryLimit.query.filter_by(
                budget_id=budget.id,
                category_id=form.category_id.data
            ).first()

            if limit:
                limit.limit_amount = form.limit_amount.data
            else:
                limit = BudgetCategoryLimit(
                    user_id=current_user.id,
                    budget_id=budget.id,
                    category_id=form.category_id.data,
                    limit_amount=form.limit_amount.data
                )
                db.session.add(limit)

            db.session.commit()

            context = build_budget_category_context(budget)
            return render_template(
                'budget/category_limits_table.html', 
                budget=budget,
                **context
            )

        except Exception as e:
            db.session.rollback()
            error_msg = "Database error occurred."
    else:
        error_msg = list(form.errors.values())[0][0] if form.errors else "Invalid input"

    response = make_response(render_template('budget/expense_result.html', error=error_msg))
    response.headers['HX-Retarget'] = '#error-container'
    return response

@category_bp.route('/budget/<string:slug>/category/<int:category_id>', methods=['DELETE'])
@login_required
@confirmed_required
def delete_category_limit(slug, category_id):
    budget = Budget.query.filter_by(slug=slug).first_or_404()
    
    if budget.user_id != current_user.id:
        return "Unauthorized", 403

    try:
        category_limit = BudgetCategoryLimit.query.filter_by(
            budget_id=budget.id,
            category_id=category_id
        ).first()

        if category_limit:
            db.session.delete(category_limit)
            db.session.commit()
            db.session.refresh(budget)
       
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Delete failed: {e}")
        return "Delete failed", 500

    context = build_budget_category_context(budget)

    return render_template('budget/category_limits_table.html',
                           budget=budget,
                           budget_id=budget.id,
                           **context)

