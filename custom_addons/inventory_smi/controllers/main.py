import json

from odoo import http
from odoo.http import request, Response


class SmiMainController(http.Controller):

    # ------------------------------------------------------------------
    # Index redirect
    # ------------------------------------------------------------------

    @http.route('/smi', type='http', auth='user', website=False)
    def smi_index(self, **kwargs):
        return request.redirect('/smi/dashboard')

    # ------------------------------------------------------------------
    # Dashboard page
    # ------------------------------------------------------------------

    @http.route('/smi/dashboard', type='http', auth='user', website=False)
    def dashboard(self, **kwargs):
        user = request.env.user
        values = {
            **self._get_dashboard_stats(),
            'top10_bahan': self._get_top10_bahan(),
            'recent_orders': self._get_recent_orders(),
            'recent_activity': self._get_recent_activity(),
            'map_points': self._get_map_points(),
            'is_direktur': user.has_group('inventory_smi.group_direktur'),
            'is_kepala': user.has_group('inventory_smi.group_kepala_produksi'),
            'is_admin': user.has_group('inventory_smi.group_admin'),
            'current_user': user,
            'active_menu': 'dashboard',
        }
        return request.render('inventory_smi.dashboard_page', values)

    # ------------------------------------------------------------------
    # Dashboard JSON API
    # ------------------------------------------------------------------

    @http.route('/smi/api/dashboard', type='http', auth='user', methods=['GET'], csrf=False)
    def dashboard_api(self, **kwargs):
        stats = self._get_dashboard_stats()

        top10 = [
            {
                'id': m.id,
                'name': m.name,
                'total_stok': m.total_stok,
                'satuan': m.uom_id.name,
                'is_low_stock': m.is_low_stock,
                'last_added_date': (
                    m.last_added_date.isoformat() if m.last_added_date else None
                ),
            }
            for m in self._get_top10_bahan()
        ]

        orders = [
            {
                'id': o.id,
                'name': o.name,
                'no_spk': o.no_spk or '',
                'tanggal': o.tanggal.isoformat() if o.tanggal else None,
                'state': o.state,
                'user': o.user_id.name or '',
            }
            for o in self._get_recent_orders()
        ]

        activity = [
            {
                'id': a.id,
                'user': a.user_id.name or '',
                'jabatan': a.jabatan or '',
                'tanggal': a.tanggal.isoformat() if a.tanggal else None,
                'tipe': a.tipe,
                'deskripsi': a.deskripsi,
            }
            for a in self._get_recent_activity()
        ]

        data = {**stats, 'top10_bahan': top10, 'recent_orders': orders, 'recent_activity': activity}
        return Response(json.dumps(data, default=str), content_type='application/json')

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_dashboard_stats(self):
        env = request.env
        materials = env['smi.material'].search([('active', '=', True)])
        total_bahan = len(materials)
        total_stok = sum(materials.mapped('total_stok'))
        active_orders = env['smi.order'].search_count([('state', '=', 'dikonfirmasi')])
        low_stock_count = len(materials.filtered(lambda m: m.is_low_stock))
        return {
            'total_bahan': total_bahan,
            'total_stok': total_stok,
            'active_orders': active_orders,
            'low_stock_count': low_stock_count,
        }

    def _get_top10_bahan(self):
        materials = request.env['smi.material'].search([('active', '=', True)])
        low = materials.filtered(lambda m: m.is_low_stock).sorted('total_stok')
        normal = materials.filtered(lambda m: not m.is_low_stock).sorted('total_stok')
        # Show low-stock items first, then fill remaining slots with normal-stock items up to 10 total
        max_items = 10
        result = list(low)
        if len(result) < max_items:
            needed = max_items - len(result)
            result += list(normal[:needed])
        return result[:max_items]

    def _get_recent_orders(self):
        return request.env['smi.order'].search(
            [], order='tanggal desc, id desc', limit=3
        )

    def _get_recent_activity(self):
        return request.env['smi.activity.log'].search(
            [], order='tanggal desc, id desc', limit=5
        )

    def _get_map_points(self):
        points = request.env['smi.inventory_point'].search([('active', '=', True)])
        result = []
        for p in points:
            entries = p.stock_entry_ids.filtered(lambda e: e.state == 'tersedia')
            if not entries:
                color = '#94A3B8'
            elif any(e.material_id.is_low_stock for e in entries):
                color = '#F59E0B'
            else:
                color = "#239670"
            result.append({
                'id': p.id,
                'name': p.name,
                'x': p.koordinat_x,
                'y': p.koordinat_y,
                'color': color,
            })
        return result
