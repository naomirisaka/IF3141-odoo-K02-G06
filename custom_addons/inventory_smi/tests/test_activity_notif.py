from unittest.mock import patch

from odoo.tests.common import TransactionCase


class _NotifBase(TransactionCase):

    def setUp(self):
        super().setUp()
        self.uom = self.env['smi.uom'].create({'name': 'Lembar-notif'})
        self.cat = self.env['smi.material.category'].create({'name': 'Kertas-notif'})
        self.material = self.env['smi.material'].create({
            'name': 'Kertas HVS 80gsm',
            'uom_id': self.uom.id,
            'category_id': self.cat.id,
            'stok_minimum': 50.0,
        })
        self.point = self.env['smi.inventory_point'].create(
            {'name': 'Rak-notif', 'koordinat_x': 5.0, 'koordinat_y': 5.0})

        # Give demo kepala user an email so mail.mail records are created
        kepala_user = self.env.ref('inventory_smi.user_kepala_produksi', raise_if_not_found=False)
        if kepala_user:
            kepala_user.sudo().partner_id.write({'email': 'kepala@test.smi'})

    def _add_stock(self, jumlah, tanggal='2026-01-01 08:00:00'):
        return self.env['smi.stock_entry'].create({
            'material_id': self.material.id,
            'inventory_point_id': self.point.id,
            'jumlah_awal': jumlah,
            'tanggal_masuk': tanggal,
        })

    def _make_order(self, jumlah):
        order = self.env['smi.order'].create({
            'name': 'Order Notif Test',
            'tanggal': '2026-02-01',
        })
        self.env['smi.order.line'].create({
            'order_id': order.id,
            'material_id': self.material.id,
            'jumlah_dibutuhkan': jumlah,
            'mode_pick': 'auto',
        })
        return order


class TestActivityLogAutoWrite(_NotifBase):

    def test_stock_entry_create_logs_stok_masuk(self):
        """Creating smi.stock_entry auto-creates activity log with tipe='stok_masuk'."""
        before = self.env['smi.activity.log'].search_count([('tipe', '=', 'stok_masuk')])
        self._add_stock(100.0)
        after = self.env['smi.activity.log'].search_count([('tipe', '=', 'stok_masuk')])
        self.assertEqual(after, before + 1)

    def test_order_confirm_logs_stok_keluar(self):
        """Confirming order auto-creates activity log with tipe='stok_keluar' per material."""
        self._add_stock(100.0)
        order = self._make_order(30.0)
        before = self.env['smi.activity.log'].search_count([('tipe', '=', 'stok_keluar')])
        order.action_confirm()
        after = self.env['smi.activity.log'].search_count([('tipe', '=', 'stok_keluar')])
        self.assertGreater(after, before)

    def test_order_create_logs_order_dibuat(self):
        """Creating smi.order auto-creates activity log with tipe='order_dibuat'."""
        before = self.env['smi.activity.log'].search_count([('tipe', '=', 'order_dibuat')])
        self._make_order(10.0)
        after = self.env['smi.activity.log'].search_count([('tipe', '=', 'order_dibuat')])
        self.assertEqual(after, before + 1)

    def test_order_complete_logs_order_selesai(self):
        """Setting order to selesai auto-logs tipe='order_selesai'."""
        self._add_stock(100.0)
        order = self._make_order(10.0)
        order.action_confirm()
        before = self.env['smi.activity.log'].search_count([('tipe', '=', 'order_selesai')])
        order.action_complete()
        after = self.env['smi.activity.log'].search_count([('tipe', '=', 'order_selesai')])
        self.assertEqual(after, before + 1)

    def test_inventory_point_create_logs_titik_ditambah(self):
        """Creating inventory point auto-logs tipe='titik_ditambah'."""
        before = self.env['smi.activity.log'].search_count([('tipe', '=', 'titik_ditambah')])
        self.env['smi.inventory_point'].create(
            {'name': 'Titik Baru', 'koordinat_x': 50.0, 'koordinat_y': 50.0})
        after = self.env['smi.activity.log'].search_count([('tipe', '=', 'titik_ditambah')])
        self.assertEqual(after, before + 1)

    def test_activity_log_contains_correct_user(self):
        """activity_log.user_id matches the session user who performed the action."""
        self._add_stock(100.0)
        log = self.env['smi.activity.log'].search(
            [('tipe', '=', 'stok_masuk')], order='id desc', limit=1)
        self.assertEqual(log.user_id.id, self.env.uid)

    def test_activity_log_description_is_human_readable(self):
        """activity_log.deskripsi is a non-empty Indonesian string."""
        self._add_stock(100.0)
        log = self.env['smi.activity.log'].search(
            [('tipe', '=', 'stok_masuk')], order='id desc', limit=1)
        self.assertTrue(log.deskripsi)
        self.assertGreater(len(log.deskripsi), 5)


class TestLowStockNotification(_NotifBase):

    def test_low_stock_triggers_notification_flag(self):
        """When material.is_low_stock becomes True, notification_sent is set True."""
        # stok_minimum = 50; add 60, then order 30 → 30 left < 50 = low
        self._add_stock(60.0)
        order = self._make_order(30.0)
        order.action_confirm()
        self.material.invalidate_recordset()
        self.assertTrue(self.material.notification_sent)

    def test_low_stock_email_queued_for_kepala_produksi(self):
        """Low-stock condition queues email to all users in group_kepala_produksi."""
        self._add_stock(60.0)
        order = self._make_order(30.0)
        mail_before = self.env['mail.mail'].sudo().search_count([])
        order.action_confirm()
        mail_after = self.env['mail.mail'].sudo().search_count([])
        # At least one mail.mail record should have been created
        self.assertGreater(mail_after, mail_before)

    def test_no_duplicate_notification_if_still_low(self):
        """Second stock reduction on already-low material does not send another email."""
        self._add_stock(100.0)
        # First order: reduce to 60 (still above min of 50)
        order1 = self._make_order(40.0)
        order1.action_confirm()
        # Second order: reduce to 40 → triggers low stock + notification
        order2 = self._make_order(20.0)
        order2.action_confirm()
        self.material.invalidate_recordset()
        self.assertTrue(self.material.notification_sent)
        # Third order: still low stock → no duplicate email
        point2 = self.env['smi.inventory_point'].create(
            {'name': 'Rak-extra', 'koordinat_x': 70.0, 'koordinat_y': 70.0})
        self.env['smi.stock_entry'].create({
            'material_id': self.material.id,
            'inventory_point_id': point2.id,
            'jumlah_awal': 5.0,
            'tanggal_masuk': '2026-01-15 08:00:00',
        })
        order3 = self._make_order(5.0)
        mail_before = self.env['mail.mail'].sudo().search_count([])
        order3.action_confirm()
        mail_after = self.env['mail.mail'].sudo().search_count([])
        self.assertEqual(mail_before, mail_after, 'No second email should be queued')

    def test_notification_cleared_on_restock(self):
        """When stock is replenished above minimum, notification_sent resets to False."""
        # Trigger low-stock first
        self._add_stock(60.0)
        order = self._make_order(30.0)
        order.action_confirm()
        self.material.invalidate_recordset()
        self.assertTrue(self.material.notification_sent)
        # Restock: add enough to go above stok_minimum (50)
        self._add_stock(100.0, tanggal='2026-02-01 08:00:00')
        self.material.invalidate_recordset()
        self.assertFalse(self.material.notification_sent)
