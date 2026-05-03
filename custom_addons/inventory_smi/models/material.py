from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SmiUom(models.Model):
    _name = 'smi.uom'
    _description = 'Satuan Bahan'
    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Nama satuan sudah ada.'),
    ]

    name = fields.Char(string='Nama Satuan', required=True)
    active = fields.Boolean(default=True)

    material_ids = fields.One2many('smi.material', 'uom_id', string='Bahan')


class SmiMaterialCategory(models.Model):
    _name = 'smi.material.category'
    _description = 'Kategori Bahan'
    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Nama kategori sudah ada.'),
    ]

    name = fields.Char(string='Nama Kategori', required=True)
    active = fields.Boolean(default=True)

    material_ids = fields.One2many('smi.material', 'category_id', string='Bahan')


class SmiMaterial(models.Model):
    _name = 'smi.material'
    _description = 'Bahan Baku'

    name = fields.Char(string='Nama Bahan', required=True)
    uom_id = fields.Many2one('smi.uom', string='Satuan', required=True, ondelete='restrict')
    category_id = fields.Many2one('smi.material.category', string='Kategori', required=True, ondelete='restrict')
    warna = fields.Char(string='Warna / Varian')
    stok_minimum = fields.Float(string='Stok Minimum (Reorder Point)', default=0.0)
    active = fields.Boolean(default=True)
    notification_sent = fields.Boolean(default=False, string='Notifikasi Terkirim')

    stock_entry_ids = fields.One2many('smi.stock_entry', 'material_id', string='Riwayat Stok')

    total_stok = fields.Float(
        string='Total Stok',
        compute='_compute_total_stok',
        store=True,
    )
    is_low_stock = fields.Boolean(
        string='Stok Rendah',
        compute='_compute_is_low_stock',
        store=True,
    )
    last_added_date = fields.Datetime(
        string='Terakhir Ditambahkan',
        compute='_compute_last_added_date',
        store=True,
    )

    @api.depends('stock_entry_ids.jumlah_tersisa', 'stock_entry_ids.state')
    def _compute_total_stok(self):
        for material in self:
            material.total_stok = sum(
                e.jumlah_tersisa
                for e in material.stock_entry_ids
                if e.state == 'tersedia'
            )

    @api.depends('total_stok', 'stok_minimum')
    def _compute_is_low_stock(self):
        for material in self:
            if material.stok_minimum > 0:
                material.is_low_stock = material.total_stok < material.stok_minimum
            else:
                material.is_low_stock = False

    @api.depends('stock_entry_ids.tanggal_masuk')
    def _compute_last_added_date(self):
        for material in self:
            dates = material.stock_entry_ids.mapped('tanggal_masuk')
            material.last_added_date = max(dates) if dates else False
