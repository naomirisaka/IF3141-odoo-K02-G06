from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


class _AccessBase(TransactionCase):

    def _create_user(self, login, group_xml_id):
        return self.env['res.users'].with_context(no_reset_password=True).create({
            'name': login, 'login': login, 'password': 'TestPass!',
            'groups_id': [
                (4, self.env.ref(group_xml_id).id),
                (4, self.env.ref('base.group_user').id),
            ],
        })


# ──────────────────────────────────────────────────────────────────────────────
# Role-based ORM access enforcement
# ──────────────────────────────────────────────────────────────────────────────

class TestRoleVisibility(_AccessBase):

    def setUp(self):
        super().setUp()
        self.uom = self.env['smi.uom'].create({'name': 'Lembar-ac11'})
        self.cat = self.env['smi.material.category'].create({'name': 'Kertas-ac11'})
        self.material = self.env['smi.material'].create({
            'name': 'Kertas Test AC11',
            'uom_id': self.uom.id,
            'category_id': self.cat.id,
        })
        self.point = self.env['smi.inventory_point'].create({
            'name': 'Rak AC11', 'koordinat_x': 20.0, 'koordinat_y': 20.0,
        })

    # --- Direktur: read-only across the board ---

    def test_direktur_cannot_create_stock_entry(self):
        """Direktur cannot create smi.stock_entry (AccessError)."""
        direktur = self._create_user('dir_ac11', 'inventory_smi.group_direktur')
        with self.assertRaises(AccessError):
            self.env(user=direktur)['smi.stock_entry'].create({
                'material_id': self.material.id,
                'inventory_point_id': self.point.id,
                'jumlah_awal': 10.0,
            })

    def test_direktur_cannot_create_order(self):
        """Direktur cannot create smi.order (AccessError)."""
        direktur = self._create_user('dir_order_ac11', 'inventory_smi.group_direktur')
        with self.assertRaises(AccessError):
            self.env(user=direktur)['smi.order'].create({'name': 'Order Direktur'})

    def test_direktur_cannot_write_material(self):
        """Direktur cannot update smi.material records (AccessError)."""
        direktur = self._create_user('dir_write_ac11', 'inventory_smi.group_direktur')
        with self.assertRaises(AccessError):
            self.material.with_user(direktur).write({'name': 'Diubah Direktur'})

    def test_direktur_cannot_create_inventory_point(self):
        """Direktur cannot create smi.inventory_point (AccessError)."""
        direktur = self._create_user('dir_pt_ac11', 'inventory_smi.group_direktur')
        with self.assertRaises(AccessError):
            self.env(user=direktur)['smi.inventory_point'].create({
                'name': 'Titik Direktur', 'koordinat_x': 10.0, 'koordinat_y': 10.0,
            })

    def test_direktur_can_read_materials(self):
        """Direktur can read smi.material records."""
        direktur = self._create_user('dir_read_ac11', 'inventory_smi.group_direktur')
        mats = self.env(user=direktur)['smi.material'].search([])
        self.assertIsNotNone(mats)

    def test_direktur_can_read_orders(self):
        """Direktur can read smi.order records."""
        direktur = self._create_user('dir_read_ord_ac11', 'inventory_smi.group_direktur')
        orders = self.env(user=direktur)['smi.order'].search([])
        self.assertIsNotNone(orders)

    # --- Staf: no inventory_point create ---

    def test_staf_cannot_create_inventory_point(self):
        """Staf Produksi cannot create smi.inventory_point (AccessError)."""
        staf = self._create_user('staf_pt_ac11', 'inventory_smi.group_staf_produksi')
        with self.assertRaises(AccessError):
            self.env(user=staf)['smi.inventory_point'].create({
                'name': 'Titik Staf', 'koordinat_x': 30.0, 'koordinat_y': 30.0,
            })

    def test_staf_is_not_admin(self):
        """Staf Produksi is not in group_admin."""
        staf = self._create_user('staf_admin_chk', 'inventory_smi.group_staf_produksi')
        self.assertFalse(staf.has_group('inventory_smi.group_admin'))

    def test_staf_cannot_delete_material(self):
        """Staf Produksi cannot delete smi.material (AccessError)."""
        staf = self._create_user('staf_del_ac11', 'inventory_smi.group_staf_produksi')
        with self.assertRaises(AccessError):
            self.material.with_user(staf).unlink()

    # --- Kepala: full stock/order, no user management ---

    def test_kepala_can_create_inventory_point(self):
        """Kepala Produksi can create smi.inventory_point."""
        kepala = self._create_user('kepala_pt_ac11', 'inventory_smi.group_kepala_produksi')
        pt = self.env(user=kepala)['smi.inventory_point'].create({
            'name': 'Titik Kepala AC11', 'koordinat_x': 50.0, 'koordinat_y': 50.0,
        })
        self.assertTrue(pt.id)

    def test_kepala_is_not_admin(self):
        """Kepala Produksi is not in group_admin."""
        kepala = self._create_user('kepala_admin_chk', 'inventory_smi.group_kepala_produksi')
        self.assertFalse(kepala.has_group('inventory_smi.group_admin'))

    # --- Admin: full access ---

    def test_admin_can_create_all_models(self):
        """Admin can create stock entry, order, and inventory point."""
        admin = self._create_user('admin_full_ac11', 'inventory_smi.group_admin')
        env = self.env(user=admin)
        pt = env['smi.inventory_point'].create({
            'name': 'Titik Admin AC11', 'koordinat_x': 70.0, 'koordinat_y': 70.0,
        })
        entry = env['smi.stock_entry'].create({
            'material_id': self.material.id,
            'inventory_point_id': pt.id,
            'jumlah_awal': 100.0,
        })
        order = env['smi.order'].create({'name': 'Order Admin AC11'})
        self.assertTrue(pt.id)
        self.assertTrue(entry.id)
        self.assertTrue(order.id)

    def test_admin_is_in_group_admin(self):
        """Admin user is in group_admin."""
        admin = self._create_user('admin_grp_chk', 'inventory_smi.group_admin')
        self.assertTrue(admin.has_group('inventory_smi.group_admin'))

    # --- Layout template role checks ---

    def test_layout_has_admin_only_menu(self):
        """Layout template restricts Pengguna menu to group_admin."""
        tmpl = self.env.ref('inventory_smi.layout')
        arch = tmpl.arch
        self.assertIn('group_admin', arch)
        self.assertIn('pengguna', arch.lower())

    def test_layout_hides_tambah_stok_from_direktur(self):
        """Stock list template hides Tambah Stok from direktur."""
        tmpl = self.env.ref('inventory_smi.stock_list_page')
        arch = tmpl.arch
        self.assertIn('is_direktur', arch)
        self.assertIn('tambah', arch.lower())

    def test_layout_hides_tambah_order_from_direktur(self):
        """Order list template hides Tambah Order from direktur."""
        tmpl = self.env.ref('inventory_smi.order_list_page')
        arch = tmpl.arch
        self.assertIn('is_direktur', arch)

    def test_order_detail_has_role_restricted_actions(self):
        """Order detail template restricts cancel/complete to authorized roles."""
        tmpl = self.env.ref('inventory_smi.order_detail_page')
        arch = tmpl.arch
        self.assertIn('is_direktur', arch)

    def test_staf_cannot_delete_stock_entry(self):
        """Staf Produksi cannot delete smi.stock_entry."""
        staf = self._create_user('staf_del_se_ac11', 'inventory_smi.group_staf_produksi')
        entry = self.env['smi.stock_entry'].create({
            'material_id': self.material.id,
            'inventory_point_id': self.point.id,
            'jumlah_awal': 50.0,
        })
        with self.assertRaises(AccessError):
            entry.with_user(staf).unlink()


# ──────────────────────────────────────────────────────────────────────────────
# Password expiry banner
# ──────────────────────────────────────────────────────────────────────────────

class TestPasswordExpiryBanner(TransactionCase):

    def test_layout_has_expiry_banner(self):
        """Layout template contains password expiry banner."""
        tmpl = self.env.ref('inventory_smi.layout')
        arch = tmpl.arch
        self.assertIn('must_change_password', arch)

    def test_layout_expiry_banner_has_warning_text(self):
        """Layout expiry banner contains Indonesian warning text."""
        tmpl = self.env.ref('inventory_smi.layout')
        arch = tmpl.arch.lower()
        self.assertTrue('kata sandi' in arch or 'password' in arch or 'kadaluwarsa' in arch)

    def test_user_must_change_password_field_exists(self):
        """res.users has must_change_password computed field."""
        user = self.env.user
        self.assertIn('must_change_password', user._fields)

    def test_fresh_user_password_not_expired(self):
        """Newly created user does not have must_change_password=True."""
        new_user = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Fresh User Expiry', 'login': 'fresh_expiry_ac11', 'password': 'TestPass!',
            'groups_id': [(4, self.env.ref('base.group_user').id)],
        })
        new_user.invalidate_recordset()
        self.assertFalse(new_user.must_change_password)

    def test_user_with_old_password_is_expired(self):
        """User with password_last_changed > 90 days ago has must_change_password=True."""
        from datetime import datetime, timedelta
        user = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Old Password User', 'login': 'old_pwd_ac11', 'password': 'TestPass!',
            'groups_id': [(4, self.env.ref('base.group_user').id)],
        })
        old_date = datetime.now() - timedelta(days=91)
        user.sudo().write({'smi_password_last_changed': old_date})
        user.invalidate_recordset()
        self.assertTrue(user.must_change_password)


# ──────────────────────────────────────────────────────────────────────────────
# Seed data
# ──────────────────────────────────────────────────────────────────────────────

class TestSeedData(TransactionCase):

    def test_seed_uom_lembar_exists(self):
        """Seed UoM 'Lembar' is installed (XML ID: uom_lembar)."""
        rec = self.env.ref('inventory_smi.uom_lembar', raise_if_not_found=False)
        self.assertIsNotNone(rec)

    def test_seed_uom_kg_exists(self):
        """Seed UoM 'Kg' is installed (XML ID: uom_kg)."""
        rec = self.env.ref('inventory_smi.uom_kg', raise_if_not_found=False)
        self.assertIsNotNone(rec)

    def test_seed_uom_liter_exists(self):
        """Seed UoM 'Liter' is installed (XML ID: uom_liter)."""
        rec = self.env.ref('inventory_smi.uom_liter', raise_if_not_found=False)
        self.assertIsNotNone(rec)

    def test_seed_category_kertas_exists(self):
        """Seed category 'Kertas' is installed (XML ID: cat_kertas)."""
        rec = self.env.ref('inventory_smi.cat_kertas', raise_if_not_found=False)
        self.assertIsNotNone(rec)

    def test_seed_category_tinta_exists(self):
        """Seed category 'Tinta' is installed (XML ID: cat_tinta)."""
        rec = self.env.ref('inventory_smi.cat_tinta', raise_if_not_found=False)
        self.assertIsNotNone(rec)

    def test_seed_category_laminasi_exists(self):
        """Seed category 'Laminasi' is installed (XML ID: cat_laminasi)."""
        rec = self.env.ref('inventory_smi.cat_laminasi', raise_if_not_found=False)
        self.assertIsNotNone(rec)

    def test_seed_material_kertas_art_exists(self):
        """Seed material 'Kertas Art Paper 120gsm' is installed."""
        rec = self.env.ref('inventory_smi.mat_kertas_art_120', raise_if_not_found=False)
        self.assertIsNotNone(rec)

    def test_seed_material_tinta_hitam_exists(self):
        """Seed material 'Tinta Hitam' is installed."""
        rec = self.env.ref('inventory_smi.mat_tinta_hitam', raise_if_not_found=False)
        self.assertIsNotNone(rec)

    def test_seed_material_laminasi_glossy_exists(self):
        """Seed material 'Laminasi Glossy' is installed."""
        rec = self.env.ref('inventory_smi.mat_laminasi_glossy', raise_if_not_found=False)
        self.assertIsNotNone(rec)

    def test_seed_materials_have_stok_minimum(self):
        """Seed materials have stok_minimum > 0."""
        for xml_id in ['inventory_smi.mat_kertas_art_120',
                        'inventory_smi.mat_tinta_hitam',
                        'inventory_smi.mat_laminasi_glossy']:
            rec = self.env.ref(xml_id, raise_if_not_found=False)
            if rec:
                self.assertGreater(rec.stok_minimum, 0,
                                   f"{xml_id} should have stok_minimum > 0")


# ──────────────────────────────────────────────────────────────────────────────
# Responsive layout & CSS
# ──────────────────────────────────────────────────────────────────────────────

class TestResponsiveLayout(TransactionCase):

    def test_layout_template_exists(self):
        """Main layout template is installed."""
        tmpl = self.env.ref('inventory_smi.layout', raise_if_not_found=False)
        self.assertIsNotNone(tmpl)

    def test_layout_has_sidebar(self):
        """Layout template has sidebar navigation."""
        tmpl = self.env.ref('inventory_smi.layout')
        arch = tmpl.arch.lower()
        self.assertIn('sidebar', arch)

    def test_layout_has_topbar(self):
        """Layout template has topbar."""
        tmpl = self.env.ref('inventory_smi.layout')
        arch = tmpl.arch.lower()
        self.assertIn('topbar', arch)

    def test_layout_has_all_nav_items(self):
        """Layout template has all 4 main nav items."""
        tmpl = self.env.ref('inventory_smi.layout')
        arch = tmpl.arch.lower()
        self.assertIn('dashboard', arch)
        self.assertIn('stok', arch)
        self.assertIn('order', arch)
        self.assertIn('aktivitas', arch)

    def test_layout_has_logout_link(self):
        """Layout template has logout link."""
        tmpl = self.env.ref('inventory_smi.layout')
        arch = tmpl.arch.lower()
        self.assertTrue('logout' in arch or 'session/logout' in arch or 'keluar' in arch)

    def test_pengguna_controller_accessible_to_admin(self):
        """Admin can read res.users records."""
        admin = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Admin Pengguna Test', 'login': 'admin_peng_ac11', 'password': 'TestPass!',
            'groups_id': [
                (4, self.env.ref('inventory_smi.group_admin').id),
                (4, self.env.ref('base.group_user').id),
            ],
        })
        users = self.env(user=admin)['res.users'].search([])
        self.assertIsNotNone(users)

    def test_pengguna_controller_template_exists(self):
        """Template inventory_smi.pengguna_page is installed."""
        tmpl = self.env.ref('inventory_smi.pengguna_page', raise_if_not_found=False)
        self.assertIsNotNone(tmpl)
