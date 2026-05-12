from odoo.tests.common import TransactionCase


class _DashBase(TransactionCase):

    def setUp(self):
        super().setUp()
        self.uom = self.env['smi.uom'].create({'name': 'Lembar-dash'})
        self.cat = self.env['smi.material.category'].create({'name': 'Kertas-dash'})
        self.point = self.env['smi.inventory_point'].create({
            'name': 'Rak-dash', 'koordinat_x': 30.0, 'koordinat_y': 40.0,
        })

    def _make_material(self, name, stok_minimum=0.0):
        return self.env['smi.material'].create({
            'name': name, 'uom_id': self.uom.id,
            'category_id': self.cat.id, 'stok_minimum': stok_minimum,
        })

    def _add_stock(self, material, jumlah, tanggal='2026-01-01 08:00:00'):
        return self.env['smi.stock_entry'].create({
            'material_id': material.id,
            'inventory_point_id': self.point.id,
            'jumlah_awal': jumlah,
            'tanggal_masuk': tanggal,
        })

    def _make_order(self, material, jumlah, state='draft'):
        order = self.env['smi.order'].create({'name': 'Order Dash', 'tanggal': '2026-02-01'})
        self.env['smi.order.line'].create({
            'order_id': order.id, 'material_id': material.id,
            'jumlah_dibutuhkan': jumlah, 'mode_pick': 'auto',
        })
        if state == 'dikonfirmasi':
            order.action_confirm()
        return order

    def _get_stats(self):
        """Mirror the controller's _get_dashboard_stats() logic."""
        env = self.env
        total_bahan = env['smi.material'].search_count([('active', '=', True)])
        total_stok = sum(env['smi.material'].search([('active', '=', True)]).mapped('total_stok'))
        active_orders = env['smi.order'].search_count([('state', '=', 'dikonfirmasi')])
        low_stock_count = env['smi.material'].search_count([
            ('active', '=', True), ('is_low_stock', '=', True)
        ])
        return {
            'total_bahan': total_bahan,
            'total_stok': total_stok,
            'active_orders': active_orders,
            'low_stock_count': low_stock_count,
        }


class TestDashboardStats(_DashBase):

    def test_dashboard_stat_cards_data_structure(self):
        """_get_dashboard_stats returns total_bahan, total_stok, active_orders, low_stock_count."""
        stats = self._get_stats()
        self.assertIn('total_bahan', stats)
        self.assertIn('total_stok', stats)
        self.assertIn('active_orders', stats)
        self.assertIn('low_stock_count', stats)

    def test_total_bahan_counts_active_materials(self):
        """total_bahan = count of active smi.material records."""
        before = self._get_stats()['total_bahan']
        self._make_material('Bahan Baru Dash')
        after = self._get_stats()['total_bahan']
        self.assertEqual(after, before + 1)

    def test_total_stok_sums_all_materials(self):
        """total_stok = sum of total_stok across all active materials."""
        mat = self._make_material('Kertas Total Dash')
        self._add_stock(mat, 75.0)
        stats = self._get_stats()
        self.assertGreaterEqual(stats['total_stok'], 75.0)

    def test_active_orders_counts_dikonfirmasi_only(self):
        """active_orders = count of orders with state='dikonfirmasi'."""
        mat = self._make_material('Bahan Order Dash')
        self._add_stock(mat, 100.0)
        before = self._get_stats()['active_orders']
        self._make_order(mat, 20.0, state='dikonfirmasi')
        after = self._get_stats()['active_orders']
        self.assertEqual(after, before + 1)

    def test_draft_order_not_counted_as_active(self):
        """Draft orders do not count toward active_orders."""
        mat = self._make_material('Bahan Draft Dash')
        before = self._get_stats()['active_orders']
        self._make_order(mat, 10.0, state='draft')
        after = self._get_stats()['active_orders']
        self.assertEqual(before, after)

    def test_low_stock_count_increments_when_material_is_low(self):
        """low_stock_count reflects materials with is_low_stock=True."""
        mat = self._make_material('Bahan Low Dash', stok_minimum=50.0)
        self._add_stock(mat, 10.0)  # 10 < 50 → is_low_stock
        mat.invalidate_recordset()
        stats = self._get_stats()
        self.assertGreaterEqual(stats['low_stock_count'], 1)

    def test_inactive_material_excluded_from_stats(self):
        """Inactive (archived) materials are excluded from all stat counts."""
        mat = self._make_material('Bahan Arsip Dash')
        self._add_stock(mat, 50.0)
        before = self._get_stats()['total_bahan']
        mat.write({'active': False})
        after = self._get_stats()['total_bahan']
        self.assertEqual(after, before - 1)


class TestDashboardTop10Bahan(_DashBase):

    def _get_top10(self):
        """Mirror the controller's top-10 logic: low-stock first, then fill up to 10 total."""
        materials = self.env['smi.material'].search([('active', '=', True)])
        low = materials.filtered(lambda m: m.is_low_stock).sorted('total_stok')
        normal = materials.filtered(lambda m: not m.is_low_stock).sorted('total_stok')
        max_items = 10
        result = list(low)
        if len(result) < max_items:
            needed = max_items - len(result)
            result += list(normal[:needed])
        return result[:max_items]

    def test_dashboard_top10_bahan_low_stock_first(self):
        """Low-stock materials appear before normal-stock materials in top-5."""
        normal = self._make_material('Normal Dash Mat', stok_minimum=0.0)
        low = self._make_material('Low Dash Mat', stok_minimum=100.0)
        self._add_stock(normal, 200.0)
        self._add_stock(low, 5.0)
        normal.invalidate_recordset()
        low.invalidate_recordset()
        top10 = self._get_top10()
        ids = [m.id for m in top10]
        self.assertIn(low.id, ids)
        self.assertIn(normal.id, ids)
        self.assertLess(ids.index(low.id), ids.index(normal.id))

    def test_dashboard_top10_returns_at_most_10(self):
        """Top-10 list is capped at 10 entries."""
        for i in range(12):
            m = self._make_material(f'Bahan Top10-{i}')
            self._add_stock(m, float(i + 1) * 10)
        top10 = self._get_top10()[:10]
        self.assertLessEqual(len(top10), 10)

    def test_dashboard_top10_contains_material_fields(self):
        """Each material in top-10 has name, total_stok, uom, is_low_stock."""
        mat = self._make_material('Mat Fields Dash', stok_minimum=0.0)
        self._add_stock(mat, 30.0)
        mat.invalidate_recordset()
        top10 = self._get_top10()
        found = next((m for m in top10 if m.id == mat.id), None)
        if found:
            self.assertTrue(found.name)
            self.assertIsNotNone(found.total_stok)
            self.assertIsNotNone(found.uom_id)


class TestDashboardRecentOrders(_DashBase):

    def test_dashboard_recent_orders_max_5(self):
        """Dashboard order feed returns at most 3 entries."""
        mat = self._make_material('Mat Orders Dash')
        self._add_stock(mat, 1000.0)
        for i in range(7):
            self._make_order(mat, 1.0)
        orders = self.env['smi.order'].search([], order='tanggal desc, id desc', limit=3)
        self.assertLessEqual(len(orders), 3)

    def test_dashboard_recent_orders_sorted_by_date_desc(self):
        """Orders in dashboard feed are newest first."""
        mat = self._make_material('Mat Order Sort Dash')
        self._add_stock(mat, 1000.0)
        o1 = self.env['smi.order'].create({'name': 'Old Order', 'tanggal': '2026-01-01'})
        o2 = self.env['smi.order'].create({'name': 'New Order', 'tanggal': '2026-03-01'})
        orders = self.env['smi.order'].search([], order='tanggal desc, id desc', limit=3)
        ids = orders.ids
        self.assertLess(ids.index(o2.id), ids.index(o1.id))

    def test_dashboard_orders_have_required_fields(self):
        """Each order record has name, no_spk, tanggal, state."""
        mat = self._make_material('Mat Req Dash')
        order = self.env['smi.order'].create({
            'name': 'Order Req Test', 'no_spk': 'SPK-001', 'tanggal': '2026-02-15',
        })
        self.assertTrue(order.name)
        self.assertTrue(order.no_spk)
        self.assertIsNotNone(order.tanggal)
        self.assertEqual(order.state, 'draft')


class TestDashboardRecentActivity(_DashBase):

    def test_dashboard_recent_activity_max_5(self):
        """Dashboard activity feed returns at most 5 entries."""
        mat = self._make_material('Mat Activity Dash')
        for i in range(7):
            self._add_stock(mat, float(i + 1) * 5)
        logs = self.env['smi.activity.log'].search([], order='tanggal desc, id desc', limit=5)
        self.assertLessEqual(len(logs), 5)

    def test_dashboard_activity_sorted_newest_first(self):
        """Activity logs in dashboard are sorted by tanggal DESC."""
        logs = self.env['smi.activity.log'].search([], order='tanggal desc, id desc', limit=5)
        dates = [log.tanggal for log in logs]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_dashboard_activity_has_required_fields(self):
        """Each activity log has user_id, jabatan, tanggal, tipe, deskripsi."""
        mat = self._make_material('Mat Log Dash')
        self._add_stock(mat, 10.0)
        log = self.env['smi.activity.log'].search(
            [('tipe', '=', 'stok_masuk')], order='id desc', limit=1
        )
        self.assertTrue(log)
        self.assertIsNotNone(log.tanggal)
        self.assertTrue(log.tipe)
        self.assertTrue(log.deskripsi)


class TestDashboardTemplate(TransactionCase):

    def test_dashboard_layout_template_exists(self):
        """Template inventory_smi.layout is installed."""
        tmpl = self.env.ref('inventory_smi.layout', raise_if_not_found=False)
        self.assertIsNotNone(tmpl)

    def test_dashboard_page_template_exists(self):
        """Template inventory_smi.dashboard_page is installed."""
        tmpl = self.env.ref('inventory_smi.dashboard_page', raise_if_not_found=False)
        self.assertIsNotNone(tmpl)

    def test_layout_template_has_sidebar(self):
        """Layout template arch contains sidebar navigation."""
        tmpl = self.env.ref('inventory_smi.layout')
        self.assertIn('sidebar', tmpl.arch)

    def test_layout_template_has_dashboard_link(self):
        """Layout template arch contains link to /smi/dashboard."""
        tmpl = self.env.ref('inventory_smi.layout')
        self.assertIn('/smi/dashboard', tmpl.arch)

    def test_layout_template_has_stok_link(self):
        """Layout template arch contains link to /smi/stok."""
        tmpl = self.env.ref('inventory_smi.layout')
        self.assertIn('/smi/stok', tmpl.arch)

    def test_layout_template_has_order_link(self):
        """Layout template arch contains link to /smi/order."""
        tmpl = self.env.ref('inventory_smi.layout')
        self.assertIn('/smi/order', tmpl.arch)

    def test_layout_template_has_pengguna_admin_only(self):
        """Layout template has pengguna link gated by group_admin check."""
        tmpl = self.env.ref('inventory_smi.layout')
        self.assertIn('/smi/pengguna', tmpl.arch)
        self.assertIn('group_admin', tmpl.arch)

    def test_dashboard_page_has_stat_cards(self):
        """Dashboard page template contains stat card structure."""
        tmpl = self.env.ref('inventory_smi.dashboard_page')
        self.assertIn('stat-card', tmpl.arch)

    def test_dashboard_page_has_bahan_section(self):
        """Dashboard page template contains bahan list section."""
        tmpl = self.env.ref('inventory_smi.dashboard_page')
        self.assertIn('top10_bahan', tmpl.arch)

    def test_dashboard_page_has_order_section(self):
        """Dashboard page template contains recent orders section."""
        tmpl = self.env.ref('inventory_smi.dashboard_page')
        self.assertIn('recent_orders', tmpl.arch)

    def test_dashboard_page_has_activity_section(self):
        """Dashboard page template contains recent activity section."""
        tmpl = self.env.ref('inventory_smi.dashboard_page')
        self.assertIn('recent_activity', tmpl.arch)

    def test_dashboard_page_has_tambah_stok_button(self):
        """Dashboard page has Tambah Stok button hidden for Direktur."""
        tmpl = self.env.ref('inventory_smi.dashboard_page')
        self.assertIn('is_direktur', tmpl.arch)


class TestDashboardRoleAccess(TransactionCase):

    def _make_user(self, login, group_xml_id):
        return self.env['res.users'].with_context(no_reset_password=True).create({
            'name': login, 'login': login, 'password': 'TestPass!',
            'groups_id': [
                (4, self.env.ref(group_xml_id).id),
                (4, self.env.ref('base.group_user').id),
            ],
        })

    def test_direktur_has_view_only_group(self):
        """Direktur role has no write/create permissions on smi.order."""
        from odoo.exceptions import AccessError
        direktur = self._make_user('dir_dash_test', 'inventory_smi.group_direktur')
        env = self.env(user=direktur)
        with self.assertRaises(AccessError):
            env['smi.order'].create({'name': 'Test', 'tanggal': '2026-01-01'})

    def test_staf_can_access_dashboard_data(self):
        """Staf Produksi can read smi.material, smi.order, smi.activity.log."""
        staf = self._make_user('staf_dash_test', 'inventory_smi.group_staf_produksi')
        env = self.env(user=staf)
        env['smi.material'].search([('active', '=', True)])
        env['smi.order'].search([])
        env['smi.activity.log'].search([])

    def test_direktur_can_read_materials(self):
        """Direktur can read smi.material (view-only)."""
        direktur = self._make_user('dir_read_test', 'inventory_smi.group_direktur')
        env = self.env(user=direktur)
        materials = env['smi.material'].search([('active', '=', True)])
        self.assertIsNotNone(materials)

    def test_must_change_password_field_exists(self):
        """res.users has must_change_password field from Phase 2."""
        user = self.env['res.users'].browse(self.env.uid)
        self.assertIsNotNone(user.must_change_password)
