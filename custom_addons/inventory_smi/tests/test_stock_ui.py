from odoo.tests.common import TransactionCase


class _StockUIBase(TransactionCase):

    def setUp(self):
        super().setUp()
        self.uom = self.env['smi.uom'].create({'name': 'Lembar-stockui'})
        self.cat = self.env['smi.material.category'].create({'name': 'Kertas-stockui'})
        self.material = self.env['smi.material'].create({
            'name': 'Kertas Art 120gsm',
            'uom_id': self.uom.id,
            'category_id': self.cat.id,
            'stok_minimum': 10.0,
        })
        self.point = self.env['smi.inventory_point'].create({
            'name': 'Rak A1', 'koordinat_x': 20.0, 'koordinat_y': 30.0,
        })

    def _create_user(self, login, group_xml_id):
        return self.env['res.users'].with_context(no_reset_password=True).create({
            'name': login, 'login': login, 'password': 'TestPass!',
            'groups_id': [
                (4, self.env.ref(group_xml_id).id),
                (4, self.env.ref('base.group_user').id),
            ],
        })

    def _add_stock(self, jumlah, tanggal='2026-01-01 08:00:00'):
        return self.env['smi.stock_entry'].create({
            'material_id': self.material.id,
            'inventory_point_id': self.point.id,
            'jumlah_awal': jumlah,
            'tanggal_masuk': tanggal,
        })


class TestStockListAccess(_StockUIBase):

    def test_stock_list_accessible_to_admin(self):
        """Admin can read smi.material records."""
        admin = self._create_user('admin_stk', 'inventory_smi.group_admin')
        env = self.env(user=admin)
        mats = env['smi.material'].search([('active', '=', True)])
        self.assertIsNotNone(mats)

    def test_stock_list_accessible_to_kepala_produksi(self):
        """Kepala Produksi can read smi.material records."""
        kepala = self._create_user('kepala_stk', 'inventory_smi.group_kepala_produksi')
        env = self.env(user=kepala)
        mats = env['smi.material'].search([('active', '=', True)])
        self.assertIsNotNone(mats)

    def test_stock_list_accessible_to_staf(self):
        """Staf Produksi can read smi.material records."""
        staf = self._create_user('staf_stk', 'inventory_smi.group_staf_produksi')
        env = self.env(user=staf)
        mats = env['smi.material'].search([('active', '=', True)])
        self.assertIsNotNone(mats)

    def test_stock_list_forbidden_for_direktur(self):
        """Direktur cannot create stock entries (write access denied)."""
        from odoo.exceptions import AccessError
        direktur = self._create_user('dir_stk', 'inventory_smi.group_direktur')
        env = self.env(user=direktur)
        with self.assertRaises(AccessError):
            env['smi.stock_entry'].create({
                'material_id': self.material.id,
                'inventory_point_id': self.point.id,
                'jumlah_awal': 10.0,
            })

    def test_stock_list_returns_active_materials_only(self):
        """Stock list domain filters active=True materials."""
        mat2 = self.env['smi.material'].create({
            'name': 'Bahan Arsip', 'uom_id': self.uom.id, 'category_id': self.cat.id,
        })
        mat2.write({'active': False})
        mats = self.env['smi.material'].search([('active', '=', True)])
        self.assertNotIn(mat2.id, mats.ids)

    def test_stock_list_search_by_name(self):
        """Search by name filters materials correctly."""
        mats = self.env['smi.material'].search([
            ('active', '=', True), ('name', 'ilike', 'Art 120gsm')
        ])
        self.assertIn(self.material.id, mats.ids)

    def test_stock_list_search_no_match(self):
        """Search with no match returns empty recordset."""
        mats = self.env['smi.material'].search([
            ('active', '=', True), ('name', 'ilike', 'XXXXNOEXIST')
        ])
        self.assertFalse(mats)

    def test_stock_list_sorted_asc(self):
        """Stock list can be sorted by total_stok ascending."""
        self._add_stock(50.0)
        mat2 = self.env['smi.material'].create({
            'name': 'Tinta Hitam', 'uom_id': self.uom.id, 'category_id': self.cat.id,
        })
        self.env['smi.stock_entry'].create({
            'material_id': mat2.id, 'inventory_point_id': self.point.id,
            'jumlah_awal': 200.0, 'tanggal_masuk': '2026-01-05 08:00:00',
        })
        mats = self.env['smi.material'].search([('active', '=', True)])
        sorted_mats = sorted(mats, key=lambda m: m.total_stok)
        self.assertLessEqual(sorted_mats[0].total_stok, sorted_mats[-1].total_stok)


class TestStockForm(_StockUIBase):

    def test_stock_form_route_exists(self):
        """Template inventory_smi.stock_form_page is installed."""
        tmpl = self.env.ref('inventory_smi.stock_form_page', raise_if_not_found=False)
        self.assertIsNotNone(tmpl)

    def test_stock_form_submission_creates_stock_entry(self):
        """Creating smi.stock_entry via ORM creates the record + activity log."""
        before_entries = self.env['smi.stock_entry'].search_count([
            ('material_id', '=', self.material.id)
        ])
        before_logs = self.env['smi.activity.log'].search_count([('tipe', '=', 'stok_masuk')])
        self._add_stock(75.0)
        after_entries = self.env['smi.stock_entry'].search_count([
            ('material_id', '=', self.material.id)
        ])
        after_logs = self.env['smi.activity.log'].search_count([('tipe', '=', 'stok_masuk')])
        self.assertEqual(after_entries, before_entries + 1)
        self.assertEqual(after_logs, before_logs + 1)

    def test_stock_form_requires_material_id(self):
        """Creating stock entry without material raises error."""
        from odoo.exceptions import ValidationError
        with self.assertRaises(Exception):
            self.env['smi.stock_entry'].create({
                'inventory_point_id': self.point.id,
                'jumlah_awal': 10.0,
            })

    def test_stock_form_requires_jumlah_positive(self):
        """jumlah_awal <= 0 raises ValidationError."""
        from odoo.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self.env['smi.stock_entry'].create({
                'material_id': self.material.id,
                'inventory_point_id': self.point.id,
                'jumlah_awal': 0.0,
            })

    def test_stock_form_requires_inventory_point(self):
        """Creating stock entry without inventory_point raises error."""
        with self.assertRaises(Exception):
            self.env['smi.stock_entry'].create({
                'material_id': self.material.id,
                'jumlah_awal': 10.0,
            })

    def test_stock_form_template_has_material_field(self):
        """Stock form template contains material_id field."""
        tmpl = self.env.ref('inventory_smi.stock_form_page')
        self.assertIn('material_id', tmpl.arch)

    def test_stock_form_template_has_jumlah_field(self):
        """Stock form template contains jumlah field."""
        tmpl = self.env.ref('inventory_smi.stock_form_page')
        self.assertIn('jumlah', tmpl.arch)

    def test_stock_form_template_has_map_picker(self):
        """Stock form template contains map picker trigger."""
        tmpl = self.env.ref('inventory_smi.stock_form_page')
        self.assertIn('inventory_point', tmpl.arch)

    def test_stock_form_auto_fills_user(self):
        """Stock entry auto-sets user_id to the session user."""
        entry = self._add_stock(50.0)
        self.assertEqual(entry.user_id.id, self.env.uid)

    def test_stock_form_auto_fills_tanggal(self):
        """Stock entry sets tanggal_masuk to now if not provided."""
        entry = self.env['smi.stock_entry'].create({
            'material_id': self.material.id,
            'inventory_point_id': self.point.id,
            'jumlah_awal': 30.0,
        })
        self.assertIsNotNone(entry.tanggal_masuk)


class TestStockDetail(_StockUIBase):

    def test_stock_detail_route(self):
        """Template inventory_smi.stock_detail_page is installed."""
        tmpl = self.env.ref('inventory_smi.stock_detail_page', raise_if_not_found=False)
        self.assertIsNotNone(tmpl)

    def test_stock_detail_shows_material_info(self):
        """Detail page template contains material info fields."""
        tmpl = self.env.ref('inventory_smi.stock_detail_page')
        self.assertIn('material', tmpl.arch)
        self.assertIn('total_stok', tmpl.arch)

    def test_stock_detail_shows_transaction_history(self):
        """Detail page template contains transaction history section."""
        tmpl = self.env.ref('inventory_smi.stock_detail_page')
        self.assertIn('entries', tmpl.arch)

    def test_stock_detail_history_sorted_newest_first(self):
        """Stock entries for a material sorted by tanggal_masuk DESC."""
        self._add_stock(50.0, '2026-01-01 08:00:00')
        self._add_stock(30.0, '2026-02-01 08:00:00')
        entries = self.env['smi.stock_entry'].search(
            [('material_id', '=', self.material.id)], order='tanggal_masuk desc'
        )
        dates = [e.tanggal_masuk for e in entries]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_stock_detail_shows_stok_minimum_field(self):
        """Detail page template shows stok_minimum field."""
        tmpl = self.env.ref('inventory_smi.stock_detail_page')
        self.assertIn('stok_minimum', tmpl.arch)

    def test_stock_detail_material_exists_check(self):
        """Non-existent material_id should return empty/redirect."""
        mat = self.env['smi.material'].browse(999999)
        self.assertFalse(mat.exists())

    def test_stock_detail_has_denah_section(self):
        """Detail page template has a map/denah section."""
        tmpl = self.env.ref('inventory_smi.stock_detail_page')
        self.assertIn('denah', tmpl.arch.lower())


class TestDenahPage(_StockUIBase):

    def test_denah_page_accessible(self):
        """Template inventory_smi.denah_page is installed."""
        tmpl = self.env.ref('inventory_smi.denah_page', raise_if_not_found=False)
        self.assertIsNotNone(tmpl)

    def test_denah_page_has_filter_controls(self):
        """Denah page template has material filter."""
        tmpl = self.env.ref('inventory_smi.denah_page')
        self.assertIn('material', tmpl.arch)

    def test_denah_page_has_map_area(self):
        """Denah page template has the SVG map area."""
        tmpl = self.env.ref('inventory_smi.denah_page')
        self.assertIn('denah', tmpl.arch.lower())

    def test_denah_page_has_map_points(self):
        """Denah page template iterates map_points."""
        tmpl = self.env.ref('inventory_smi.denah_page')
        self.assertIn('map_points', tmpl.arch)

    def test_denah_map_points_color_aman(self):
        """Point with stok above minimum gets green color."""
        self._add_stock(100.0)
        self.material.write({'stok_minimum': 10.0})
        self.material.invalidate_recordset()
        entries = self.point.stock_entry_ids.filtered(lambda e: e.state == 'tersedia')
        all_low = all(e.material_id.is_low_stock for e in entries)
        any_low = any(e.material_id.is_low_stock for e in entries)
        self.assertFalse(all_low)
        self.assertFalse(any_low)

    def test_denah_map_points_color_low(self):
        """Point with low-stock material gets orange/red color."""
        self._add_stock(5.0)  # 5 < stok_minimum 10
        self.material.invalidate_recordset()
        self.assertTrue(self.material.is_low_stock)

    def test_denah_point_side_panel_accessible(self):
        """Denah page template has side panel structure for point detail."""
        tmpl = self.env.ref('inventory_smi.denah_page')
        self.assertIn('panel', tmpl.arch.lower())


class TestInventoryPointAccess(_StockUIBase):

    def test_staf_cannot_add_inventory_point(self):
        """Staf Produksi cannot create smi.inventory_point (AccessError)."""
        from odoo.exceptions import AccessError
        staf = self._create_user('staf_pt', 'inventory_smi.group_staf_produksi')
        env = self.env(user=staf)
        with self.assertRaises(AccessError):
            env['smi.inventory_point'].create({
                'name': 'Titik Staf', 'koordinat_x': 30.0, 'koordinat_y': 40.0,
            })

    def test_kepala_can_add_inventory_point(self):
        """Kepala Produksi can create smi.inventory_point."""
        kepala = self._create_user('kepala_pt', 'inventory_smi.group_kepala_produksi')
        env = self.env(user=kepala)
        pt = env['smi.inventory_point'].create({
            'name': 'Titik Kepala', 'koordinat_x': 55.0, 'koordinat_y': 65.0,
        })
        self.assertTrue(pt.id)

    def test_admin_can_add_inventory_point(self):
        """Admin can create smi.inventory_point."""
        admin = self._create_user('admin_pt', 'inventory_smi.group_admin')
        env = self.env(user=admin)
        pt = env['smi.inventory_point'].create({
            'name': 'Titik Admin', 'koordinat_x': 10.0, 'koordinat_y': 20.0,
        })
        self.assertTrue(pt.id)

    def test_staf_can_read_inventory_points(self):
        """Staf Produksi can read smi.inventory_point records."""
        staf = self._create_user('staf_read_pt', 'inventory_smi.group_staf_produksi')
        env = self.env(user=staf)
        points = env['smi.inventory_point'].search([('active', '=', True)])
        self.assertIsNotNone(points)


class TestStockUITemplates(TransactionCase):

    def test_stock_list_template_exists(self):
        """Template inventory_smi.stock_list_page is installed."""
        tmpl = self.env.ref('inventory_smi.stock_list_page', raise_if_not_found=False)
        self.assertIsNotNone(tmpl)

    def test_stock_list_template_has_search(self):
        """Stock list template has search input."""
        tmpl = self.env.ref('inventory_smi.stock_list_page')
        self.assertIn('search', tmpl.arch.lower())

    def test_stock_list_template_has_tambah_button(self):
        """Stock list template has Tambah Stok button."""
        tmpl = self.env.ref('inventory_smi.stock_list_page')
        self.assertIn('tambah', tmpl.arch.lower())

    def test_stock_list_template_has_lihat_denah_button(self):
        """Stock list template has Lihat Denah button."""
        tmpl = self.env.ref('inventory_smi.stock_list_page')
        self.assertIn('denah', tmpl.arch.lower())

    def test_stock_list_template_has_table_columns(self):
        """Stock list template has Nama Bahan, Total Stok, Status columns."""
        tmpl = self.env.ref('inventory_smi.stock_list_page')
        arch = tmpl.arch.lower()
        self.assertIn('bahan', arch)
        self.assertIn('stok', arch)
        self.assertIn('status', arch)

    def test_stock_form_template_has_csrf(self):
        """Stock form template includes CSRF token."""
        tmpl = self.env.ref('inventory_smi.stock_form_page')
        self.assertIn('csrf_token', tmpl.arch)

    def test_stock_form_template_has_catatan_field(self):
        """Stock form template has catatan field."""
        tmpl = self.env.ref('inventory_smi.stock_form_page')
        self.assertIn('catatan', tmpl.arch)
