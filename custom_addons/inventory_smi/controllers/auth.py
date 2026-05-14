from odoo import http
from odoo.exceptions import AccessDenied
from odoo.http import request
from odoo.addons.web.controllers.home import Home


class SmiAuthController(Home):

    @http.route('/web/login', type='http', auth='none', methods=['GET', 'POST'], sitemap=False)
    def web_login(self, redirect=None, **kw):
        """Override login to:
        1. Render Indonesian custom template.
        2. Show lockout error before attempting auth.
        3. Redirect to /smi/dashboard on success.
        """
        values = dict(kw)
        values['redirect'] = redirect or '/smi/dashboard'

        if request.httprequest.method == 'GET':
            # Clear any previous error on fresh visit
            return request.render('inventory_smi.login_page', values)

        # POST — attempt login
        login_val = request.params.get('login', '').strip()
        password_val = request.params.get('password', '')

        # Look up user once (used for lockout checks and failure tracking)
        user = request.env['res.users'].sudo().search(
            [('login', '=', login_val)], limit=1
        ) if login_val else None

        # Pre-flight lockout check — bail before hitting authenticate()
        if user and user._smi_is_locked():
            values['error'] = 'locked'
            return request.render('inventory_smi.login_page', values)

        # Delegate to Odoo's standard session authenticate
        try:
            uid = request.session.authenticate(request.db, login_val, password_val)
        except AccessDenied:
            uid = None

        if uid:
            # Success — reset fail counter and go to dashboard
            if user:
                user._smi_reset_login_fail()
            return request.redirect('/smi/dashboard')

        # Failure — track it here so the write is committed with this request's transaction
        if user:
            user._smi_record_failed_login()
            values['error'] = 'locked' if user._smi_is_locked() else 'credentials'
        else:
            values['error'] = 'credentials'

        values['login'] = login_val
        return request.render('inventory_smi.login_page', values)
