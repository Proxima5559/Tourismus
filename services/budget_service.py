from models import Budget, Expense, Category, BudgetCategoryLimit, generate_unique_slug
from utils.extensions import db
from loguru import logger
from sqlalchemy import func

class BudgetService:
    
    @staticmethod
    def get_user_budgets_paginated(user_id, page=1, per_page=6):
      
        return Budget.query.filter_by(user_id=user_id)\
            .order_by(Budget.start_date.asc())\
            .paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def get_budget_expenses_paginated(budget_id, page=1, per_page=10):
       
        return Expense.query.filter_by(budget_id=budget_id)\
            .order_by(Expense.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def get_actuals_paginated(budget_id, page=1, per_page=10):
       
        return Expense.query.filter_by(budget_id=budget_id)\
            .order_by(Expense.id.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
    @staticmethod
    def get_budget_details_context(slug, user_id, page=1, per_page=10):
       
        budget = Budget.get_by_slug_or_404(slug, user_id)
        
        pagination = Expense.query.filter_by(budget_id=budget.id)\
            .order_by(Expense.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        categories = Category.get_all_cached()
        days_remaining = budget.days_remaining
        
        total_spent_result = db.session.query(func.sum(Expense.amount)).filter_by(budget_id=budget.id).first()
        total_spent = total_spent_result[0] if total_spent_result and total_spent_result[0] else 0

        category_spent_totals = dict(
            db.session.query(
                Expense.category_id,
                func.sum(Expense.amount)
            )
            .filter(Expense.budget_id == budget.id)
            .group_by(Expense.category_id)
            .all()
        )

        category_limits = {
            l.category_id: l
            for l in BudgetCategoryLimit.query.filter_by(budget_id=budget.id).all()
        }

        return {
            "budget": budget,
            "expenses": pagination.items,
            "categories": categories,
            "total_spent": total_spent,
            "category_limits": category_limits,
            "category_spent_totals": category_spent_totals,
            "days_remaining": days_remaining,
            "current_page": page,
            "total_pages": pagination.pages,
            "pagination": pagination 
        }
    @staticmethod
    def update_budget_logic(budget, form):
        
        try:
            total_expenses = db.session.query(func.sum(Expense.amount)).filter_by(budget_id=budget.id).scalar() or 0.0
            new_amount = float(form.amount.data)

            if new_amount < total_expenses:
                return False, f"Budget cannot be lower than existing expenses ({total_expenses:,.2f} {budget.currency})", "error"

            new_name = form.name.data
            if budget.name != new_name:
                budget.name = new_name
                budget.slug = generate_unique_slug(Budget, new_name)

            budget.amount = new_amount
            budget.currency = str(form.currency.data or "").strip().upper()
            budget.start_date = form.start_date.data
            budget.end_date = form.end_date.data

            db.session.commit()
            return True, "Budget updated successfully!", "success"

        except Exception as e:
            db.session.rollback()
            logger.error(f"Update failed for budget {budget.slug}: {e}")
            return False, "A database error occurred. Please try again.", "error"