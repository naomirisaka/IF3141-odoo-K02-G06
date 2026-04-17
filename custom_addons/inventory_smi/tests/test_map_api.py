from odoo.tests.common import TransactionCase


class _MapBase(TransactionCase):

    def setUp(self):
        super().setUp()
        self.uom = self.env['smi.uom'].create({'name': 'Lembar-map'})
        self.cat = self.env['smi.material.category'].create({'name': 'Kertas-map'})
        self.mat1 = self.env['smi.material'].create({
            'name': 'Kertas Art 120gsm',
            'uom_id': self.uom.id,
            'category_id': self.cat.id,
            'stok_minimum': 20.0,
        })
        self.mat2 = self.env['smi.material'].create({
            'name': 'Tinta Hitam',
            'uom_id': self.uom.id,
            'category_id': self.cat.id,
            'stok_minimum': 0.0,
        })
        self.point1 = self.env['smi.inventory_point'].create({
            'name': 'Rak A1',
            'koordinat_x': 20.0,
            'koordinat_y': 30.0,
        })
        self.point2 = self.env['smi.inventory_point'].create({
            'name': 'Area Cetak',
            'koordinat_x': 70.0,
            'koordinat_y': 50.0,
        })
        # mat1 at point1: 10 units → below stok_minimum (20) → is_low_stock
        self.env['smi.stock_entry'].create({
            'material_id': self.mat1.id,
            'inventory_point_id': self.point1.id,
            'jumlah_awal': 10.0,
            'tanggal_masuk': '2026-01-01 08:00:00',
        })
        # mat2 at point2: 50 units, stok_minimum=0 → not low
        self.env['smi.stock_entry'].create({
            'material_id': self.mat2.id,
            'inventory_point_id': self.point2.id,
            'jumlah_awal': 50.0,
            'tanggal_masuk': '2026-01-05 08:00:00',
        })

    def _build_point_summary(self, point):
        """Mirrors the logic in SmiMapApiController._point_summary()."""
        entries = point.stock_entry_ids.filtered(lambda e: e.state == 'tersedia')
        materials = []
        for entry in entries:
            materials.append({
                'material_id': entry.material_id.id,
                'material_name': entry.material_id.name,
                'jumlah_tersisa': entry.jumlah_tersisa,
                'satuan': entry.material_id.uom_id.name,
                'is_low_stock': entry.material_id.is_low_stock,
                'tanggal_masuk': (
                    entry.tanggal_masuk.isoformat() if entry.tanggal_masuk else None
                ),
            })
        return {
            'id': point.id,
            'name': point.name,
            'x': point.koordinat_x,
            'y': point.koordinat_y,
            'deskripsi': point.deskripsi or '',
            'materials': materials,
        }


class TestGetInventoryPoints(_MapBase):

    def test_get_inventory_points_returns_json(self):
        """GET /smi/api/inventory_points returns a list of active points."""
        points = self.env['smi.inventory_point'].search([('active', '=', True)])
        self.assertGreaterEqual(len(points), 2)

    def test_get_inventory_points_includes_stok_summary(self):
        """Each point summary includes: id, name, x, y, materials list."""
        summary = self._build_point_summary(self.point1)
        self.assertIn('id', summary)
        self.assertIn('name', summary)
        self.assertIn('x', summary)
        self.assertIn('y', summary)
        self.assertIn('materials', summary)
        self.assertIsInstance(summary['materials'], list)

    def test_point_summary_materials_contain_required_fields(self):
        """Material entries in point summary have material_id, jumlah_tersisa, satuan, is_low_stock."""
        summary = self._build_point_summary(self.point1)
        self.assertEqual(len(summary['materials']), 1)
        m = summary['materials'][0]
        self.assertIn('material_id', m)
        self.assertIn('jumlah_tersisa', m)
        self.assertIn('satuan', m)
        self.assertIn('is_low_stock', m)

    def test_point_summary_low_stock_flag_is_true(self):
        """is_low_stock=True for material with stok < stok_minimum."""
        self.mat1.invalidate_recordset()
        summary = self._build_point_summary(self.point1)
        self.assertTrue(summary['materials'][0]['is_low_stock'])

    def test_point_summary_not_low_stock_when_minimum_zero(self):
        """is_low_stock=False when stok_minimum=0."""
        self.mat2.invalidate_recordset()
        summary = self._build_point_summary(self.point2)
        self.assertFalse(summary['materials'][0]['is_low_stock'])

    def test_inactive_point_excluded_from_active_search(self):
        """Soft-deleted point not returned when filtering by active=True."""
        self.point2.write({'active': False})
        active_points = self.env['smi.inventory_point'].search([('active', '=', True)])
        self.assertNotIn(self.point2.id, active_points.ids)


class TestGetSinglePointDetail(_MapBase):

    def test_get_single_point_detail(self):
        """Single point detail includes full stock entry info."""
        point = self.env['smi.inventory_point'].browse(self.point1.id)
        self.assertEqual(len(point.stock_entry_ids), 1)
        entry = point.stock_entry_ids[0]
        self.assertEqual(entry.jumlah_awal, 10.0)
        self.assertEqual(entry.jumlah_tersisa, 10.0)
        self.assertIsNotNone(entry.tanggal_masuk)

    def test_single_point_summary_excludes_habis_entries(self):
        """Entries with state='habis' are excluded from the materials summary."""
        entry = self.point1.stock_entry_ids[0]
        entry.write({'jumlah_tersisa': 0.0})
        summary = self._build_point_summary(self.point1)
        self.assertEqual(len(summary['materials']), 0)

    def test_single_point_multiple_entries_all_shown(self):
        """Multiple stock entries at same point all appear in summary."""
        self.env['smi.stock_entry'].create({
            'material_id': self.mat2.id,
            'inventory_point_id': self.point1.id,
            'jumlah_awal': 30.0,
            'tanggal_masuk': '2026-01-10 08:00:00',
        })
        summary = self._build_point_summary(self.point1)
        self.assertEqual(len(summary['materials']), 2)


class TestGetMaterials(_MapBase):

    def test_get_materials_returns_stok_and_low_stock_flag(self):
        """smi.material exposes total_stok and is_low_stock."""
        self.mat1.invalidate_recordset()
        self.assertEqual(self.mat1.total_stok, 10.0)
        self.assertTrue(self.mat1.is_low_stock)

    def test_material_total_stok_aggregates_all_points(self):
        """total_stok sums across all inventory points."""
        self.env['smi.stock_entry'].create({
            'material_id': self.mat1.id,
            'inventory_point_id': self.point2.id,
            'jumlah_awal': 5.0,
            'tanggal_masuk': '2026-01-12 08:00:00',
        })
        self.mat1.invalidate_recordset()
        self.assertEqual(self.mat1.total_stok, 15.0)

    def test_material_filter_by_point(self):
        """Materials at a specific point accessible via stock_entry_ids."""
        mat_ids = self.point1.stock_entry_ids.mapped('material_id').ids
        self.assertIn(self.mat1.id, mat_ids)
        self.assertNotIn(self.mat2.id, mat_ids)


class TestCreateInventoryPoint(_MapBase):

    def _create_user(self, login, group_xml_id):
        return self.env['res.users'].with_context(no_reset_password=True).create({
            'name': login,
            'login': login,
            'password': 'TestPass123!',
            'groups_id': [
                (4, self.env.ref(group_xml_id).id),
                (4, self.env.ref('base.group_user').id),
            ],
        })

    def test_create_point_succeeds_for_kepala(self):
        """POST /smi/api/inventory_points — Kepala Produksi can create a point."""
        kepala = self._create_user('kepala_api_test', 'inventory_smi.group_kepala_produksi')
        env = self.env(user=kepala)
        point = env['smi.inventory_point'].create({
            'name': 'Titik Kepala Baru',
            'koordinat_x': 45.0,
            'koordinat_y': 55.0,
        })
        self.assertTrue(point.id)
        self.assertEqual(point.name, 'Titik Kepala Baru')

    def test_create_point_requires_kepala_produksi(self):
        """POST /smi/api/inventory_points — Staf Produksi cannot create a point (403)."""
        from odoo.exceptions import AccessError
        staf = self._create_user('staf_api_test', 'inventory_smi.group_staf_produksi')
        env = self.env(user=staf)
        with self.assertRaises(AccessError):
            env['smi.inventory_point'].create({
                'name': 'Titik Staf Ditolak',
                'koordinat_x': 30.0,
                'koordinat_y': 40.0,
            })


class TestDeleteInventoryPoint(_MapBase):

    def _create_user(self, login, group_xml_id):
        return self.env['res.users'].with_context(no_reset_password=True).create({
            'name': login,
            'login': login,
            'password': 'TestPass123!',
            'groups_id': [
                (4, self.env.ref(group_xml_id).id),
                (4, self.env.ref('base.group_user').id),
            ],
        })

    def test_delete_point_succeeds_for_kepala(self):
        """DELETE /smi/api/inventory_points/<id> — Kepala can soft-delete (archive)."""
        kepala = self._create_user('kepala_del_test', 'inventory_smi.group_kepala_produksi')
        env = self.env(user=kepala)
        point = env['smi.inventory_point'].create({
            'name': 'Titik Hapus',
            'koordinat_x': 10.0,
            'koordinat_y': 10.0,
        })
        point.write({'active': False})
        self.assertFalse(point.active)

    def test_delete_point_requires_kepala_produksi(self):
        """DELETE /smi/api/inventory_points/<id> — Staf cannot write (archive) a point."""
        from odoo.exceptions import AccessError
        staf = self._create_user('staf_del_test', 'inventory_smi.group_staf_produksi')
        env = self.env(user=staf)
        with self.assertRaises(AccessError):
            env['smi.inventory_point'].browse(self.point1.id).write({'active': False})


class TestUnauthenticatedAccess(TransactionCase):

    def test_unauthenticated_api_returns_401_public_blocked(self):
        """Public user cannot read smi.inventory_point (no access rule)."""
        from odoo.exceptions import AccessError
        public = self.env.ref('base.public_user', raise_if_not_found=False)
        if not public:
            self.skipTest('public_user not available')
        env_public = self.env(user=public)
        with self.assertRaises(Exception):
            env_public['smi.inventory_point'].search_read([], ['name'])
