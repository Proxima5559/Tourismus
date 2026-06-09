from flask import render_template, make_response
from sqlalchemy.orm import joinedload
from loguru import logger
from utils.extensions import db
from models import Budget, Category, BudgetCategoryLimit

class CategoryService:

    @staticmethod
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

    @classmethod
    def set_or_update_limit(cls, budget, form, user_id):
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
                        user_id=user_id,
                        budget_id=budget.id,
                        category_id=form.category_id.data,
                        limit_amount=form.limit_amount.data
                    )
                    db.session.add(limit)

                db.session.commit()

                context = cls.build_budget_category_context(budget)
                return render_template(
                    'budget/category/category_limits_table.html', 
                    budget=budget,
                    **context
                ), 200

            except Exception as e:
                db.session.rollback()
                logger.error(f"Database error setting limit: {e}")
                error_msg = "Database error occurred."
        else:
            error_msg = list(form.errors.values())[0][0] if form.errors else "Invalid input"

        response = make_response(render_template('budget/expense/expense_result.html', error=error_msg))
        response.headers['HX-Retarget'] = '#error-container'
        return response, 200

    @classmethod
    def delete_limit_and_get_context(cls, budget, category_id):
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

        context = cls.build_budget_category_context(budget)
        return render_template(
            'budget/category/category_limits_table.html',
            budget=budget,
            budget_id=budget.id,
            **context
        ), 200