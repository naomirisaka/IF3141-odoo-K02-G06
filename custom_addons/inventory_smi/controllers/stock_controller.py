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
                    vals['tanggal_masuk'] = tanggal_masuk.replace('T', ' ')

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
        order_usage = []
        try:
            order_lines = request.env['smi.order.line'].search(
                [
                    ('material_id', '=', material_id),
                    ('order_id.state', 'in', ['dikonfirmasi', 'selesai']),
                ],
                order='id desc',
            )
            ordered_lines = sorted(
                order_lines,
                key=lambda line: (
                    line.order_id.tanggal or line.create_date,
                    line.order_id.id or 0,
                    line.id or 0,
                ),
                reverse=True,
            )
            for line in ordered_lines:
                order_usage.append({
                    'order_id': line.order_id.id,
                    'order_name': line.order_id.name,
                    'no_spk': line.order_id.no_spk or '-',
                    'tanggal': line.order_id.tanggal,
                    'state': line.order_id.state,
                    'jumlah_dibutuhkan': line.jumlah_dibutuhkan,
                    'jumlah_terpenuhi': line.jumlah_terpenuhi,
                    'mode_pick': line.mode_pick,
                    'pick_count': len(line.order_pick_ids),
                })
        except Exception:
            order_usage = []
        points_with_stock = entries.mapped('inventory_point_id')
        inventory_points = request.env['smi.inventory_point'].search([('active', '=', True)], order='name asc')

        # provide map points JSON for the frontend detail panel
        map_points = self._get_map_points(material)

        values = {
            'material': material,
            'total_stok': material.total_stok,
            'entries': entries,
            'order_usage': order_usage,
            'points_with_stock': points_with_stock,
            'inventory_points': inventory_points,
            'map_points': map_points,
            'map_points_json': json.dumps(map_points),
            'can_manage_points': user.has_group('inventory_smi.group_kepala_produksi') or user.has_group('inventory_smi.group_admin'),
            'is_direktur': user.has_group('inventory_smi.group_direktur'),
            'is_kepala': user.has_group('inventory_smi.group_kepala_produksi'),
            'is_admin': user.has_group('inventory_smi.group_admin'),
            'current_user': user,
            'active_menu': 'stok',
        }
        return request.render('inventory_smi.stock_detail_page', values)

    @http.route('/smi/stok/<int:material_id>/stok-minimum', type='http', auth='user', website=False, methods=['POST'])
    def update_stock_minimum(self, material_id, **post):
        user = request.env.user
        if not (user.has_group('inventory_smi.group_kepala_produksi') or user.has_group('inventory_smi.group_admin')):
            return request.not_found()

        material = request.env['smi.material'].browse(material_id)
        if not material.exists():
            return request.redirect('/smi/stok')

        try:
            stok_minimum = float(post.get('stok_minimum', material.stok_minimum or 0.0))
        except (TypeError, ValueError):
            stok_minimum = material.stok_minimum or 0.0

        if stok_minimum < 0:
            stok_minimum = 0.0

        material.sudo().write({'stok_minimum': stok_minimum})
        return request.redirect(f'/smi/stok/{material_id}')

    @http.route('/smi/stok/entry/<int:entry_id>/lokasi', type='http', auth='user', website=False, methods=['POST'])
    def update_stock_location(self, entry_id, **post):
        user = request.env.user
        if not (user.has_group('inventory_smi.group_kepala_produksi') or user.has_group('inventory_smi.group_admin')):
            return request.not_found()

        entry = request.env['smi.stock_entry'].browse(entry_id)
        if not entry.exists():
            return request.redirect('/smi/stok')

        try:
            inventory_point_id = int(post.get('inventory_point_id', 0))
        except (TypeError, ValueError):
            inventory_point_id = 0

        point = request.env['smi.inventory_point'].browse(inventory_point_id)
        if not point.exists() or not point.active:
            return request.redirect(f'/smi/stok/{entry.material_id.id}')

        entry.sudo().write({'inventory_point_id': point.id})
        return request.redirect(f'/smi/stok/{entry.material_id.id}')

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
            'can_manage_points': user.has_group('inventory_smi.group_kepala_produksi') or user.has_group('inventory_smi.group_admin'),
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
