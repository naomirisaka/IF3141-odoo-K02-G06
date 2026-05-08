import json

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, ValidationError


class SmiStockController(http.Controller):

    # ------------------------------------------------------------------
    # Stock list
    # ------------------------------------------------------------------

    @http.route('/smi/stok', type='http', auth='user', website=False)
    def stock_list(self, search='', sort='name', **kwargs):
        user = request.env.user
        domain = [('active', '=', True)]
        if search:
            domain.append(('name', 'ilike', search))

        order_map = {
            'name': 'name asc',
            'stok_asc': 'total_stok asc',
            'stok_desc': 'total_stok desc',
        }
        order = order_map.get(sort, 'name asc')
        materials = request.env['smi.material'].search(domain, order=order)

        values = {
            'materials': materials,
            'search': search,
            'sort': sort,
            'is_direktur': user.has_group('inventory_smi.group_direktur'),
            'is_kepala': user.has_group('inventory_smi.group_kepala_produksi'),
            'is_admin': user.has_group('inventory_smi.group_admin'),
            'current_user': user,
            'active_menu': 'stok',
        }
        return request.render('inventory_smi.stock_list_page', values)

    # ------------------------------------------------------------------
    # Add stock form (GET + POST)
    # ------------------------------------------------------------------

    @http.route('/smi/stok/tambah', type='http', auth='user', website=False, methods=['GET', 'POST'])
    def stock_add(self, **post):
        user = request.env.user

        if request.httprequest.method == 'POST':
            try:
                material_id = int(post.get('material_id', 0))
                inventory_point_id = int(post.get('inventory_point_id', 0))
                jumlah_awal = float(post.get('jumlah_awal', 0))
                tanggal_masuk = post.get('tanggal_masuk') or False
                catatan = post.get('catatan', '')

                vals = {
                    'material_id': material_id,
                    'inventory_point_id': inventory_point_id,
                    'jumlah_awal': jumlah_awal,
                    'catatan': catatan,
                }
                if tanggal_masuk:
                    vals['tanggal_masuk'] = tanggal_masuk

                request.env['smi.stock_entry'].create(vals)
                return request.redirect('/smi/stok')
            except (ValidationError, Exception) as e:
                error = str(e)
                materials = request.env['smi.material'].search([('active', '=', True)])
                points = request.env['smi.inventory_point'].search([('active', '=', True)])
                values = {
                    'materials': materials,
                    'points': points,
                    'error': error,
                    'post': post,
                    'is_direktur': user.has_group('inventory_smi.group_direktur'),
                    'is_kepala': user.has_group('inventory_smi.group_kepala_produksi'),
                    'is_admin': user.has_group('inventory_smi.group_admin'),
                    'current_user': user,
                    'active_menu': 'stok',
                }
                return request.render('inventory_smi.stock_form_page', values)

        materials = request.env['smi.material'].search([('active', '=', True)])
        points = request.env['smi.inventory_point'].search([('active', '=', True)])
        values = {
            'materials': materials,
            'points': points,
            'error': None,
            'post': {},
            'is_direktur': user.has_group('inventory_smi.group_direktur'),
            'is_kepala': user.has_group('inventory_smi.group_kepala_produksi'),
            'is_admin': user.has_group('inventory_smi.group_admin'),
            'current_user': user,
            'active_menu': 'stok',
        }
        return request.render('inventory_smi.stock_form_page', values)

    # ------------------------------------------------------------------
    # Stock detail page
    # ------------------------------------------------------------------

    @http.route('/smi/stok/<int:material_id>', type='http', auth='user', website=False)
    def stock_detail(self, material_id, **kwargs):
        user = request.env.user
        material = request.env['smi.material'].browse(material_id)
        if not material.exists():
            return request.redirect('/smi/stok')

        entries = request.env['smi.stock_entry'].search(
            [('material_id', '=', material_id)],
            order='tanggal_masuk desc',
        )
        points_with_stock = entries.mapped('inventory_point_id')

        # provide map points JSON for the frontend detail panel
        map_points = self._get_map_points(material)

        values = {
            'material': material,
            'total_stok': material.total_stok,
            'entries': entries,
            'points_with_stock': points_with_stock,
            'map_points': map_points,
            'map_points_json': json.dumps(map_points),
            'can_manage_points': user.has_group('inventory_smi.group_kepala_produksi'),
            'is_direktur': user.has_group('inventory_smi.group_direktur'),
            'is_kepala': user.has_group('inventory_smi.group_kepala_produksi'),
            'is_admin': user.has_group('inventory_smi.group_admin'),
            'current_user': user,
            'active_menu': 'stok',
        }
        return request.render('inventory_smi.stock_detail_page', values)

    # ------------------------------------------------------------------
    # Denah fullscreen
    # ------------------------------------------------------------------

    @http.route('/smi/stok/denah', type='http', auth='user', website=False)
    def denah_page(self, material_id=None, **kwargs):
        user = request.env.user
        materials = request.env['smi.material'].search([('active', '=', True)])
        selected_material = None
        if material_id:
            try:
                selected_material = request.env['smi.material'].browse(int(material_id))
                if not selected_material.exists():
                    selected_material = None
            except Exception:
                selected_material = None

        map_points = self._get_map_points(selected_material)

        values = {
            'materials': materials,
            'selected_material': selected_material,
            'map_points': map_points,
            'map_points_json': json.dumps(map_points),
            'can_manage_points': user.has_group('inventory_smi.group_kepala_produksi'),
            'is_direktur': user.has_group('inventory_smi.group_direktur'),
            'is_kepala': user.has_group('inventory_smi.group_kepala_produksi'),
            'is_admin': user.has_group('inventory_smi.group_admin'),
            'current_user': user,
            'active_menu': 'stok',
        }
        return request.render('inventory_smi.denah_page', values)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_map_points(self, filter_material=None):
        points = request.env['smi.inventory_point'].search([('active', '=', True)])
        result = []
        for p in points:
            entries = p.stock_entry_ids.filtered(lambda e: e.state == 'tersedia')
            if filter_material:
                entries = entries.filtered(lambda e: e.material_id.id == filter_material.id)
            if not entries:
                color = '#94A3B8'
            elif all(e.material_id.is_low_stock for e in entries):
                color = '#EF4444'
            elif any(e.material_id.is_low_stock for e in entries):
                color = '#F59E0B'
            else:
                color = '#10B981'

            point_entries = p.stock_entry_ids.filtered(lambda e: e.state == 'tersedia')
            materials_in_point = point_entries.mapped('material_id')

            result.append({
                'id': p.id,
                'name': p.name,
                'x': p.koordinat_x,
                'y': p.koordinat_y,
                'color': color,
                'materials': [
                    {
                        'id': m.id,
                        'name': m.name,
                        'total_stok': m.total_stok,
                        'uom': m.uom_id.name,
                        'is_low_stock': m.is_low_stock,
                    }
                    for m in materials_in_point
                ],
            })
        return result
