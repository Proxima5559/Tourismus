from flask import Blueprint, render_template, request
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload
from datetime import date, datetime, timedelta
import calendar
from utils.extensions import db
from utils.decorators import confirmed_required
from models import DailyPlan, Expense 
from collections import defaultdict


history_bp = Blueprint('history', __name__, url_prefix='/history')

@history_bp.route('/calendar')
@login_required
@confirmed_required
def view_calendar():
    year = int(request.args.get('year', datetime.now().year))
    month = int(request.args.get('month', datetime.now().month))
    
    start_date = date(year, month, 1)
    end_date = date(year + (month == 12), (month % 12) + 1, 1)
    
    plans = (
        DailyPlan.query
        .filter(
            DailyPlan.user_id == current_user.id,
            DailyPlan.date >= start_date,
            DailyPlan.date < end_date
        )
        .options(joinedload(DailyPlan.items))
        .all()
    )


    expenses = (
        Expense.query
        .filter(
            Expense.user_id == current_user.id,
            Expense.created_at >= start_date,
            Expense.created_at < end_date
        )
        .options(
            joinedload(Expense.budget),
            joinedload(Expense.category)
        )
        .all()
    )

    day_data = defaultdict(lambda: {
        'expenses': [],
        'total_cash': 0,
        'plan': None
    })

    
    for e in expenses:
        day = e.created_at.day
        day_data[day]['expenses'].append(e)
        day_data[day]['total_cash'] += e.amount

    for p in plans:
        day = p.date.day

        total_tasks = len(p.items)
        done_tasks = sum(1 for i in p.items if i.is_completed)

        day_data[day]['plan'] = {
            'slug': p.slug,
            'stats': f"{done_tasks}/{total_tasks}",
            'all_done': total_tasks > 0 and done_tasks == total_tasks
        }

    cal = calendar.Calendar(firstweekday=6)
    month_days = cal.monthdayscalendar(year, month)
    
    context = {
        "month_days": month_days, "year": year, "month": month,
        "month_name": calendar.month_name[month],
        "day_data": day_data,
        "prev_month": month-1 if month > 1 else 12,
        "prev_year": year if month > 1 else year-1,
        "next_month": month+1 if month < 12 else 1,
        "next_year": year if month < 12 else year+1,
        "today": datetime.now().date()
    }
    is_htmx = request.headers.get('HX-Request')
    is_boosted = request.headers.get('HX-Boosted')

    if is_htmx and not is_boosted:
        return render_template('history/calendar_grid.html', **context)
    return render_template('history/index.html', **context)

@history_bp.route('/day-details/<int:year>/<int:month>/<int:day>')
@login_required
@confirmed_required
def day_details(year, month, day):
    target_date = date(year, month, day)
    
    start = datetime(year, month, day)
    end = start + timedelta(days=1)
    
    plan = (
        DailyPlan.query
        .filter(
            DailyPlan.user_id == current_user.id,
            DailyPlan.date == target_date
        )
        .options(joinedload(DailyPlan.items))
        .first()
    )

    expenses = (
        Expense.query
        .filter(
            Expense.user_id == current_user.id,
            Expense.created_at >= start,
            Expense.created_at < end
        )
        .options(
            joinedload(Expense.budget),
            joinedload(Expense.category)
        )
        .all()
    )
    
    return render_template('history/_day_details_partial.html', 
                           expenses=expenses, 
                           plan=plan, 
                           target_date=target_date)