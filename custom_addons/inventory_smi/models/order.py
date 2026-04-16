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
