import math
from datetime import datetime, timedelta
from itertools import accumulate
from sqlalchemy import func
from loguru import logger
from utils.extensions import db
from models import Budget, Expense, Category

class AnalyticsService:

    @staticmethod
    def _calculate_budget_projections(budget, daily_amounts):
        today = datetime.now().date()
        
        if daily_amounts:
            days_elapsed = (today - budget.start_date).days
            days_elapsed = max(1, days_elapsed)
            avg_daily_spend = budget.spent_amount / days_elapsed
        else:
            avg_daily_spend = 0

        remaining_balance = max(0, budget.amount - budget.spent_amount)
        
        if avg_daily_spend > 0:
            days_remaining_until_zero = remaining_balance / avg_daily_spend
            run_out_date = today + timedelta(days=math.floor(days_remaining_until_zero))
        else:
            run_out_date = budget.end_date

        is_over_pacing = run_out_date < budget.end_date
        
        return {
            "avg_daily_spend": round(avg_daily_spend, 2),
            "run_out_date": run_out_date,
            "is_over_pacing": is_over_pacing,
            "days_left_budget": (budget.end_date - today).days
        }

    @classmethod
    def get_dashboard_context(cls, slug):
        budget = Budget.query.filter_by(slug=slug).first_or_404()

        category_data = (
            db.session.query(Category.name, func.sum(Expense.amount))
            .join(Expense, Expense.category_id == Category.id)
            .filter(Expense.budget_id == budget.id)
            .group_by(Category.name)
            .all()
        )
        logger.debug(f"DEBUG: Category Data found: {category_data}")

        if category_data:
            labels, values = map(list, zip(*category_data))
            values = [float(v or 0.0) for v in values]
        else:
            labels, values = [], []

        date_expr = func.date(Expense.created_at)
        time_data = (
            db.session.query(
                func.date(Expense.created_at).label('date'), 
                func.sum(Expense.amount).label('total')
            )
            .filter(Expense.budget_id == budget.id)
            .group_by(date_expr)
            .order_by(date_expr)
            .all()
        )

        dates = [
            d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d)
            for d, _ in time_data
        ]
        daily_amounts = [float(t or 0) for _, t in time_data]
        
        projections = cls._calculate_budget_projections(budget, daily_amounts)
        cumulative_amounts = list(accumulate(daily_amounts))
        limit_line = [float(budget.amount)] * len(dates)

        return {
            "budget": budget,
            "labels": labels,
            "values": values,
            "dates": dates,
            "daily_amounts": daily_amounts,
            "total_spent": budget.spent_amount,
            "cumulative_amounts": cumulative_amounts,
            "limit_line": limit_line,
            **projections
        }