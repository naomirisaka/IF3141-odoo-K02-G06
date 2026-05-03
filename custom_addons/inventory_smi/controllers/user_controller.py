from odoo import http
from odoo.http import request


class SmiUserController(http.Controller):

    @http.route('/smi/pengguna', type='http', auth='user', website=False)
    def pengguna_page(self, search='', **kwargs):
        user = request.env.user
        if not user.has_group('inventory_smi.group_admin'):
            return request.redirect('/smi/dashboard')

        domain = [('share', '=', False), ('active', '=', True)]
        if search:
            domain.append(('name', 'ilike', search))

        users = request.env['res.users'].search(domain, order='name asc')

        _ROLE_MAP = [
            ('inventory_smi.group_admin', 'Admin'),
            ('inventory_smi.group_kepala_produksi', 'Kepala Produksi'),
            ('inventory_smi.group_staf_produksi', 'Staf Produksi'),
            ('inventory_smi.group_direktur', 'Direktur'),
        ]

        def get_role(u):
            for xml_id, label in _ROLE_MAP:
                try:
                    if u.has_group(xml_id):
                        return label
                except Exception:
                    pass
            return '-'

        users_data = [{'user': u, 'role': get_role(u)} for u in users]

        values = {
            'users_data': users_data,
            'search': search,
            'is_direktur': user.has_group('inventory_smi.group_direktur'),
            'is_kepala': user.has_group('inventory_smi.group_kepala_produksi'),
            'is_admin': user.has_group('inventory_smi.group_admin'),
            'current_user': user,
            'active_menu': 'pengguna',
            'page_title': 'Manajemen Pengguna',
        }
        return request.render('inventory_smi.pengguna_page', values)
