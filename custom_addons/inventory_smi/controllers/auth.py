from odoo import http
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

        # Pre-flight lockout check (avoids leaking timing on hash compare)
        if login_val:
            user = request.env['res.users'].sudo().search(
                [('login', '=', login_val)], limit=1
            )
            if user and user._smi_is_locked():
                values['error'] = 'locked'
                return request.render('inventory_smi.login_page', values)

        # Delegate to Odoo's standard session authenticate
        uid = request.session.authenticate(request.db, login_val, password_val)

        if uid:
            # Success — go to dashboard
            request.session.get_context()
            return request.redirect('/smi/dashboard')

        # Failure — show error
        values['error'] = 'credentials'
        values['login'] = login_val
        return request.render('inventory_smi.login_page', values)
