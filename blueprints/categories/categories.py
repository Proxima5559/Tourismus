from flask import Blueprint
from flask_login import current_user, login_required
from models import Budget, Category
from utils.decorators import confirmed_required
from utils.forms import CategoryLimitForm
from services.category_service import CategoryService

category_bp = Blueprint('category', __name__)

@category_bp.route('/budget/<string:slug>/set-limit', methods=['POST'])
@login_required
@confirmed_required
def set_category_limit(slug):
    budget = Budget.query.filter_by(slug=slug).first_or_404()
    
    if budget.user_id != current_user.id:
        return "Unauthorized", 403

    form = CategoryLimitForm(budget_id=budget.id)
    form.category_id.choices = [(c.id, c.name) for c in Category.get_all_cached()]
    
    html_res, status_code = CategoryService.set_or_update_limit(budget, form, current_user.id)
    return html_res, status_code


@category_bp.route('/budget/<string:slug>/category/<int:category_id>', methods=['DELETE'])
@login_required
@confirmed_required
def delete_category_limit(slug, category_id):
    budget = Budget.query.filter_by(slug=slug).first_or_404()
    
    if budget.user_id != current_user.id:
        return "Unauthorized", 403

    html_res, status_code = CategoryService.delete_limit_and_get_context(budget, category_id)
    return html_res, status_code

