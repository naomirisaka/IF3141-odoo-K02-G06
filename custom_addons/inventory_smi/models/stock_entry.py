from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SmiStockEntry(models.Model):
    _name = 'smi.stock_entry'
    _description = 'Riwayat Stok Bahan Baku'
    _order = 'tanggal_masuk asc'

    material_id = fields.Many2one(
        'smi.material', string='Bahan', required=True, ondelete='restrict', index=True
    )
    inventory_point_id = fields.Many2one(
        'smi.inventory_point', string='Titik Penyimpanan', required=True, ondelete='restrict', index=True
    )
    jumlah_awal = fields.Float(string='Jumlah Awal', required=True)
    jumlah_tersisa = fields.Float(string='Jumlah Tersisa')
    tanggal_masuk = fields.Datetime(
        string='Tanggal Masuk', required=True, default=fields.Datetime.now
    )
    user_id = fields.Many2one('res.users', string='Ditambahkan Oleh', default=lambda self: self.env.user)
    catatan = fields.Text(string='Catatan')
    state = fields.Selection(
        [('tersedia', 'Tersedia'), ('habis', 'Habis')],
        string='Status',
        default='tersedia',
        required=True,
    )

    @api.constrains('jumlah_awal')
    def _check_jumlah_awal(self):
        for entry in self:
            if entry.jumlah_awal <= 0:
                raise ValidationError('Jumlah awal harus lebih dari 0.')

    @api.constrains('jumlah_tersisa', 'jumlah_awal')
    def _check_jumlah_tersisa(self):
        for entry in self:
            if entry.jumlah_tersisa < 0:
                raise ValidationError('Jumlah tersisa tidak boleh negatif.')
            if entry.jumlah_tersisa > entry.jumlah_awal:
                raise ValidationError(
                    f'Jumlah tersisa ({entry.jumlah_tersisa}) tidak boleh melebihi '
                    f'jumlah awal ({entry.jumlah_awal}).'
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'jumlah_tersisa' not in vals or vals['jumlah_tersisa'] is None:
                vals['jumlah_tersisa'] = vals.get('jumlah_awal', 0.0)
        return super().create(vals_list)

    def write(self, vals):
        result = super().write(vals)
        if 'jumlah_tersisa' in vals:
            for entry in self:
                if entry.jumlah_tersisa == 0.0 and entry.state != 'habis':
                    super(SmiStockEntry, entry).write({'state': 'habis'})
                elif entry.jumlah_tersisa > 0.0 and entry.state == 'habis':
                    super(SmiStockEntry, entry).write({'state': 'tersedia'})
        return result
