import json

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, ValidationError


class SmiOrderController(http.Controller):

    # ──────────────────────────────────────────────────────────────────────
    # Order list
    # ──────────────────────────────────────────────────────────────────────

    @http.route('/smi/order', type='http', auth='user', website=False)
    def order_list(self, search='', status='', **kwargs):
        user = request.env.user
        domain = []
        if search:
            domain.append(('name', 'ilike', search))
        if status:
            domain.append(('state', '=', status))

        orders = request.env['smi.order'].search(domain, order='tanggal desc, id desc')

        values = {
            'orders': orders,
            'search': search,
            'status': status,
            'is_direktur': user.has_group('inventory_smi.group_direktur'),
            'is_kepala': user.has_group('inventory_smi.group_kepala_produksi'),
            'is_admin': user.has_group('inventory_smi.group_admin'),
            'current_user': user,
            'active_menu': 'order',
            'page_title': 'Daftar Order',
        }
        return request.render('inventory_smi.order_list_page', values)

    # ──────────────────────────────────────────────────────────────────────
    # Add order — Step 1: order header
    # ──────────────────────────────────────────────────────────────────────

    @http.route('/smi/order/tambah', type='http', auth='user', website=False,
                methods=['GET', 'POST'])
    def order_form_step1(self, **post):
        user = request.env.user
        if user.has_group('inventory_smi.group_direktur'):
            return request.redirect('/smi/order')

        if request.httprequest.method == 'POST':
            try:
                name = post.get('name', '').strip()
                no_spk = post.get('no_spk', '').strip()
                tanggal = post.get('tanggal') or False
                catatan = post.get('catatan', '')

                if not name:
                    raise ValidationError('Nama pesanan wajib diisi.')

                vals = {'name': name, 'catatan': catatan}
                if no_spk:
                    vals['no_spk'] = no_spk
                if tanggal:
                    vals['tanggal'] = tanggal

                order = request.env['smi.order'].create(vals)
                return request.redirect(f'/smi/order/tambah/step2?order_id={order.id}')
            except (ValidationError, Exception) as e:
                values = self._step1_values(user, error=str(e), post=post)
                return request.render('inventory_smi.order_form_step1_page', values)

        values = self._step1_values(user)
        return request.render('inventory_smi.order_form_step1_page', values)

    def _step1_values(self, user, error=None, post=None):
        from datetime import date
        return {
            'error': error,
            'post': post or {},
            'today': date.today().isoformat(),
            'is_direktur': user.has_group('inventory_smi.group_direktur'),
            'is_kepala': user.has_group('inventory_smi.group_kepala_produksi'),
            'is_admin': user.has_group('inventory_smi.group_admin'),
            'current_user': user,
            'active_menu': 'order',
            'page_title': 'Tambah Order — Langkah 1',
            'step': 1,
        }

    # ──────────────────────────────────────────────────────────────────────
    # Add order — Step 2: material lines
    # ──────────────────────────────────────────────────────────────────────

    @http.route('/smi/order/tambah/step2', type='http', auth='user', website=False,
                methods=['GET', 'POST'])
    def order_form_step2(self, order_id=None, **post):
        user = request.env.user
        if user.has_group('inventory_smi.group_direktur'):
            return request.redirect('/smi/order')

        if not order_id:
            return request.redirect('/smi/order/tambah')

        try:
            order_id = int(order_id)
        except (TypeError, ValueError):
            return request.redirect('/smi/order/tambah')

        order = request.env['smi.order'].browse(order_id)
        if not order.exists() or order.state != 'draft':
            return request.redirect('/smi/order')

        if request.httprequest.method == 'POST':
            action = post.get('action', '')

            if action == 'add_line':
                try:
                    mat_id = int(post.get('material_id', 0))
                    jumlah = float(post.get('jumlah_dibutuhkan', 0))
                    mode = post.get('mode_pick', 'auto')
                    if not mat_id or jumlah <= 0:
                        raise ValidationError('Bahan dan jumlah wajib diisi.')
                    request.env['smi.order.line'].create({
                        'order_id': order.id,
                        'material_id': mat_id,
                        'jumlah_dibutuhkan': jumlah,
                        'mode_pick': mode,
                    })
                except Exception as e:
                    pass
                return request.redirect(f'/smi/order/tambah/step2?order_id={order_id}')

            elif action == 'remove_line':
                line_id = int(post.get('line_id', 0))
                if line_id:
                    line = request.env['smi.order.line'].browse(line_id)
                    if line.exists() and line.order_id.id == order.id:
                        line.unlink()
                return request.redirect(f'/smi/order/tambah/step2?order_id={order_id}')

            elif action == 'add_manual_pick':
                try:
                    line_id = int(post.get('line_id', 0))
                    entry_id = int(post.get('stock_entry_id', 0))
                    jumlah = float(post.get('jumlah_diambil', 0))
                    if line_id and entry_id and jumlah > 0:
                        line = request.env['smi.order.line'].browse(line_id)
                        if line.exists() and line.order_id.id == order.id:
                            request.env['smi.order.pick'].create({
                                'order_line_id': line_id,
                                'stock_entry_id': entry_id,
                                'jumlah_diambil': jumlah,
                            })
                except Exception:
                    pass
                return request.redirect(f'/smi/order/tambah/step2?order_id={order_id}')

            elif action == 'remove_manual_pick':
                pick_id = int(post.get('pick_id', 0))
                if pick_id:
                    pick = request.env['smi.order.pick'].browse(pick_id)
                    if pick.exists() and pick.order_line_id.order_id.id == order.id:
                        pick.unlink()
                return request.redirect(f'/smi/order/tambah/step2?order_id={order_id}')

            elif action == 'next':
                return request.redirect(f'/smi/order/tambah/step3?order_id={order_id}')

            return request.redirect(f'/smi/order/tambah/step2?order_id={order_id}')

        materials = request.env['smi.material'].search([('active', '=', True)])
        points_with_stock = request.env['smi.inventory_point'].search([('active', '=', True)])

        fifo_previews = {}
        for line in order.order_line_ids:
            if line.mode_pick == 'auto':
                fifo_previews[line.id] = self._compute_fifo_preview(
                    line.material_id, line.jumlah_dibutuhkan
                )

        values = {
            'order': order,
            'materials': materials,
            'points_with_stock': points_with_stock,
            'fifo_previews': fifo_previews,
            'is_direktur': user.has_group('inventory_smi.group_direktur'),
            'is_kepala': user.has_group('inventory_smi.group_kepala_produksi'),
            'is_admin': user.has_group('inventory_smi.group_admin'),
            'current_user': user,
            'active_menu': 'order',
            'page_title': 'Tambah Order — Langkah 2',
            'step': 2,
        }
        return request.render('inventory_smi.order_form_step2_page', values)

    def _compute_fifo_preview(self, material, needed):
        entries = request.env['smi.stock_entry'].search([
            ('material_id', '=', material.id),
            ('jumlah_tersisa', '>', 0),
            ('state', '=', 'tersedia'),
        ], order='tanggal_masuk asc')

        remaining = needed
        picks = []
        for entry in entries:
            if remaining <= 0:
                break
            take = min(entry.jumlah_tersisa, remaining)
            picks.append({
                'point_name': entry.inventory_point_id.name,
                'jumlah_diambil': take,
                'tanggal_masuk': entry.tanggal_masuk,
                'entry_id': entry.id,
            })
            remaining -= take
        return picks

    # ──────────────────────────────────────────────────────────────────────
    # Add order — Step 3: confirmation
    # ──────────────────────────────────────────────────────────────────────

    @http.route('/smi/order/tambah/step3', type='http', auth='user', website=False,
                methods=['GET', 'POST'])
    def order_form_step3(self, order_id=None, **post):
        user = request.env.user
        if user.has_group('inventory_smi.group_direktur'):
            return request.redirect('/smi/order')

        if not order_id:
            return request.redirect('/smi/order/tambah')

        try:
            order_id = int(order_id)
        except (TypeError, ValueError):
            return request.redirect('/smi/order/tambah')

        order = request.env['smi.order'].browse(order_id)
        if not order.exists():
            return request.redirect('/smi/order')

        error = None
        if request.httprequest.method == 'POST':
            action = post.get('action', '')
            if action == 'confirm':
                try:
                    order.action_confirm()
                    return request.redirect(f'/smi/order/{order.id}')
                except (ValidationError, Exception) as e:
                    error = str(e)
            elif action == 'back':
                return request.redirect(f'/smi/order/tambah/step2?order_id={order_id}')

        all_sufficient = all(line.is_sufficient for line in order.order_line_ids)

        values = {
            'order': order,
            'all_sufficient': all_sufficient,
            'error': error,
            'is_direktur': user.has_group('inventory_smi.group_direktur'),
            'is_kepala': user.has_group('inventory_smi.group_kepala_produksi'),
            'is_admin': user.has_group('inventory_smi.group_admin'),
            'current_user': user,
            'active_menu': 'order',
            'page_title': 'Tambah Order — Konfirmasi',
            'step': 3,
        }
        return request.render('inventory_smi.order_form_step3_page', values)

    # ──────────────────────────────────────────────────────────────────────
    # Order detail
    # ──────────────────────────────────────────────────────────────────────

    @http.route('/smi/order/<int:order_id>', type='http', auth='user', website=False,
                methods=['GET', 'POST'])
    def order_detail(self, order_id, **post):
        user = request.env.user
        order = request.env['smi.order'].browse(order_id)
        if not order.exists():
            return request.redirect('/smi/order')

        error = None
        if request.httprequest.method == 'POST':
            action = post.get('action', '')
            if action == 'cancel':
                try:
                    order.action_cancel()
                except (ValidationError, Exception) as e:
                    error = str(e)
            elif action == 'complete':
                try:
                    order.action_complete()
                except (ValidationError, Exception) as e:
                    error = str(e)

        values = {
            'order': order,
            'error': error,
            'is_direktur': user.has_group('inventory_smi.group_direktur'),
            'is_kepala': user.has_group('inventory_smi.group_kepala_produksi'),
            'is_admin': user.has_group('inventory_smi.group_admin'),
            'current_user': user,
            'active_menu': 'order',
            'page_title': f'Detail Order — {order.name}',
        }
        return request.render('inventory_smi.order_detail_page', values)

    # ──────────────────────────────────────────────────────────────────────
    # Cancel shortcut (POST /smi/order/<id>/cancel)
    # ──────────────────────────────────────────────────────────────────────

    @http.route('/smi/order/<int:order_id>/cancel', type='http', auth='user', website=False,
                methods=['POST'])
    def order_cancel(self, order_id, **post):
        order = request.env['smi.order'].browse(order_id)
        if order.exists():
            try:
                order.action_cancel()
            except (ValidationError, Exception):
                pass
        return request.redirect(f'/smi/order/{order_id}')
