from odoo import api, fields, models


class SmiActivityLog(models.Model):
    _name = 'smi.activity.log'
    _description = 'Log Aktivitas Pengguna'
    _order = 'tanggal desc, id desc'

    user_id = fields.Many2one(
        'res.users', string='Pengguna', default=lambda self: self.env.user, index=True
    )
    jabatan = fields.Char(string='Jabatan')
    tanggal = fields.Datetime(string='Tanggal & Waktu', default=fields.Datetime.now, required=True)
    tipe = fields.Selection(
        [
            ('stok_masuk', 'Stok Masuk'),
            ('stok_keluar', 'Stok Keluar'),
            ('order_dibuat', 'Order Dibuat'),
            ('order_selesai', 'Order Selesai'),
            ('order_dibatalkan', 'Order Dibatalkan'),
            ('user_dibuat', 'Pengguna Dibuat'),
            ('titik_ditambah', 'Titik Inventori Ditambah'),
        ],
        string='Tipe Aktivitas',
        required=True,
        index=True,
    )
    deskripsi = fields.Text(string='Deskripsi', required=True)
    ref_model = fields.Char(string='Model Referensi')
    ref_id = fields.Integer(string='ID Referensi')
