from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class _StockBase(TransactionCase):
    """Shared helpers for stock tests."""

    def setUp(self):
        super().setUp()
        self.uom = self.env['smi.uom'].create({'name': 'Lembar-stock'})
        self.cat = self.env['smi.material.category'].create({'name': 'Kertas-stock'})
        self.material = self.env['smi.material'].create({
            'name': 'Kertas Art Paper 120gsm',
            'uom_id': self.uom.id,
            'category_id': self.cat.id,
        })
        self.point_a = self.env['smi.inventory_point'].create({
            'name': 'Titik A1', 'koordinat_x': 10.0, 'koordinat_y': 20.0,
        })
        self.point_b = self.env['smi.inventory_point'].create({
            'name': 'Titik B2', 'koordinat_x': 50.0, 'koordinat_y': 60.0,
        })


class TestMaterialComputedFields(_StockBase):

    def test_total_stok_sums_all_entries(self):
        """total_stok = sum of jumlah_tersisa across all inventory points."""
        self.env['smi.stock_entry'].create([
            {'material_id': self.material.id, 'inventory_point_id': self.point_a.id,
             'jumlah_awal': 50.0, 'tanggal_masuk': '2026-01-01 08:00:00'},
            {'material_id': self.material.id, 'inventory_point_id': self.point_b.id,
             'jumlah_awal': 30.0, 'tanggal_masuk': '2026-01-05 08:00:00'},
        ])
        self.assertEqual(self.material.total_stok, 80.0)

    def test_total_stok_excludes_habis_entries(self):
        """state='habis' entries are excluded from total_stok."""
        entry = self.env['smi.stock_entry'].create({
            'material_id': self.material.id, 'inventory_point_id': self.point_a.id,
            'jumlah_awal': 50.0, 'jumlah_tersisa': 0.0, 'state': 'habis',
            'tanggal_masuk': '2026-01-01 08:00:00',
        })
        self.assertEqual(self.material.total_stok, 0.0)

    def test_is_low_stock_true_when_below_minimum(self):
        """is_low_stock=True when total_stok < stok_minimum."""
        self.material.stok_minimum = 100.0
        self.env['smi.stock_entry'].create({
            'material_id': self.material.id, 'inventory_point_id': self.point_a.id,
            'jumlah_awal': 40.0, 'tanggal_masuk': '2026-01-01 08:00:00',
        })
        self.assertTrue(self.material.is_low_stock)

    def test_is_low_stock_false_when_above_minimum(self):
        """is_low_stock=False when total_stok >= stok_minimum."""
        self.material.stok_minimum = 30.0
        self.env['smi.stock_entry'].create({
            'material_id': self.material.id, 'inventory_point_id': self.point_a.id,
            'jumlah_awal': 50.0, 'tanggal_masuk': '2026-01-01 08:00:00',
        })
        self.assertFalse(self.material.is_low_stock)

    def test_is_low_stock_false_when_minimum_is_zero(self):
        """is_low_stock=False when stok_minimum=0 regardless of stock."""
        self.material.stok_minimum = 0.0
        self.env['smi.stock_entry'].create({
            'material_id': self.material.id, 'inventory_point_id': self.point_a.id,
            'jumlah_awal': 1.0, 'tanggal_masuk': '2026-01-01 08:00:00',
        })
        self.assertFalse(self.material.is_low_stock)

    def test_last_added_date_is_latest_entry(self):
        """last_added_date = max(tanggal_masuk) among active entries."""
        self.env['smi.stock_entry'].create([
            {'material_id': self.material.id, 'inventory_point_id': self.point_a.id,
             'jumlah_awal': 10.0, 'tanggal_masuk': '2026-01-01 08:00:00'},
            {'material_id': self.material.id, 'inventory_point_id': self.point_b.id,
             'jumlah_awal': 10.0, 'tanggal_masuk': '2026-01-10 08:00:00'},
        ])
        expected = fields.Datetime.from_string('2026-01-10 08:00:00')
        self.assertEqual(self.material.last_added_date, expected)


class TestStockEntryConstraints(_StockBase):

    def test_jumlah_awal_must_be_positive(self):
        """jumlah_awal <= 0 raises ValidationError."""
        with self.assertRaises(ValidationError):
            self.env['smi.stock_entry'].create({
                'material_id': self.material.id, 'inventory_point_id': self.point_a.id,
                'jumlah_awal': 0.0, 'tanggal_masuk': '2026-01-01 08:00:00',
            })

    def test_jumlah_tersisa_cannot_exceed_jumlah_awal(self):
        """jumlah_tersisa > jumlah_awal raises ValidationError."""
        entry = self.env['smi.stock_entry'].create({
            'material_id': self.material.id, 'inventory_point_id': self.point_a.id,
            'jumlah_awal': 50.0, 'tanggal_masuk': '2026-01-01 08:00:00',
        })
        with self.assertRaises(ValidationError):
            entry.jumlah_tersisa = 99.0
            entry._check_jumlah_tersisa()

    def test_jumlah_tersisa_cannot_be_negative(self):
        """jumlah_tersisa < 0 raises ValidationError."""
        entry = self.env['smi.stock_entry'].create({
            'material_id': self.material.id, 'inventory_point_id': self.point_a.id,
            'jumlah_awal': 50.0, 'tanggal_masuk': '2026-01-01 08:00:00',
        })
        with self.assertRaises(ValidationError):
            entry.write({'jumlah_tersisa': -1.0})

    def test_state_becomes_habis_when_tersisa_zero(self):
        """state auto-set to 'habis' when jumlah_tersisa set to 0."""
        entry = self.env['smi.stock_entry'].create({
            'material_id': self.material.id, 'inventory_point_id': self.point_a.id,
            'jumlah_awal': 50.0, 'tanggal_masuk': '2026-01-01 08:00:00',
        })
        entry.write({'jumlah_tersisa': 0.0})
        self.assertEqual(entry.state, 'habis')


class TestInventoryPointConstraints(_StockBase):

    def test_x_coordinate_must_be_0_to_100(self):
        """koordinat_x outside 0–100 raises ValidationError."""
        with self.assertRaises(ValidationError):
            self.env['smi.inventory_point'].create({
                'name': 'Invalid X', 'koordinat_x': 150.0, 'koordinat_y': 50.0,
            })

    def test_y_coordinate_must_be_0_to_100(self):
        """koordinat_y outside 0–100 raises ValidationError."""
        with self.assertRaises(ValidationError):
            self.env['smi.inventory_point'].create({
                'name': 'Invalid Y', 'koordinat_x': 50.0, 'koordinat_y': -5.0,
            })


class TestUoMUniqueness(TransactionCase):

    def test_duplicate_uom_name_raises_error(self):
        """Creating two smi.uom with same name raises error."""
        self.env['smi.uom'].create({'name': 'Unik-UoM-Test'})
        raised = False
        try:
            self.env['smi.uom'].create({'name': 'Unik-UoM-Test'})
            self.env.flush_all()
        except Exception:
            raised = True
        self.assertTrue(raised, 'Expected an error for duplicate UoM name')


class TestCategoryUniqueness(TransactionCase):

    def test_duplicate_category_name_raises_error(self):
        """Creating two smi.material.category with same name raises error."""
        self.env['smi.material.category'].create({'name': 'Unik-Cat-Test'})
        raised = False
        try:
            self.env['smi.material.category'].create({'name': 'Unik-Cat-Test'})
            self.env.flush_all()
        except Exception:
            raised = True
        self.assertTrue(raised, 'Expected an error for duplicate category name')
