from odoo import http
from odoo.http import request


_STOK_TIPES = ['stok_masuk', 'stok_keluar', 'titik_ditambah']
_ORDER_TIPES = ['order_dibuat', 'order_selesai', 'order_dibatalkan']

_TIPE_LABELS = {
    'stok_masuk':     ('Masuk', 'badge-success'),
    'stok_keluar':    ('Keluar', 'badge-blue'),
    'titik_ditambah': ('Titik Baru', 'badge-grey'),
    'order_dibuat':   ('Order Dibuat', 'badge-blue'),
    'order_selesai':  ('Order Selesai', 'badge-success'),
    'order_dibatalkan': ('Dibatalkan', 'badge-danger'),
    'user_dibuat':    ('Pengguna Baru', 'badge-grey'),
}


class SmiActivityController(http.Controller):

    @http.route('/smi/activity', type='http', auth='user', website=False)
    def activity_page(self, tab='stok', search='', tipe='', **kwargs):
        user = request.env.user
        is_staf = user.has_group('inventory_smi.group_staf_produksi') and \
                  not user.has_group('inventory_smi.group_kepala_produksi') and \
                  not user.has_group('inventory_smi.group_admin')

        if tab == 'order':
            tipe_filter = _ORDER_TIPES
        else:
            tab = 'stok'
            tipe_filter = _STOK_TIPES

        domain = [('tipe', 'in', tipe_filter)]

        if is_staf:
            domain.append(('user_id', '=', user.id))

        if search:
            domain.append(('user_id.name', 'ilike', search))

        if tipe and tipe in tipe_filter:
            domain.append(('tipe', '=', tipe))

        logs = request.env['smi.activity.log'].search(domain, order='tanggal desc, id desc')

        values = {
            'logs': logs,
            'tab': tab,
            'search': search,
            'tipe_filter': tipe,
            'tipe_labels': _TIPE_LABELS,
            'is_staf': is_staf,
            'is_direktur': user.has_group('inventory_smi.group_direktur'),
            'is_kepala': user.has_group('inventory_smi.group_kepala_produksi'),
            'is_admin': user.has_group('inventory_smi.group_admin'),
            'current_user': user,
            'active_menu': 'activity',
            'page_title': 'Aktivitas',
        }
        return request.render('inventory_smi.activity_page', values)
