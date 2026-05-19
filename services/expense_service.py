from flask import render_template
from sqlalchemy.orm import joinedload
from models import Expense, Budget, Category, BudgetCategoryLimit
from utils.extensions import db

class ExpenseService:
    @staticmethod
    def paginate_expenses(budget_id, page=1, per_page=10, category_id=None):
        query = Expense.query.filter_by(budget_id=budget_id)

        if category_id and str(category_id).isdigit():
            query = query.filter(Expense.category_id == int(category_id))

        return query.order_by(Expense.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def render_budget_state(budget_id, page=1):
        budget = Budget.query.get_or_404(budget_id)
        categories = Category.get_all_cached()
        
        pagination = ExpenseService.paginate_expenses(budget_id, page=page, per_page=10)
        expenses = pagination.items 
        
        category_spent_totals = budget.get_category_financials()
        limits_list = BudgetCategoryLimit.query.options(joinedload(BudgetCategoryLimit.category))\
            .filter_by(budget_id=budget_id).all()
        
        category_limits = {l.category_id: l for l in limits_list}
        has_items = len(expenses) > 0

        expenses_html = render_template(
            "budget/expenses_table.html",
            expenses=expenses,
            total_pages=pagination.pages, 
            current_page=page,
            budget=budget,
            categories=categories
        )

        limits_html = render_template(
            "budget/category_limits_table.html",
            categories=categories,
            category_limits=category_limits,
            category_spent_totals=category_spent_totals,
            budget=budget
        )

        buttons_html = render_template(
            "budget/_conditional_buttons.html", 
            expenses=has_items, 
            budget=budget
        )

        pdf_oob = render_template('budget/pdf/pdf.html', budget=budget) if has_items else ""

        return (
            f"{expenses_html}"
            f"<div id=\"category-limits-table\" hx-swap-oob=\"true\">{limits_html}</div>"
            f"<div id=\"conditional-buttons\" hx-swap-oob=\"true\">{buttons_html}</div>"
            f"<div id=\"pdf-section-wrapper\" hx-swap-oob=\"true\">{pdf_oob}</div>"
        )
    
    @staticmethod
    def handle_transfer(source_expense, form):
        if form.validate_on_submit():
            try:
                amount_to_move = form.amount.data 
                target_expense = Expense.query.get(form.target_expense_id.data)

                source_expense.amount = float(source_expense.amount) - amount_to_move
                target_expense.amount = float(target_expense.amount) + amount_to_move

                db.session.commit()
                
                return render_template('budget/transfer_result.html', 
                                     result=f"Moved {amount_to_move} successfully.")
            
            except Exception as e:
                db.session.rollback()
                print(f"DB Error: {e}") 
                return render_template('budget/transfer_result.html', 
                                     error="Database update failed.")
        
        error_msg = list(form.errors.values())[0][0] if form.errors else "Invalid submission."
        return render_template('budget/transfer_result.html', error=error_msg)

    @staticmethod
    def get_transfer_targets(source_expense):
        return Expense.query.filter(
            Expense.budget_id == source_expense.budget_id, 
            Expense.id != source_expense.id,
            Expense.is_closed == False
        ).all()
    
    @staticmethod
    def get_expense_details_context(slug):
        expense = Expense.query.filter_by(slug=slug).first_or_404()
        
        budget = Budget.query.get(expense.budget_id)
        all_categories = Category.query.all()
        other_expenses = Expense.query.filter(
            Expense.budget_id == expense.budget_id, 
            Expense.id != expense.id
        ).all()

        
        total_budget = float(budget.amount) if budget else 0
        expense_amount = float(expense.amount)
        
        if total_budget > 0:
            expense_percentage = (expense_amount / total_budget) * 100
            remaining_percentage = 100 - expense_percentage
            remaining_amount = total_budget - expense_amount
        else:
            expense_percentage = 0
            remaining_percentage = 100
            remaining_amount = 0

        return {
            "expense": expense,
            "other_expenses": other_expenses,
            "budget": budget,
            "expense_percentage": expense_percentage,
            "remaining_percentage": remaining_percentage,
            "remaining_amount": remaining_amount,
            "categories": all_categories
        }