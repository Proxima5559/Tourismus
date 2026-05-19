from flask import render_template, request, flash, redirect, url_for

def register_error_handlers(app):
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        error_msg = "Slow down, comrade! Too many requests. Try again in a minute."
        if request.headers.get('HX-Request'):
            return f'<div class="alert alert-danger">{error_msg}</div>', 429
        
        flash(error_msg, "danger")
        return redirect(url_for('auth.login'))

    # # 404 Not Found
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500