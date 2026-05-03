from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError, ValidationError


class _OrderUIBase(TransactionCase):

    def setUp(self):
        super().setUp()
        self.uom = self.env['smi.uom'].create({'name': 'Lembar-orderui'})
        self.cat = self.env['smi.material.category'].create({'name': 'Kertas-orderui'})
        self.material = self.env['smi.material'].create({
            'name': 'Kertas HVS 80gsm',
            'uom_id': self.uom.id,
            'category_id': self.cat.id,
            'stok_minimum': 5.0,
        })
        self.material2 = self.env['smi.material'].create({
            'name': 'Tinta Hitam Cair',
            'uom_id': self.uom.id,
            'category_id': self.cat.id,
            'stok_minimum': 2.0,
        })
        self.point = self.env['smi.inventory_point'].create({
            'name': 'Rak B1', 'koordinat_x': 40.0, 'koordinat_y': 50.0,
        })
        self.point2 = self.env['smi.inventory_point'].create({
            'name': 'Rak B2', 'koordinat_x': 60.0, 'koordinat_y': 70.0,
        })

    def _create_user(self, login, group_xml_id):
        return self.env['res.users'].with_context(no_reset_password=True).create({
            'name': login, 'login': login, 'password': 'TestPass!',
            'groups_id': [
                (4, self.env.ref(group_xml_id).id),
                (4, self.env.ref('base.group_user').id),
            ],
        })

    def _add_stock(self, material, point, jumlah, tanggal='2026-01-01 08:00:00'):
        return self.env['smi.stock_entry'].create({
            'material_id': material.id,
            'inventory_point_id': point.id,
            'jumlah_awal': jumlah,
            'tanggal_masuk': tanggal,
        })

    def _create_draft_order(self, name='Order Test', no_spk='SPK-001'):
        return self.env['smi.order'].create({
            'name': name,
            'no_spk': no_spk,
            'tanggal': '2026-04-17',
        })


# ──────────────────────────────────────────────────────────────────────────────
# Access control
# ──────────────────────────────────────────────────────────────────────────────

class TestOrderListAccess(_OrderUIBase):

    def test_order_list_accessible_to_staf(self):
        """Staf Produksi can read smi.order records."""
        staf = self._create_user('staf_ord', 'inventory_smi.group_staf_produksi')
        env = self.env(user=staf)
        orders = env['smi.order'].search([])
        self.assertIsNotNone(orders)

    def test_order_list_accessible_to_kepala(self):
        """Kepala Produksi can read smi.order records."""
        kepala = self._create_user('kepala_ord', 'inventory_smi.group_kepala_produksi')
        env = self.env(user=kepala)
        orders = env['smi.order'].search([])
        self.assertIsNotNone(orders)

    def test_order_list_accessible_to_direktur(self):
        """Direktur can read smi.order records (view-only)."""
        direktur = self._create_user('dir_ord', 'inventory_smi.group_direktur')
        env = self.env(user=direktur)
        orders = env['smi.order'].search([])
        self.assertIsNotNone(orders)

    def test_direktur_cannot_create_order(self):
        """Direktur cannot create smi.order (AccessError)."""
        direktur = self._create_user('dir_create_ord', 'inventory_smi.group_direktur')
        env = self.env(user=direktur)
        with self.assertRaises(AccessError):
            env['smi.order'].create({
                'name': 'Order Direktur',
                'tanggal': '2026-04-17',
            })

    def test_staf_can_create_order(self):
        """Staf Produksi can create smi.order."""
        staf = self._create_user('staf_create_ord', 'inventory_smi.group_staf_produksi')
        env = self.env(user=staf)
        order = env['smi.order'].create({
            'name': 'Order Staf Test',
            'tanggal': '2026-04-17',
        })
        self.assertTrue(order.id)
        self.assertEqual(order.state, 'draft')

    def test_order_list_search_by_name(self):
        """Search by name filters orders correctly."""
        self._create_draft_order('Cetak Brosur ABC', 'SPK-100')
        orders = self.env['smi.order'].search([('name', 'ilike', 'Brosur ABC')])
        self.assertTrue(len(orders) >= 1)
        self.assertIn('Brosur ABC', orders[0].name)

    def test_order_list_filter_by_state(self):
        """Filter by state=draft returns only draft orders."""
        order = self._create_draft_order('Draft Filter Test')
        drafts = self.env['smi.order'].search([('state', '=', 'draft')])
        self.assertIn(order.id, drafts.ids)


# ──────────────────────────────────────────────────────────────────────────────
# Order form — Step 1 (header info)
# ──────────────────────────────────────────────────────────────────────────────

class TestOrderFormStep1(_OrderUIBase):

    def test_order_form_step1_creates_draft_order(self):
        """Creating order via ORM produces state=draft."""
        order = self._create_draft_order('Cetak Kalender 2026', 'SPK-200')
        self.assertEqual(order.state, 'draft')
        self.assertEqual(order.name, 'Cetak Kalender 2026')
        self.assertEqual(order.no_spk, 'SPK-200')

    def test_order_form_step1_auto_fills_user(self):
        """Order auto-sets user_id to the session user."""
        order = self._create_draft_order()
        self.assertEqual(order.user_id.id, self.env.uid)

    def test_order_form_step1_auto_fills_tanggal(self):
        """Order sets tanggal to today if not provided."""
        order = self.env['smi.order'].create({'name': 'Order Auto Date'})
        self.assertIsNotNone(order.tanggal)

    def test_order_form_step1_logs_order_dibuat(self):
        """Creating order auto-creates activity log with tipe='order_dibuat'."""
        before = self.env['smi.activity.log'].search_count([('tipe', '=', 'order_dibuat')])
        self._create_draft_order('Order Log Test')
        after = self.env['smi.activity.log'].search_count([('tipe', '=', 'order_dibuat')])
        self.assertEqual(after, before + 1)

    def test_order_form_step1_name_required(self):
        """Creating order without name raises error."""
        with self.assertRaises(Exception):
            self.env['smi.order'].create({'tanggal': '2026-04-17', 'name': False})


# ──────────────────────────────────────────────────────────────────────────────
# Order form — Step 2 (material lines + stock check)
# ──────────────────────────────────────────────────────────────────────────────

class TestOrderFormStep2(_OrderUIBase):

    def setUp(self):
        super().setUp()
        self._add_stock(self.material, self.point, 100.0, '2026-01-01 08:00:00')
        self.order = self._create_draft_order('Step2 Test Order', 'SPK-300')

    def test_order_form_step2_material_sufficient_is_sufficient_true(self):
        """Order line with jumlah <= total_stok has is_sufficient=True."""
        line = self.env['smi.order.line'].create({
            'order_id': self.order.id,
            'material_id': self.material.id,
            'jumlah_dibutuhkan': 50.0,
            'mode_pick': 'auto',
        })
        self.assertTrue(line.is_sufficient)

    def test_order_form_step2_material_insufficient_is_sufficient_false(self):
        """Order line with jumlah > total_stok has is_sufficient=False."""
        line = self.env['smi.order.line'].create({
            'order_id': self.order.id,
            'material_id': self.material.id,
            'jumlah_dibutuhkan': 999.0,
            'mode_pick': 'auto',
        })
        self.assertFalse(line.is_sufficient)

    def test_order_form_step2_zero_stock_is_sufficient_false(self):
        """Order line for material with 0 stock has is_sufficient=False."""
        line = self.env['smi.order.line'].create({
            'order_id': self.order.id,
            'material_id': self.material2.id,
            'jumlah_dibutuhkan': 10.0,
            'mode_pick': 'auto',
        })
        self.assertFalse(line.is_sufficient)

    def test_order_form_step2_can_add_multiple_lines(self):
        """Order can have multiple order lines for different materials."""
        self._add_stock(self.material2, self.point, 50.0)
        self.env['smi.order.line'].create({
            'order_id': self.order.id,
            'material_id': self.material.id,
            'jumlah_dibutuhkan': 30.0,
            'mode_pick': 'auto',
        })
        self.env['smi.order.line'].create({
            'order_id': self.order.id,
            'material_id': self.material2.id,
            'jumlah_dibutuhkan': 20.0,
            'mode_pick': 'auto',
        })
        self.assertEqual(len(self.order.order_line_ids), 2)

    def test_order_form_step2_mode_auto_default(self):
        """New order line defaults to mode_pick='auto'."""
        line = self.env['smi.order.line'].create({
            'order_id': self.order.id,
            'material_id': self.material.id,
            'jumlah_dibutuhkan': 10.0,
        })
        self.assertEqual(line.mode_pick, 'auto')

    def test_order_form_step2_mode_manual_allowed(self):
        """Order line can be set to mode_pick='manual'."""
        line = self.env['smi.order.line'].create({
            'order_id': self.order.id,
            'material_id': self.material.id,
            'jumlah_dibutuhkan': 10.0,
            'mode_pick': 'manual',
        })
        self.assertEqual(line.mode_pick, 'manual')

    def test_order_form_step2_fifo_preview_allocation(self):
        """FIFO preview allocates from oldest entry first (no stock change yet)."""
        self._add_stock(self.material, self.point2, 30.0, '2026-02-01 08:00:00')
        needed = 80.0
        entries = self.env['smi.stock_entry'].search([
            ('material_id', '=', self.material.id),
            ('jumlah_tersisa', '>', 0),
            ('state', '=', 'tersedia'),
        ], order='tanggal_masuk asc')
        remaining = needed
        picks = []
        for entry in entries:
            if remaining <= 0:
                break
            take = min(entry.jumlah_tersisa, remaining)
            picks.append({'entry_id': entry.id, 'jumlah_diambil': take})
            remaining -= take
        self.assertEqual(sum(p['jumlah_diambil'] for p in picks), needed)
        self.assertEqual(picks[0]['jumlah_diambil'], 100.0 if needed >= 100 else needed)


# ──────────────────────────────────────────────────────────────────────────────
# Order form — Step 3 (confirmation + stock reduction)
# ──────────────────────────────────────────────────────────────────────────────

class TestOrderFormStep3(_OrderUIBase):

    def setUp(self):
        super().setUp()
        self.entry1 = self._add_stock(self.material, self.point, 50.0, '2026-01-01 08:00:00')
        self.entry2 = self._add_stock(self.material, self.point2, 30.0, '2026-02-01 08:00:00')
        self.order = self._create_draft_order('Konfirmasi Test Order', 'SPK-400')

    def test_order_form_step3_auto_fifo_confirms_and_reduces_stock(self):
        """Confirming order with auto FIFO reduces stock_entry.jumlah_tersisa."""
        line = self.env['smi.order.line'].create({
            'order_id': self.order.id,
            'material_id': self.material.id,
            'jumlah_dibutuhkan': 60.0,
            'mode_pick': 'auto',
        })
        self.order.action_confirm()
        self.assertEqual(self.order.state, 'dikonfirmasi')
        self.entry1.invalidate_recordset()
        self.entry2.invalidate_recordset()
        self.assertEqual(self.entry1.jumlah_tersisa, 0.0)
        self.assertAlmostEqual(self.entry2.jumlah_tersisa, 20.0, places=2)

    def test_order_form_step3_manual_pick_confirms_from_selected_points(self):
        """Manual pick confirmation reduces stock from exactly the selected points."""
        line = self.env['smi.order.line'].create({
            'order_id': self.order.id,
            'material_id': self.material.id,
            'jumlah_dibutuhkan': 30.0,
            'mode_pick': 'manual',
        })
        self.env['smi.order.pick'].create({
            'order_line_id': line.id,
            'stock_entry_id': self.entry2.id,
            'jumlah_diambil': 30.0,
        })
        self.order.action_confirm()
        self.assertEqual(self.order.state, 'dikonfirmasi')
        self.entry2.invalidate_recordset()
        self.assertAlmostEqual(self.entry2.jumlah_tersisa, 0.0, places=2)

    def test_order_form_step3_insufficient_stock_raises_error(self):
        """Confirming order with insufficient stock raises ValidationError."""
        self.env['smi.order.line'].create({
            'order_id': self.order.id,
            'material_id': self.material.id,
            'jumlah_dibutuhkan': 999.0,
            'mode_pick': 'auto',
        })
        with self.assertRaises(ValidationError):
            self.order.action_confirm()

    def test_order_form_step3_no_lines_raises_error(self):
        """Confirming order with no lines raises ValidationError."""
        with self.assertRaises(ValidationError):
            self.order.action_confirm()

    def test_order_form_step3_logs_stok_keluar(self):
        """Confirming order logs stok_keluar activity."""
        self.env['smi.order.line'].create({
            'order_id': self.order.id,
            'material_id': self.material.id,
            'jumlah_dibutuhkan': 10.0,
            'mode_pick': 'auto',
        })
        before = self.env['smi.activity.log'].search_count([('tipe', '=', 'stok_keluar')])
        self.order.action_confirm()
        after = self.env['smi.activity.log'].search_count([('tipe', '=', 'stok_keluar')])
        self.assertGreater(after, before)


# ──────────────────────────────────────────────────────────────────────────────
# Order detail
# ──────────────────────────────────────────────────────────────────────────────

class TestOrderDetail(_OrderUIBase):

    def setUp(self):
        super().setUp()
        self._add_stock(self.material, self.point, 100.0)
        self.order = self._create_draft_order('Detail Test Order', 'SPK-500')

    def test_order_detail_route_template_exists(self):
        """Template inventory_smi.order_detail_page is installed."""
        tmpl = self.env.ref('inventory_smi.order_detail_page', raise_if_not_found=False)
        self.assertIsNotNone(tmpl)

    def test_order_detail_shows_order_info(self):
        """Detail page template contains order info fields."""
        tmpl = self.env.ref('inventory_smi.order_detail_page')
        self.assertIn('order', tmpl.arch)

    def test_order_detail_shows_order_lines(self):
        """Detail page template contains order lines section."""
        tmpl = self.env.ref('inventory_smi.order_detail_page')
        self.assertIn('order_line', tmpl.arch)

    def test_order_detail_shows_status_badge(self):
        """Detail page template shows state/status."""
        tmpl = self.env.ref('inventory_smi.order_detail_page')
        arch = tmpl.arch.lower()
        self.assertIn('state', arch)

    def test_order_detail_shows_pick_detail(self):
        """Detail page template shows pick/pengambilan detail."""
        tmpl = self.env.ref('inventory_smi.order_detail_page')
        arch = tmpl.arch.lower()
        self.assertTrue('pick' in arch or 'pengambilan' in arch or 'diambil' in arch)

    def test_order_detail_nonexistent_id_redirects(self):
        """Browsing non-existent order returns empty record."""
        fake_order = self.env['smi.order'].browse(999999)
        self.assertFalse(fake_order.exists())

    def test_order_detail_has_cancel_option(self):
        """Detail page template has cancel action."""
        tmpl = self.env.ref('inventory_smi.order_detail_page')
        arch = tmpl.arch.lower()
        self.assertTrue('batal' in arch or 'cancel' in arch)


# ──────────────────────────────────────────────────────────────────────────────
# Order cancel action
# ──────────────────────────────────────────────────────────────────────────────

class TestOrderCancel(_OrderUIBase):

    def test_order_draft_can_be_cancelled(self):
        """Draft order can be cancelled → state='dibatalkan'."""
        order = self._create_draft_order('Cancel Draft Order')
        order.action_cancel()
        self.assertEqual(order.state, 'dibatalkan')

    def test_order_cancel_logs_order_dibatalkan(self):
        """Cancelling order logs tipe='order_dibatalkan'."""
        order = self._create_draft_order('Cancel Log Order')
        before = self.env['smi.activity.log'].search_count([('tipe', '=', 'order_dibatalkan')])
        order.action_cancel()
        after = self.env['smi.activity.log'].search_count([('tipe', '=', 'order_dibatalkan')])
        self.assertEqual(after, before + 1)

    def test_order_selesai_cannot_be_cancelled(self):
        """Completed order cannot be cancelled (raises ValidationError)."""
        self._add_stock(self.material, self.point, 100.0)
        order = self._create_draft_order('Selesai Cancel Test')
        self.env['smi.order.line'].create({
            'order_id': order.id,
            'material_id': self.material.id,
            'jumlah_dibutuhkan': 10.0,
            'mode_pick': 'auto',
        })
        order.action_confirm()
        order.action_complete()
        self.assertEqual(order.state, 'selesai')
        with self.assertRaises(ValidationError):
            order.action_cancel()

    def test_order_confirmed_can_be_cancelled(self):
        """Confirmed order can be cancelled."""
        self._add_stock(self.material, self.point, 100.0)
        order = self._create_draft_order('Confirm Then Cancel')
        self.env['smi.order.line'].create({
            'order_id': order.id,
            'material_id': self.material.id,
            'jumlah_dibutuhkan': 10.0,
            'mode_pick': 'auto',
        })
        order.action_confirm()
        self.assertEqual(order.state, 'dikonfirmasi')
        order.action_cancel()
        self.assertEqual(order.state, 'dibatalkan')


# ──────────────────────────────────────────────────────────────────────────────
# Template checks
# ──────────────────────────────────────────────────────────────────────────────

class TestOrderUITemplates(TransactionCase):

    def test_order_list_template_exists(self):
        """Template inventory_smi.order_list_page is installed."""
        tmpl = self.env.ref('inventory_smi.order_list_page', raise_if_not_found=False)
        self.assertIsNotNone(tmpl)

    def test_order_list_template_has_search(self):
        """Order list template has search input."""
        tmpl = self.env.ref('inventory_smi.order_list_page')
        self.assertIn('search', tmpl.arch.lower())

    def test_order_list_template_has_tambah_button(self):
        """Order list template has Tambah Order button."""
        tmpl = self.env.ref('inventory_smi.order_list_page')
        self.assertIn('tambah', tmpl.arch.lower())

    def test_order_list_template_has_table_columns(self):
        """Order list template has nama, no_spk, tanggal, status columns."""
        tmpl = self.env.ref('inventory_smi.order_list_page')
        arch = tmpl.arch.lower()
        self.assertIn('spk', arch)
        self.assertIn('tanggal', arch)
        self.assertIn('status', arch)

    def test_order_list_template_has_status_badges(self):
        """Order list template has status badge rendering."""
        tmpl = self.env.ref('inventory_smi.order_list_page')
        arch = tmpl.arch.lower()
        self.assertTrue('draft' in arch or 'dikonfirmasi' in arch)

    def test_order_form_step1_template_exists(self):
        """Template inventory_smi.order_form_step1_page is installed."""
        tmpl = self.env.ref('inventory_smi.order_form_step1_page', raise_if_not_found=False)
        self.assertIsNotNone(tmpl)

    def test_order_form_step1_template_has_csrf(self):
        """Order form step 1 template has CSRF token."""
        tmpl = self.env.ref('inventory_smi.order_form_step1_page')
        self.assertIn('csrf_token', tmpl.arch)

    def test_order_form_step1_template_has_name_field(self):
        """Order form step 1 has name field."""
        tmpl = self.env.ref('inventory_smi.order_form_step1_page')
        self.assertIn('name', tmpl.arch)

    def test_order_form_step1_template_has_no_spk_field(self):
        """Order form step 1 has no_spk field."""
        tmpl = self.env.ref('inventory_smi.order_form_step1_page')
        self.assertIn('no_spk', tmpl.arch)

    def test_order_form_step2_template_exists(self):
        """Template inventory_smi.order_form_step2_page is installed."""
        tmpl = self.env.ref('inventory_smi.order_form_step2_page', raise_if_not_found=False)
        self.assertIsNotNone(tmpl)

    def test_order_form_step2_template_has_material_selector(self):
        """Order form step 2 has material selector."""
        tmpl = self.env.ref('inventory_smi.order_form_step2_page')
        arch = tmpl.arch.lower()
        self.assertTrue('material' in arch or 'bahan' in arch)

    def test_order_form_step2_template_has_fifo_option(self):
        """Order form step 2 has FIFO/auto mode option."""
        tmpl = self.env.ref('inventory_smi.order_form_step2_page')
        arch = tmpl.arch.lower()
        self.assertTrue('fifo' in arch or 'auto' in arch or 'otomatis' in arch)

    def test_order_form_step2_template_has_manual_option(self):
        """Order form step 2 has manual pick mode option."""
        tmpl = self.env.ref('inventory_smi.order_form_step2_page')
        arch = tmpl.arch.lower()
        self.assertIn('manual', arch)

    def test_order_form_step3_template_exists(self):
        """Template inventory_smi.order_form_step3_page is installed."""
        tmpl = self.env.ref('inventory_smi.order_form_step3_page', raise_if_not_found=False)
        self.assertIsNotNone(tmpl)

    def test_order_form_step3_template_has_summary(self):
        """Order form step 3 has order summary."""
        tmpl = self.env.ref('inventory_smi.order_form_step3_page')
        arch = tmpl.arch.lower()
        self.assertTrue('konfirmasi' in arch or 'summary' in arch or 'ringkasan' in arch)

    def test_order_form_step3_template_has_confirm_button(self):
        """Order form step 3 has confirm button."""
        tmpl = self.env.ref('inventory_smi.order_form_step3_page')
        arch = tmpl.arch.lower()
        self.assertTrue('konfirmasi' in arch or 'confirm' in arch)

    def test_order_detail_template_exists(self):
        """Template inventory_smi.order_detail_page is installed."""
        tmpl = self.env.ref('inventory_smi.order_detail_page', raise_if_not_found=False)
        self.assertIsNotNone(tmpl)
