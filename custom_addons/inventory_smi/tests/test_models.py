from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from psycopg2 import IntegrityError
from odoo.tools import mute_logger


class TestUoMModel(TransactionCase):

    def test_uom_create(self):
        uom = self.env['smi.uom'].create({'name': 'Lembar'})
        self.assertEqual(uom.name, 'Lembar')

    def test_uom_unique_name(self):
        self.env['smi.uom'].create({'name': 'Rim'})
        with mute_logger('odoo.sql_db'):
            with self.assertRaises(Exception):
                self.env['smi.uom'].create({'name': 'Rim'})


class TestMaterialCategoryModel(TransactionCase):

    def test_category_create(self):
        cat = self.env['smi.material.category'].create({'name': 'Kertas'})
        self.assertEqual(cat.name, 'Kertas')

    def test_category_unique_name(self):
        self.env['smi.material.category'].create({'name': 'Tinta'})
        with mute_logger('odoo.sql_db'):
            with self.assertRaises(Exception):
                self.env['smi.material.category'].create({'name': 'Tinta'})


class TestMaterialModel(TransactionCase):

    def setUp(self):
        super().setUp()
        self.uom = self.env['smi.uom'].create({'name': 'Lembar'})
        self.category = self.env['smi.material.category'].create({'name': 'Kertas'})

    def test_material_create_minimal(self):
        mat = self.env['smi.material'].create({
            'name': 'Kertas Art Paper 120gsm',
            'uom_id': self.uom.id,
            'category_id': self.category.id,
        })
        self.assertEqual(mat.name, 'Kertas Art Paper 120gsm')

    def test_material_requires_name(self):
        with self.assertRaises(Exception):
            self.env['smi.material'].create({
                'name': False,
                'uom_id': self.uom.id,
                'category_id': self.category.id,
            })

    def test_material_total_stok_computed_zero_on_create(self):
        mat = self.env['smi.material'].create({
            'name': 'Tinta Hitam',
            'uom_id': self.uom.id,
            'category_id': self.category.id,
        })
        self.assertEqual(mat.total_stok, 0.0)

    def test_material_is_low_stock_false_when_no_minimum(self):
        mat = self.env['smi.material'].create({
            'name': 'Tinta Merah',
            'uom_id': self.uom.id,
            'category_id': self.category.id,
            'stok_minimum': 0,
        })
        self.assertFalse(mat.is_low_stock)

    def test_material_notification_sent_defaults_false(self):
        mat = self.env['smi.material'].create({
            'name': 'Laminasi Doff',
            'uom_id': self.uom.id,
            'category_id': self.category.id,
        })
        self.assertFalse(mat.notification_sent)


class TestInventoryPointModel(TransactionCase):

    def test_point_create_with_coordinates(self):
        point = self.env['smi.inventory_point'].create({
            'name': 'Rak A1',
            'koordinat_x': 25.0,
            'koordinat_y': 50.0,
        })
        self.assertEqual(point.name, 'Rak A1')
        self.assertAlmostEqual(point.koordinat_x, 25.0)
        self.assertAlmostEqual(point.koordinat_y, 50.0)

    def test_point_coordinate_x_max_boundary(self):
        point = self.env['smi.inventory_point'].create({
            'name': 'Rak Max',
            'koordinat_x': 100.0,
            'koordinat_y': 100.0,
        })
        self.assertAlmostEqual(point.koordinat_x, 100.0)

    def test_point_coordinate_x_out_of_range(self):
        with self.assertRaises(ValidationError):
            self.env['smi.inventory_point'].create({
                'name': 'Invalid',
                'koordinat_x': 110.0,
                'koordinat_y': 50.0,
            })

    def test_point_coordinate_y_out_of_range(self):
        with self.assertRaises(ValidationError):
            self.env['smi.inventory_point'].create({
                'name': 'Invalid',
                'koordinat_x': 50.0,
                'koordinat_y': -5.0,
            })

    def test_point_coordinate_x_negative(self):
        with self.assertRaises(ValidationError):
            self.env['smi.inventory_point'].create({
                'name': 'Invalid',
                'koordinat_x': -1.0,
                'koordinat_y': 50.0,
            })


class TestStockEntryModel(TransactionCase):

    def setUp(self):
        super().setUp()
        self.uom = self.env['smi.uom'].create({'name': 'Rim'})
        self.category = self.env['smi.material.category'].create({'name': 'Kertas'})
        self.material = self.env['smi.material'].create({
            'name': 'Kertas HVS 80gsm',
            'uom_id': self.uom.id,
            'category_id': self.category.id,
        })
        self.point = self.env['smi.inventory_point'].create({
            'name': 'Rak B1',
            'koordinat_x': 30.0,
            'koordinat_y': 40.0,
        })

    def test_stock_entry_create(self):
        entry = self.env['smi.stock_entry'].create({
            'material_id': self.material.id,
            'inventory_point_id': self.point.id,
            'jumlah_awal': 100.0,
        })
        self.assertEqual(entry.material_id, self.material)
        self.assertEqual(entry.inventory_point_id, self.point)

    def test_stock_entry_state_defaults_to_tersedia(self):
        entry = self.env['smi.stock_entry'].create({
            'material_id': self.material.id,
            'inventory_point_id': self.point.id,
            'jumlah_awal': 50.0,
        })
        self.assertEqual(entry.state, 'tersedia')

    def test_stock_entry_jumlah_tersisa_equals_jumlah_awal_on_create(self):
        entry = self.env['smi.stock_entry'].create({
            'material_id': self.material.id,
            'inventory_point_id': self.point.id,
            'jumlah_awal': 75.0,
        })
        self.assertAlmostEqual(entry.jumlah_tersisa, 75.0)

    def test_stock_entry_jumlah_awal_must_be_positive(self):
        with self.assertRaises(ValidationError):
            self.env['smi.stock_entry'].create({
                'material_id': self.material.id,
                'inventory_point_id': self.point.id,
                'jumlah_awal': 0.0,
            })

    def test_stock_entry_jumlah_awal_negative_rejected(self):
        with self.assertRaises(ValidationError):
            self.env['smi.stock_entry'].create({
                'material_id': self.material.id,
                'inventory_point_id': self.point.id,
                'jumlah_awal': -10.0,
            })

    def test_stock_entry_jumlah_tersisa_cannot_be_negative(self):
        entry = self.env['smi.stock_entry'].create({
            'material_id': self.material.id,
            'inventory_point_id': self.point.id,
            'jumlah_awal': 50.0,
        })
        with self.assertRaises(ValidationError):
            entry.jumlah_tersisa = -1.0
            entry._check_jumlah_tersisa()

    def test_stock_entry_state_becomes_habis_when_tersisa_zero(self):
        entry = self.env['smi.stock_entry'].create({
            'material_id': self.material.id,
            'inventory_point_id': self.point.id,
            'jumlah_awal': 50.0,
        })
        entry.write({'jumlah_tersisa': 0.0})
        self.assertEqual(entry.state, 'habis')

    def test_material_total_stok_updates_after_entry_created(self):
        self.env['smi.stock_entry'].create({
            'material_id': self.material.id,
            'inventory_point_id': self.point.id,
            'jumlah_awal': 100.0,
        })
        self.assertAlmostEqual(self.material.total_stok, 100.0)

    def test_material_total_stok_sums_multiple_entries(self):
        point2 = self.env['smi.inventory_point'].create({
            'name': 'Rak C1',
            'koordinat_x': 60.0,
            'koordinat_y': 70.0,
        })
        self.env['smi.stock_entry'].create({
            'material_id': self.material.id,
            'inventory_point_id': self.point.id,
            'jumlah_awal': 40.0,
        })
        self.env['smi.stock_entry'].create({
            'material_id': self.material.id,
            'inventory_point_id': point2.id,
            'jumlah_awal': 60.0,
        })
        self.assertAlmostEqual(self.material.total_stok, 100.0)

    def test_material_total_stok_excludes_habis_entries(self):
        entry = self.env['smi.stock_entry'].create({
            'material_id': self.material.id,
            'inventory_point_id': self.point.id,
            'jumlah_awal': 50.0,
        })
        entry.write({'jumlah_tersisa': 0.0})
        self.assertAlmostEqual(self.material.total_stok, 0.0)

    def test_material_is_low_stock_true_when_below_minimum(self):
        self.material.stok_minimum = 100.0
        self.env['smi.stock_entry'].create({
            'material_id': self.material.id,
            'inventory_point_id': self.point.id,
            'jumlah_awal': 20.0,
        })
        self.assertTrue(self.material.is_low_stock)

    def test_material_is_low_stock_false_when_above_minimum(self):
        self.material.stok_minimum = 10.0
        self.env['smi.stock_entry'].create({
            'material_id': self.material.id,
            'inventory_point_id': self.point.id,
            'jumlah_awal': 50.0,
        })
        self.assertFalse(self.material.is_low_stock)

    def test_material_last_added_date_is_latest_entry(self):
        from datetime import datetime
        t1 = datetime(2026, 1, 1, 8, 0, 0)
        t2 = datetime(2026, 1, 10, 8, 0, 0)
        point2 = self.env['smi.inventory_point'].create({
            'name': 'Rak D1',
            'koordinat_x': 10.0,
            'koordinat_y': 10.0,
        })
        self.env['smi.stock_entry'].create({
            'material_id': self.material.id,
            'inventory_point_id': self.point.id,
            'jumlah_awal': 30.0,
            'tanggal_masuk': t1,
        })
        self.env['smi.stock_entry'].create({
            'material_id': self.material.id,
            'inventory_point_id': point2.id,
            'jumlah_awal': 20.0,
            'tanggal_masuk': t2,
        })
        self.assertEqual(self.material.last_added_date, t2)


class TestOrderModel(TransactionCase):

    def setUp(self):
        super().setUp()
        self.uom = self.env['smi.uom'].create({'name': 'Lembar'})
        self.category = self.env['smi.material.category'].create({'name': 'Kertas'})
        self.material = self.env['smi.material'].create({
            'name': 'Kertas Art Paper',
            'uom_id': self.uom.id,
            'category_id': self.category.id,
        })

    def test_order_create_draft(self):
        order = self.env['smi.order'].create({
            'name': 'Poster Kondangan',
            'no_spk': 'SPK-001',
        })
        self.assertEqual(order.state, 'draft')

    def test_order_line_create(self):
        order = self.env['smi.order'].create({
            'name': 'Brosur Event',
            'no_spk': 'SPK-002',
        })
        line = self.env['smi.order.line'].create({
            'order_id': order.id,
            'material_id': self.material.id,
            'jumlah_dibutuhkan': 100.0,
        })
        self.assertEqual(line.order_id, order)
        self.assertEqual(line.material_id, self.material)
        self.assertAlmostEqual(line.jumlah_dibutuhkan, 100.0)

    def test_order_line_jumlah_terpenuhi_defaults_zero(self):
        order = self.env['smi.order'].create({
            'name': 'Kartu Nama',
            'no_spk': 'SPK-003',
        })
        line = self.env['smi.order.line'].create({
            'order_id': order.id,
            'material_id': self.material.id,
            'jumlah_dibutuhkan': 50.0,
        })
        self.assertAlmostEqual(line.jumlah_terpenuhi, 0.0)

    def test_order_line_mode_pick_defaults_auto(self):
        order = self.env['smi.order'].create({
            'name': 'Kalender',
            'no_spk': 'SPK-004',
        })
        line = self.env['smi.order.line'].create({
            'order_id': order.id,
            'material_id': self.material.id,
            'jumlah_dibutuhkan': 200.0,
        })
        self.assertEqual(line.mode_pick, 'auto')


class TestActivityLogModel(TransactionCase):

    def test_activity_log_create_manual(self):
        log = self.env['smi.activity.log'].create({
            'tipe': 'stok_masuk',
            'deskripsi': 'Test log entry',
        })
        self.assertEqual(log.tipe, 'stok_masuk')
        self.assertEqual(log.deskripsi, 'Test log entry')

    def test_activity_log_defaults(self):
        log = self.env['smi.activity.log'].create({
            'tipe': 'order_dibuat',
            'deskripsi': 'Membuat order test',
        })
        self.assertIsNotNone(log.tanggal)
        self.assertEqual(log.user_id, self.env.user)


class TestSecurityGroups(TransactionCase):

    def test_group_admin_exists(self):
        group = self.env.ref('inventory_smi.group_admin', raise_if_not_found=False)
        self.assertIsNotNone(group)

    def test_group_kepala_produksi_exists(self):
        group = self.env.ref('inventory_smi.group_kepala_produksi', raise_if_not_found=False)
        self.assertIsNotNone(group)

    def test_group_staf_produksi_exists(self):
        group = self.env.ref('inventory_smi.group_staf_produksi', raise_if_not_found=False)
        self.assertIsNotNone(group)

    def test_group_direktur_exists(self):
        group = self.env.ref('inventory_smi.group_direktur', raise_if_not_found=False)
        self.assertIsNotNone(group)
