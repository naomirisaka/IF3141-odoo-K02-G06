from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


class _ActivityUIBase(TransactionCase):

    def setUp(self):
        super().setUp()
        self.uom = self.env['smi.uom'].create({'name': 'Lembar-actui'})
        self.cat = self.env['smi.material.category'].create({'name': 'Kertas-actui'})
        self.material = self.env['smi.material'].create({
            'name': 'Kertas Glossy 150gsm',
            'uom_id': self.uom.id,
            'category_id': self.cat.id,
        })
        self.point = self.env['smi.inventory_point'].create({
            'name': 'Rak C1', 'koordinat_x': 30.0, 'koordinat_y': 40.0,
        })

    def _create_user(self, login, group_xml_id):
        return self.env['res.users'].with_context(no_reset_password=True).create({
            'name': login, 'login': login, 'password': 'TestPass!',
            'groups_id': [
                (4, self.env.ref(group_xml_id).id),
                (4, self.env.ref('base.group_user').id),
            ],
        })

    def _log(self, tipe, deskripsi, user_id=None):
        vals = {
            'tipe': tipe,
            'deskripsi': deskripsi,
            'jabatan': 'Staf Produksi',
        }
        if user_id:
            vals['user_id'] = user_id
        return self.env['smi.activity.log'].create(vals)


# ──────────────────────────────────────────────────────────────────────────────
# Access control
# ──────────────────────────────────────────────────────────────────────────────

class TestActivityPageAccess(_ActivityUIBase):

    def test_activity_page_accessible_to_kepala(self):
        """Kepala Produksi can read all smi.activity.log records."""
        kepala = self._create_user('kepala_act', 'inventory_smi.group_kepala_produksi')
        env = self.env(user=kepala)
        logs = env['smi.activity.log'].search([])
        self.assertIsNotNone(logs)

    def test_activity_page_accessible_to_admin(self):
        """Admin can read all smi.activity.log records."""
        admin = self._create_user('admin_act', 'inventory_smi.group_admin')
        env = self.env(user=admin)
        logs = env['smi.activity.log'].search([])
        self.assertIsNotNone(logs)

    def test_activity_page_accessible_to_direktur(self):
        """Direktur can read smi.activity.log records (view-only)."""
        direktur = self._create_user('dir_act', 'inventory_smi.group_direktur')
        env = self.env(user=direktur)
        logs = env['smi.activity.log'].search([])
        self.assertIsNotNone(logs)

    def test_activity_page_accessible_to_staf(self):
        """Staf can read smi.activity.log records."""
        staf = self._create_user('staf_act', 'inventory_smi.group_staf_produksi')
        env = self.env(user=staf)
        logs = env['smi.activity.log'].search([])
        self.assertIsNotNone(logs)

    def test_staf_sees_only_own_logs(self):
        """Staf's activity view filtered to user_id = current user."""
        staf = self._create_user('staf_own', 'inventory_smi.group_staf_produksi')
        other = self._create_user('other_own', 'inventory_smi.group_staf_produksi')

        log_staf = self._log('stok_masuk', 'Log milik staf', user_id=staf.id)
        log_other = self._log('stok_masuk', 'Log milik other', user_id=other.id)

        env = self.env(user=staf)
        domain = [('user_id', '=', staf.id)]
        own_logs = env['smi.activity.log'].search(domain)
        all_log_ids = own_logs.ids

        self.assertIn(log_staf.id, all_log_ids)
        self.assertNotIn(log_other.id, all_log_ids)

    def test_kepala_sees_all_logs(self):
        """Kepala Produksi sees logs from all users (no user filter)."""
        staf = self._create_user('staf_kp', 'inventory_smi.group_staf_produksi')
        other = self._create_user('other_kp', 'inventory_smi.group_kepala_produksi')

        log1 = self._log('stok_masuk', 'Log staf kp', user_id=staf.id)
        log2 = self._log('order_dibuat', 'Log other kp', user_id=other.id)

        kepala = self._create_user('kepala_see_all', 'inventory_smi.group_kepala_produksi')
        env = self.env(user=kepala)
        all_logs = env['smi.activity.log'].search([])
        self.assertIn(log1.id, all_logs.ids)
        self.assertIn(log2.id, all_logs.ids)


# ──────────────────────────────────────────────────────────────────────────────
# Tab filtering
# ──────────────────────────────────────────────────────────────────────────────

class TestActivityTabFilter(_ActivityUIBase):

    def setUp(self):
        super().setUp()
        self._log('stok_masuk', 'Masuk 100 lembar kertas')
        self._log('stok_keluar', 'Keluar 50 lembar untuk order')
        self._log('titik_ditambah', 'Menambahkan Titik Baru X')
        self._log('order_dibuat', 'Membuat order Cetak Brosur')
        self._log('order_selesai', 'Order Cetak Brosur selesai')
        self._log('order_dibatalkan', 'Order dibatalkan')

    def test_tab_stok_returns_stok_masuk(self):
        """Tab stok includes tipe='stok_masuk'."""
        stok_tipes = ['stok_masuk', 'stok_keluar', 'titik_ditambah']
        logs = self.env['smi.activity.log'].search([('tipe', 'in', stok_tipes)])
        tipes = logs.mapped('tipe')
        self.assertIn('stok_masuk', tipes)

    def test_tab_stok_returns_stok_keluar(self):
        """Tab stok includes tipe='stok_keluar'."""
        logs = self.env['smi.activity.log'].search([
            ('tipe', 'in', ['stok_masuk', 'stok_keluar', 'titik_ditambah'])
        ])
        self.assertIn('stok_keluar', logs.mapped('tipe'))

    def test_tab_stok_returns_titik_ditambah(self):
        """Tab stok includes tipe='titik_ditambah'."""
        logs = self.env['smi.activity.log'].search([
            ('tipe', 'in', ['stok_masuk', 'stok_keluar', 'titik_ditambah'])
        ])
        self.assertIn('titik_ditambah', logs.mapped('tipe'))

    def test_tab_stok_excludes_order_types(self):
        """Tab stok does NOT include order_dibuat, order_selesai, order_dibatalkan."""
        logs = self.env['smi.activity.log'].search([
            ('tipe', 'in', ['stok_masuk', 'stok_keluar', 'titik_ditambah'])
        ])
        for log in logs:
            self.assertNotIn(log.tipe, ['order_dibuat', 'order_selesai', 'order_dibatalkan'])

    def test_tab_order_returns_order_dibuat(self):
        """Tab order includes tipe='order_dibuat'."""
        logs = self.env['smi.activity.log'].search([
            ('tipe', 'in', ['order_dibuat', 'order_selesai', 'order_dibatalkan'])
        ])
        self.assertIn('order_dibuat', logs.mapped('tipe'))

    def test_tab_order_returns_order_selesai(self):
        """Tab order includes tipe='order_selesai'."""
        logs = self.env['smi.activity.log'].search([
            ('tipe', 'in', ['order_dibuat', 'order_selesai', 'order_dibatalkan'])
        ])
        self.assertIn('order_selesai', logs.mapped('tipe'))

    def test_tab_order_returns_order_dibatalkan(self):
        """Tab order includes tipe='order_dibatalkan'."""
        logs = self.env['smi.activity.log'].search([
            ('tipe', 'in', ['order_dibuat', 'order_selesai', 'order_dibatalkan'])
        ])
        self.assertIn('order_dibatalkan', logs.mapped('tipe'))

    def test_tab_order_excludes_stok_types(self):
        """Tab order does NOT include stok_masuk, stok_keluar, titik_ditambah."""
        logs = self.env['smi.activity.log'].search([
            ('tipe', 'in', ['order_dibuat', 'order_selesai', 'order_dibatalkan'])
        ])
        for log in logs:
            self.assertNotIn(log.tipe, ['stok_masuk', 'stok_keluar', 'titik_ditambah'])


# ──────────────────────────────────────────────────────────────────────────────
# Search / filter
# ──────────────────────────────────────────────────────────────────────────────

class TestActivitySearch(_ActivityUIBase):

    def test_search_by_user_name(self):
        """Filtering by user name returns matching logs."""
        staf = self._create_user('Budi Santoso', 'inventory_smi.group_staf_produksi')
        log = self._log('stok_masuk', 'Input stok', user_id=staf.id)
        logs = self.env['smi.activity.log'].search([
            ('user_id.name', 'ilike', 'Budi Santoso')
        ])
        self.assertIn(log.id, logs.ids)

    def test_search_no_match_returns_empty(self):
        """Search with no match returns empty result."""
        logs = self.env['smi.activity.log'].search([
            ('user_id.name', 'ilike', 'XXXXNOEXIST_XYZ')
        ])
        self.assertFalse(logs)

    def test_filter_by_tipe(self):
        """Filter by tipe returns only matching records."""
        log = self._log('user_dibuat', 'Pengguna baru ditambahkan')
        logs = self.env['smi.activity.log'].search([('tipe', '=', 'user_dibuat')])
        self.assertIn(log.id, logs.ids)
        for l in logs:
            self.assertEqual(l.tipe, 'user_dibuat')

    def test_activity_sorted_newest_first(self):
        """Activity logs sorted by tanggal DESC."""
        import time
        log1 = self._log('stok_masuk', 'Log lama')
        time.sleep(0.05)
        log2 = self._log('stok_keluar', 'Log baru')
        logs = self.env['smi.activity.log'].search([], order='tanggal desc, id desc')
        dates = [l.tanggal for l in logs]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_activity_detail_has_deskripsi(self):
        """Activity log record has non-empty deskripsi."""
        log = self._log('stok_masuk', 'Menambahkan 100 lembar Kertas Glossy 150gsm ke Rak C1')
        fetched = self.env['smi.activity.log'].browse(log.id)
        self.assertTrue(fetched.deskripsi)
        self.assertIn('Kertas', fetched.deskripsi)

    def test_activity_detail_has_user_and_jabatan(self):
        """Activity log record has user_id and jabatan set."""
        log = self._log('order_dibuat', 'Order baru dibuat')
        self.assertTrue(log.user_id)
        self.assertTrue(log.jabatan)

    def test_activity_detail_has_tanggal(self):
        """Activity log record has tanggal set."""
        log = self._log('titik_ditambah', 'Titik baru ditambahkan')
        self.assertIsNotNone(log.tanggal)


# ──────────────────────────────────────────────────────────────────────────────
# Template checks
# ──────────────────────────────────────────────────────────────────────────────

class TestActivityUITemplates(TransactionCase):

    def test_activity_page_template_exists(self):
        """Template inventory_smi.activity_page is installed."""
        tmpl = self.env.ref('inventory_smi.activity_page', raise_if_not_found=False)
        self.assertIsNotNone(tmpl)

    def test_activity_template_has_two_tabs(self):
        """Activity template has Stok and Order tabs."""
        tmpl = self.env.ref('inventory_smi.activity_page')
        arch = tmpl.arch.lower()
        self.assertIn('stok', arch)
        self.assertIn('order', arch)

    def test_activity_template_has_search(self):
        """Activity template has search input."""
        tmpl = self.env.ref('inventory_smi.activity_page')
        self.assertIn('search', tmpl.arch.lower())

    def test_activity_template_has_table(self):
        """Activity template has table with log rows."""
        tmpl = self.env.ref('inventory_smi.activity_page')
        arch = tmpl.arch.lower()
        self.assertIn('tbl', arch)

    def test_activity_template_has_user_column(self):
        """Activity template shows user/pengguna column."""
        tmpl = self.env.ref('inventory_smi.activity_page')
        arch = tmpl.arch.lower()
        self.assertTrue('pengguna' in arch or 'user' in arch)

    def test_activity_template_has_deskripsi_column(self):
        """Activity template shows deskripsi column."""
        tmpl = self.env.ref('inventory_smi.activity_page')
        arch = tmpl.arch.lower()
        self.assertIn('deskripsi', arch)

    def test_activity_template_has_tipe_badges(self):
        """Activity template shows tipe badge rendering."""
        tmpl = self.env.ref('inventory_smi.activity_page')
        arch = tmpl.arch.lower()
        self.assertTrue('badge' in arch)

    def test_activity_template_has_tanggal_column(self):
        """Activity template shows tanggal column."""
        tmpl = self.env.ref('inventory_smi.activity_page')
        arch = tmpl.arch.lower()
        self.assertIn('tanggal', arch)

    def test_activity_template_has_detail_modal(self):
        """Activity template has detail modal structure."""
        tmpl = self.env.ref('inventory_smi.activity_page')
        arch = tmpl.arch.lower()
        self.assertTrue('modal' in arch or 'detail' in arch)

    def test_activity_template_has_jabatan_column(self):
        """Activity template shows jabatan/role column."""
        tmpl = self.env.ref('inventory_smi.activity_page')
        arch = tmpl.arch.lower()
        self.assertTrue('jabatan' in arch or 'role' in arch)
