from odoo import http
from odoo.http import request


class SmiMaterialController(http.Controller):

    @http.route('/smi/material/kelola-stok-minimum', type='http', auth='user', website=False)
    def manage_minimum_stock(self, **kwargs):
        """Page for kepala produksi to manage stok_minimum values."""
        user = request.env.user
        
        if not (user.has_group('inventory_smi.group_kepala_produksi') or user.has_group('inventory_smi.group_admin')):
            return request.redirect('/web')

        materials = request.env['smi.material'].search([('active', '=', True)], order='name')
        
        values = {
            'materials': materials,
            'is_direktur': user.has_group('inventory_smi.group_direktur'),
            'is_kepala': user.has_group('inventory_smi.group_kepala_produksi'),
            'is_admin': user.has_group('inventory_smi.group_admin'),
            'current_user': user,
            'active_menu': 'material_stok_min',
        }
        return request.render('inventory_smi.material_stok_minimum_page', values)

    @http.route('/smi/api/material/<int:material_id>/stok-minimum', type='http', auth='user', methods=['POST'], csrf=False)
    def update_minimum_stock(self, material_id, **kwargs):
        user = request.env.user
        
        if not (user.has_group('inventory_smi.group_kepala_produksi') or user.has_group('inventory_smi.group_admin')):
            return request.not_found()

        material = request.env['smi.material'].browse(material_id)
        if not material.exists():
            return request.not_found()

        try:
            stok_minimum = float(kwargs.get('stok_minimum', 0))
            if stok_minimum < 0:
                stok_minimum = 0
            material.write({'stok_minimum': stok_minimum})
            return request.make_response('{"success": true}', [('Content-Type', 'application/json')])
        except Exception as e:
            return request.make_response('{"error": "%s"}' % str(e), [('Content-Type', 'application/json')])
