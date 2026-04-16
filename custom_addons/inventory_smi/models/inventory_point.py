from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SmiInventoryPoint(models.Model):
    _name = 'smi.inventory_point'
    _description = 'Titik Penyimpanan Inventori'

    name = fields.Char(string='Nama Titik', required=True)
    koordinat_x = fields.Float(string='Koordinat X (%)', default=50.0)
    koordinat_y = fields.Float(string='Koordinat Y (%)', default=50.0)
    deskripsi = fields.Text(string='Keterangan')
    active = fields.Boolean(default=True)

    stock_entry_ids = fields.One2many('smi.stock_entry', 'inventory_point_id', string='Stok di Titik Ini')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for point in records:
            self.env['smi.activity.log']._log(
                tipe='titik_ditambah',
                deskripsi=f'Menambahkan titik inventori baru: {point.name}',
                ref_model='smi.inventory_point',
                ref_id=point.id,
            )
        return records

    @api.constrains('koordinat_x', 'koordinat_y')
    def _check_coordinates(self):
        for point in self:
            if not (0.0 <= point.koordinat_x <= 100.0):
                raise ValidationError(
                    f'Koordinat X harus antara 0 dan 100. Nilai saat ini: {point.koordinat_x}'
                )
            if not (0.0 <= point.koordinat_y <= 100.0):
                raise ValidationError(
                    f'Koordinat Y harus antara 0 dan 100. Nilai saat ini: {point.koordinat_y}'
                )
