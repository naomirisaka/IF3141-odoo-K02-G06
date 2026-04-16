from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class _OrderBase(TransactionCase):
    """Shared setup: 1 material + 3 stock entries at different dates."""

    def setUp(self):
        super().setUp()
        self.uom = self.env['smi.uom'].create({'name': 'Lembar-order'})
        self.cat = self.env['smi.material.category'].create({'name': 'Kertas-order'})
        self.material = self.env['smi.material'].create({
            'name': 'Kertas Art 120gsm',
            'uom_id': self.uom.id,
            'category_id': self.cat.id,
        })
        self.point_a = self.env['smi.inventory_point'].create(
            {'name': 'Titik A', 'koordinat_x': 10.0, 'koordinat_y': 10.0})
        self.point_b = self.env['smi.inventory_point'].create(
            {'name': 'Titik B', 'koordinat_x': 20.0, 'koordinat_y': 20.0})
        self.point_c = self.env['smi.inventory_point'].create(
            {'name': 'Titik C', 'koordinat_x': 30.0, 'koordinat_y': 30.0})

        # Three entries: oldest 50, mid 30, newest 20
        self.entry1 = self.env['smi.stock_entry'].create({
            'material_id': self.material.id,
            'inventory_point_id': self.point_a.id,
            'jumlah_awal': 50.0,
            'tanggal_masuk': '2026-01-01 08:00:00',
        })
        self.entry2 = self.env['smi.stock_entry'].create({
            'material_id': self.material.id,
            'inventory_point_id': self.point_b.id,
            'jumlah_awal': 30.0,
            'tanggal_masuk': '2026-01-05 08:00:00',
        })
        self.entry3 = self.env['smi.stock_entry'].create({
            'material_id': self.material.id,
            'inventory_point_id': self.point_c.id,
            'jumlah_awal': 20.0,
            'tanggal_masuk': '2026-01-10 08:00:00',
        })

    def _make_order(self, jumlah, mode='auto'):
        order = self.env['smi.order'].create({
            'name': 'Test Order',
            'tanggal': '2026-02-01',
        })
        self.env['smi.order.line'].create({
            'order_id': order.id,
            'material_id': self.material.id,
            'jumlah_dibutuhkan': jumlah,
            'mode_pick': mode,
        })
        return order


class TestFIFO(_OrderBase):

    def test_fifo_picks_oldest_first(self):
        """Auto FIFO takes from oldest entry first."""
        order = self._make_order(30.0)
        order.action_confirm()
        picks = order.order_line_ids[0].order_pick_ids
        self.assertEqual(picks[0].stock_entry_id.id, self.entry1.id)

    def test_fifo_splits_across_entries_when_needed(self):
        """Needing 70 units takes all 50 from entry1 + 20 from entry2."""
        order = self._make_order(70.0)
        order.action_confirm()
        line = order.order_line_ids[0]
        picks = line.order_pick_ids.sorted('stock_entry_id')
        taken = {p.stock_entry_id.id: p.jumlah_diambil for p in picks}
        self.assertEqual(taken.get(self.entry1.id), 50.0)
        self.assertEqual(taken.get(self.entry2.id), 20.0)

    def test_fifo_exact_amount_exhausts_entry(self):
        """Taking exactly 50 units sets entry1.state='habis'."""
        order = self._make_order(50.0)
        order.action_confirm()
        self.entry1.invalidate_recordset()
        self.assertEqual(self.entry1.state, 'habis')

    def test_fifo_creates_correct_order_picks(self):
        """smi.order.pick records created with correct jumlah_diambil per entry."""
        order = self._make_order(50.0)
        order.action_confirm()
        picks = order.order_line_ids[0].order_pick_ids
        self.assertEqual(len(picks), 1)
        self.assertEqual(picks[0].jumlah_diambil, 50.0)

    def test_fifo_updates_jumlah_tersisa_correctly(self):
        """stock_entry.jumlah_tersisa reduced correctly after FIFO."""
        order = self._make_order(30.0)
        order.action_confirm()
        self.entry1.invalidate_recordset()
        self.assertEqual(self.entry1.jumlah_tersisa, 20.0)

    def test_fifo_100_percent_accuracy_no_overshoot(self):
        """Total diambil across all picks == jumlah_dibutuhkan exactly."""
        order = self._make_order(75.0)
        order.action_confirm()
        line = order.order_line_ids[0]
        total = sum(p.jumlah_diambil for p in line.order_pick_ids)
        self.assertAlmostEqual(total, 75.0, places=6)


class TestStockAvailabilityCheck(_OrderBase):

    def test_insufficient_stock_raises_validation_error(self):
        """Confirming order with insufficient stock raises ValidationError."""
        order = self._make_order(200.0)
        with self.assertRaises(ValidationError):
            order.action_confirm()

    def test_sufficient_stock_allows_confirmation(self):
        """Confirming order with sufficient stock succeeds."""
        order = self._make_order(50.0)
        order.action_confirm()
        self.assertEqual(order.state, 'dikonfirmasi')

    def test_zero_stock_raises_error(self):
        """Confirming order when material has 0 stock raises error."""
        # exhaust all stock
        self.entry1.write({'jumlah_tersisa': 0.0})
        self.entry2.write({'jumlah_tersisa': 0.0})
        self.entry3.write({'jumlah_tersisa': 0.0})
        order = self._make_order(1.0)
        with self.assertRaises(ValidationError):
            order.action_confirm()

    def test_partial_stock_across_points_aggregated(self):
        """Stock from multiple points is summed for availability check."""
        # total = 50+30+20 = 100, request 99 should work
        order = self._make_order(99.0)
        order.action_confirm()
        self.assertEqual(order.state, 'dikonfirmasi')


class TestManualPick(_OrderBase):

    def test_manual_pick_total_must_equal_needed(self):
        """Manual picks not summing to jumlah_dibutuhkan raises ValidationError."""
        order = self._make_order(50.0, mode='manual')
        line = order.order_line_ids[0]
        # add a pick that is short
        self.env['smi.order.pick'].create({
            'order_line_id': line.id,
            'stock_entry_id': self.entry1.id,
            'jumlah_diambil': 30.0,
        })
        with self.assertRaises(ValidationError):
            order.action_confirm()

    def test_manual_pick_cannot_exceed_entry_tersisa(self):
        """Taking more than entry.jumlah_tersisa raises ValidationError."""
        order = self._make_order(60.0, mode='manual')
        line = order.order_line_ids[0]
        self.env['smi.order.pick'].create({
            'order_line_id': line.id,
            'stock_entry_id': self.entry1.id,
            'jumlah_diambil': 60.0,  # entry1 only has 50
        })
        with self.assertRaises(ValidationError):
            order.action_confirm()

    def test_manual_pick_updates_stock(self):
        """Confirmed manual pick reduces stock_entry.jumlah_tersisa."""
        order = self._make_order(30.0, mode='manual')
        line = order.order_line_ids[0]
        self.env['smi.order.pick'].create({
            'order_line_id': line.id,
            'stock_entry_id': self.entry1.id,
            'jumlah_diambil': 30.0,
        })
        order.action_confirm()
        self.entry1.invalidate_recordset()
        self.assertEqual(self.entry1.jumlah_tersisa, 20.0)


class TestOrderStateTransitions(_OrderBase):

    def test_new_order_is_draft(self):
        """New order starts in state='draft'."""
        order = self._make_order(10.0)
        self.assertEqual(order.state, 'draft')

    def test_confirm_draft_order(self):
        """Draft order can be confirmed → state='dikonfirmasi'."""
        order = self._make_order(10.0)
        order.action_confirm()
        self.assertEqual(order.state, 'dikonfirmasi')

    def test_cannot_confirm_order_with_no_lines(self):
        """Confirming empty order raises ValidationError."""
        order = self.env['smi.order'].create({
            'name': 'Empty Order', 'tanggal': '2026-02-01',
        })
        with self.assertRaises(ValidationError):
            order.action_confirm()

    def test_complete_confirmed_order(self):
        """Confirmed order can be set to selesai."""
        order = self._make_order(10.0)
        order.action_confirm()
        order.action_complete()
        self.assertEqual(order.state, 'selesai')

    def test_cancel_draft_order(self):
        """Draft order can be cancelled."""
        order = self._make_order(10.0)
        order.action_cancel()
        self.assertEqual(order.state, 'dibatalkan')

    def test_cannot_edit_confirmed_order(self):
        """Editing confirmed order raises error."""
        order = self._make_order(10.0)
        order.action_confirm()
        with self.assertRaises(ValidationError):
            order.write({'name': 'Changed'})
