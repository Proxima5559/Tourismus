from flask import Blueprint, render_template, request
from flask_login import current_user, login_required
from utils.decorators import confirmed_required
from utils.forms import DailyPlanForm
from utils.extensions import db
from loguru import logger

from models import Budget, DailyPlan, PlanItem

plans_dash_bp = Blueprint('plans_dash', __name__, template_folder='templates')


@plans_dash_bp.route('/plans')
@login_required
@confirmed_required
def index():
    form = DailyPlanForm()
    user_budgets = Budget.query.filter_by(user_id=current_user.id).all()
    form.budget_id.choices = [(b.id, b.name) for b in user_budgets]
    
    plans = DailyPlan.query.filter_by(user_id=current_user.id).order_by(DailyPlan.date.desc()).all()
    plan = plans[0] if plans else None

    page = request.args.get('page', 1, type=int)
    pagination = DailyPlan.get_user_plans_paginated(current_user.id, page)
    return render_template('plans_dash/plans_dash.html', 
                           plans=plans, 
                           plan=plan,
                           form=form, 
                           user_budgets=user_budgets,
                           pagination=pagination,
                           selected_budget_id=None,
                           error_msg=None)


@plans_dash_bp.route('/plan/<string:slug>')
@login_required
@confirmed_required
def plan_detail(slug):
    plan = DailyPlan.query.filter_by(slug=slug, user_id=current_user.id).first_or_404()
    mandatory = [i for i in plan.items if i.is_mandatory]
    secondary = [i for i in plan.items if not i.is_mandatory]
    return render_template('plans_dash/plan_editor.html', plan=plan, mandatory=mandatory, secondary=secondary)

@plans_dash_bp.route('/section/plans', methods=['GET', 'POST'])
@login_required
@confirmed_required
def section_plans():
    form = DailyPlanForm()
    user_budgets = Budget.query.filter_by(user_id=current_user.id).all()
    logger.debug(f"User {current_user.id} budgets: {[b.name for b in user_budgets]}")
    form.budget_id.choices = [(b.id, b.name) for b in user_budgets]


    
    error_msg = None

    if form.validate_on_submit():
            new_plan = DailyPlan(
                user_id=current_user.id,
                budget_id=form.budget_id.data,
                date=form.date.data,
                tag=form.tag.data 
            )
            db.session.add(new_plan)
            db.session.commit()
            form = DailyPlanForm()
            form.budget_id.choices = [(b.id, b.name) for b in user_budgets]

    plans = DailyPlan.query.filter_by(user_id=current_user.id).order_by(DailyPlan.date.desc()).all()
    
    page = request.args.get('page', 1, type=int)

    pagination = DailyPlan.get_user_plans_paginated(current_user.id, page)
    return render_template('plans_dash/_plans_section.html', 
                           plans=plans, 
                           form=form, 
                           user_budgets=user_budgets,
                           pagination=pagination,
                           error_msg=error_msg)



@plans_dash_bp.route('/filter-plans', methods=['GET'])
@login_required
@confirmed_required
def filter_plans():
    budget_id = request.args.get('budget_filter')
    page = request.args.get('page', 1, type=int)
    
    if budget_id and budget_id.isdigit():
        budget_id = int(budget_id)
    else:
        budget_id = None

    pagination = DailyPlan.get_user_plans_paginated(
        user_id=current_user.id, 
        page=page, 
        budget_id=budget_id
    )
    
    return render_template(
        'plans_dash/_plans_list_partial.html', 
        plans=pagination.items,  
        pagination=pagination,    
        selected_budget_id=budget_id 
    )
@plans_dash_bp.route('/plan/<slug>/add-item', methods=['POST'])
@login_required
@confirmed_required
def add_item(slug):
    plan = DailyPlan.query.filter_by(slug=slug).first_or_404()
    description = request.form.get('description')
    is_mandatory = 'is_mandatory' in request.form 

    if not description:
        return "", 400

    try:
        new_item = PlanItem(
            daily_plan_id=plan.id,
            description=description,
            is_mandatory=is_mandatory
        )

        db.session.add(new_item)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding item to plan {plan.id}: {e}")
        return "", 500

    html = render_template(
        'plans_dash/_task_item_partial.html',
        item=new_item
    )

    if new_item.is_mandatory:
        return html, 200, {
            "HX-Retarget": "#mandatory-list",
            "HX-Reswap": "beforeend"
        }
    else:
        return html, 200, {
            "HX-Retarget": "#secondary-list",
            "HX-Reswap": "beforeend"
        }

@plans_dash_bp.route('/item/<int:item_id>/toggle', methods=['POST'])
@login_required
@confirmed_required
def toggle_item(item_id):
    item = PlanItem.query.get_or_404(item_id)
    if item.daily_plan.user_id == current_user.id:
        item.is_completed = not item.is_completed
        db.session.commit()
    return render_template('plans_dash/_task_item_partial.html', item=item)

@plans_dash_bp.route('/plan/<slug>/tag', methods=['POST'])
@login_required
@confirmed_required
def add_tag(slug):
    plan = DailyPlan.query.filter_by(slug=slug).first_or_404()
    new_tag = request.form.get('tag_name', '').strip()
    
    if not new_tag:
        return "", 400
    
    try:
        current_tags = plan.tag.split(',') if plan.tag else []
        if new_tag not in current_tags:
            current_tags.append(new_tag)
            plan.tag = ",".join(current_tags)
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding tag to plan {plan.id}: {e}")
        return "", 500
    
    return render_template('plans_dash/_tags_partial.html', plan=plan)

@plans_dash_bp.route('/plan/<string:slug>/delete', methods=['DELETE'])
@login_required
@confirmed_required
def delete_plan(slug):
    plan = DailyPlan.query.filter_by(slug=slug, user_id=current_user.id).first_or_404()
      
    try:
        db.session.delete(plan)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting plan {plan.id}: {e}")
        return "", 500
 
    return "", 200

@plans_dash_bp.route('/plan/<slug>/tags/clear', methods=['DELETE'])
@login_required
@confirmed_required
def clear_all_tags(slug):
    plan = DailyPlan.query.filter_by(slug=slug, user_id=current_user.id).first_or_404()
    
    try:
        plan.tag = None
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error clearing tags for plan {plan.id}: {e}")
        return "", 500

    return render_template('plans_dash/_tags_partial.html', plan=plan)

@plans_dash_bp.route('/item/<int:item_id>/delete', methods=['DELETE'])
@login_required
@confirmed_required
def delete_item(item_id):
    item = PlanItem.query.get_or_404(item_id)

    try:
        db.session.delete(item)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting item {item.id}: {e}")
        return "", 500

    return "", 200

@plans_dash_bp.route('/plans/delete-all', methods=['DELETE'])
@login_required
@confirmed_required
def delete_all_plans():
    try:
        DailyPlan.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting all plans for user {current_user.id}: {e}")
        return "", 500

    return render_template(
        'plans_dash/_plans_list_partial.html',
        plans=[],
        pagination=None,
        selected_budget_id=None
    )