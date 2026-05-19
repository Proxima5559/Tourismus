from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from flask import redirect, url_for, flash
from utils.extensions import cache


class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, 'is_admin', False)

    def inaccessible_callback(self, name, **kwargs):
        flash("Admin access required.", "danger")
        return redirect(url_for('auth.login')) 

class CategoryAdminView(SecureModelView):
    def after_model_change(self, form, model, is_created):
        cache.delete('all_categories_list')

    def after_model_delete(self, model):
        cache.delete('all_categories_list')

class UserAdminView(SecureModelView):
    column_exclude_list = ['password_hash']
    form_excluded_columns = ['password_hash', 'slug']
    column_searchable_list = ['username', 'email']