from odoo import api, fields, models

_ROLE_MAP = [
    ('inventory_smi.group_admin', 'Admin'),
    ('inventory_smi.group_kepala_produksi', 'Kepala Produksi'),
    ('inventory_smi.group_staf_produksi', 'Staf Produksi'),
    ('inventory_smi.group_direktur', 'Direktur'),
]


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
            ('titik_dihapus', 'Titik Inventori Dihapus'),
        ],
        string='Tipe Aktivitas',
        required=True,
        index=True,
    )
    deskripsi = fields.Text(string='Deskripsi', required=True)
    ref_model = fields.Char(string='Model Referensi')
    ref_id = fields.Integer(string='ID Referensi')

    # ------------------------------------------------------------------
    # Helpers called by other models
    # ------------------------------------------------------------------

    @api.model
    def _get_role_label(self):
        user = self.env.user
        for xml_id, label in _ROLE_MAP:
            if user.has_group(xml_id):
                return label
        return 'Pengguna'

    @api.model
    def _log(self, tipe, deskripsi, ref_model=None, ref_id=None):
        self.sudo().create({
            'user_id': self.env.uid,
            'jabatan': self._get_role_label(),
            'tipe': tipe,
            'deskripsi': deskripsi,
            'ref_model': ref_model,
            'ref_id': ref_id,
        })

    # ------------------------------------------------------------------
    # Low-stock notification
    # ------------------------------------------------------------------

    @api.model
    def _check_and_notify_low_stock(self, material):
        material.invalidate_recordset()
        if material.is_low_stock and not material.notification_sent:
            material.sudo().notification_sent = True
            kepala_group = self.env.ref('inventory_smi.group_kepala_produksi')
            recipients = kepala_group.users.filtered(
                lambda u: u.partner_id and u.partner_id.email
            )
            template = self.env.ref(
                'inventory_smi.email_template_low_stock', raise_if_not_found=False
            )
            if template and recipients:
                for user in recipients:
                    template.with_context(material=material).send_mail(
                        user.partner_id.id, force_send=False
                    )
            try:
                self.env['bus.bus']._sendone(
                    'smi_low_stock',
                    {'type': 'low_stock',
                     'material': material.name,
                     'stok': material.total_stok},
                )
            except Exception:
                pass
        elif not material.is_low_stock and material.notification_sent:
            material.sudo().notification_sent = False
