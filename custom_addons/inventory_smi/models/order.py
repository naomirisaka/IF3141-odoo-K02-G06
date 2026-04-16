from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SmiOrder(models.Model):
    _name = 'smi.order'
    _description = 'Pesanan'
    _order = 'tanggal desc, id desc'

    name = fields.Char(string='Nama Pesanan', required=True)
    no_spk = fields.Char(string='No. SPK')
    tanggal = fields.Date(string='Tanggal', required=True, default=fields.Date.today)
    user_id = fields.Many2one('res.users', string='Dibuat Oleh', default=lambda self: self.env.user)
    catatan = fields.Text(string='Catatan')
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('dikonfirmasi', 'Dikonfirmasi'),
            ('selesai', 'Selesai'),
            ('dibatalkan', 'Dibatalkan'),
        ],
        string='Status',
        default='draft',
        required=True,
    )

    order_line_ids = fields.One2many('smi.order.line', 'order_id', string='Bahan yang Dibutuhkan')

    # ------------------------------------------------------------------
    # Guard: prevent editing once confirmed
    # ------------------------------------------------------------------

    def write(self, vals):
        for order in self:
            if order.state not in ('draft', 'dibatalkan') and set(vals) - {'state'}:
                raise ValidationError(
                    'Order yang sudah dikonfirmasi tidak dapat diubah.'
                )
        return super().write(vals)

    # ------------------------------------------------------------------
    # State actions
    # ------------------------------------------------------------------

    def action_confirm(self):
        for order in self:
            if order.state != 'draft':
                raise ValidationError('Hanya order berstatus Draft yang dapat dikonfirmasi.')
            if not order.order_line_ids:
                raise ValidationError('Order harus memiliki minimal satu baris bahan.')
            for line in order.order_line_ids:
                if line.mode_pick == 'auto':
                    order._apply_fifo(line)
                else:
                    order._validate_manual_picks(line)
            order.sudo().write({'state': 'dikonfirmasi'})

    def action_complete(self):
        for order in self:
            if order.state != 'dikonfirmasi':
                raise ValidationError('Hanya order berstatus Dikonfirmasi yang dapat diselesaikan.')
            order.sudo().write({'state': 'selesai'})

    def action_cancel(self):
        for order in self:
            if order.state == 'selesai':
                raise ValidationError('Order yang sudah selesai tidak dapat dibatalkan.')
            order.sudo().write({'state': 'dibatalkan'})

    # ------------------------------------------------------------------
    # FIFO algorithm
    # ------------------------------------------------------------------

    def _apply_fifo(self, order_line):
        material = order_line.material_id
        needed = order_line.jumlah_dibutuhkan

        total_available = sum(
            e.jumlah_tersisa for e in material.stock_entry_ids
            if e.jumlah_tersisa > 0 and e.state == 'tersedia'
        )
        if total_available < needed:
            raise ValidationError(
                f'Stok {material.name} tidak mencukupi. '
                f'Tersedia: {total_available} {material.uom_id.name}, '
                f'Dibutuhkan: {needed} {material.uom_id.name}.'
            )

        entries = self.env['smi.stock_entry'].search([
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
                'order_line_id': order_line.id,
                'stock_entry_id': entry.id,
                'jumlah_diambil': take,
            })
            entry.write({'jumlah_tersisa': entry.jumlah_tersisa - take})
            remaining -= take

        self.env['smi.order.pick'].create(picks)

    # ------------------------------------------------------------------
    # Manual pick validation
    # ------------------------------------------------------------------

    def _validate_manual_picks(self, order_line):
        picks = order_line.order_pick_ids
        if not picks:
            raise ValidationError(
                f'Baris manual untuk {order_line.material_id.name} belum memiliki detail pengambilan.'
            )

        for pick in picks:
            if pick.jumlah_diambil > pick.stock_entry_id.jumlah_tersisa:
                raise ValidationError(
                    f'Jumlah yang diambil ({pick.jumlah_diambil}) melebihi '
                    f'stok tersisa di titik tersebut ({pick.stock_entry_id.jumlah_tersisa}).'
                )

        total_picked = sum(p.jumlah_diambil for p in picks)
        if abs(total_picked - order_line.jumlah_dibutuhkan) > 0.001:
            raise ValidationError(
                f'Total pengambilan manual ({total_picked}) harus sama dengan '
                f'kebutuhan ({order_line.jumlah_dibutuhkan}).'
            )

        for pick in picks:
            pick.stock_entry_id.write({
                'jumlah_tersisa': pick.stock_entry_id.jumlah_tersisa - pick.jumlah_diambil
            })


class SmiOrderLine(models.Model):
    _name = 'smi.order.line'
    _description = 'Baris Kebutuhan Bahan'

    order_id = fields.Many2one('smi.order', string='Order', required=True, ondelete='cascade', index=True)
    material_id = fields.Many2one('smi.material', string='Bahan', required=True, ondelete='restrict')
    jumlah_dibutuhkan = fields.Float(string='Jumlah Dibutuhkan', required=True)
    mode_pick = fields.Selection(
        [('auto', 'Otomatis (FIFO)'), ('manual', 'Manual')],
        string='Mode Pengambilan',
        default='auto',
        required=True,
    )

    order_pick_ids = fields.One2many('smi.order.pick', 'order_line_id', string='Detail Pengambilan')

    jumlah_terpenuhi = fields.Float(
        string='Jumlah Terpenuhi',
        compute='_compute_jumlah_terpenuhi',
        store=True,
    )
    is_sufficient = fields.Boolean(
        string='Stok Cukup',
        compute='_compute_is_sufficient',
    )

    @api.depends('order_pick_ids.jumlah_diambil')
    def _compute_jumlah_terpenuhi(self):
        for line in self:
            line.jumlah_terpenuhi = sum(p.jumlah_diambil for p in line.order_pick_ids)

    @api.depends('material_id', 'jumlah_dibutuhkan')
    def _compute_is_sufficient(self):
        for line in self:
            if line.material_id:
                line.is_sufficient = line.material_id.total_stok >= line.jumlah_dibutuhkan
            else:
                line.is_sufficient = False


class SmiOrderPick(models.Model):
    _name = 'smi.order.pick'
    _description = 'Detail Pengambilan Stok per Titik'

    order_line_id = fields.Many2one(
        'smi.order.line', string='Baris Order', required=True, ondelete='cascade', index=True
    )
    stock_entry_id = fields.Many2one(
        'smi.stock_entry', string='Batch Stok', required=True, ondelete='restrict'
    )
    inventory_point_id = fields.Many2one(
        related='stock_entry_id.inventory_point_id',
        string='Titik Penyimpanan',
        store=True,
    )
    jumlah_diambil = fields.Float(string='Jumlah Diambil', required=True)
