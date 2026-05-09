import json

from odoo import http
from odoo.http import request, Response
from odoo.exceptions import AccessError


def _json_response(data, status=200):
    return Response(
        json.dumps(data, default=str),
        status=status,
        content_type='application/json',
    )


def _require_auth():
    if not request.session.uid:
        return _json_response({'error': 'Tidak terautentikasi'}, 401)
    return None


def _require_kepala():
    err = _require_auth()
    if err:
        return err
    if not request.env.user.has_group('inventory_smi.group_kepala_produksi') \
            and not request.env.user.has_group('inventory_smi.group_admin'):
        return _json_response({'error': 'Akses ditolak'}, 403)
    return None


def _point_summary(point):
    entries = point.stock_entry_ids.filtered(lambda e: e.state == 'tersedia')
    materials = []
    for entry in entries:
        materials.append({
            'entry_id': entry.id,
            'material_id': entry.material_id.id,
            'material_name': entry.material_id.name,
            'jumlah_tersisa': entry.jumlah_tersisa,
            'jumlah_awal': entry.jumlah_awal,
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


class SmiMapApiController(http.Controller):

    # ------------------------------------------------------------------
    # GET /smi/api/inventory_points
    # ------------------------------------------------------------------

    @http.route(
        '/smi/api/inventory_points',
        type='http', auth='user', methods=['GET'], csrf=False,
    )
    def get_inventory_points(self, material_id=None, **kwargs):
        domain = [('active', '=', True)]
        points = request.env['smi.inventory_point'].search(domain)

        if material_id:
            try:
                mid = int(material_id)
            except (ValueError, TypeError):
                return _json_response({'error': 'material_id tidak valid'}, 400)
            points = points.filtered(
                lambda p: mid in p.stock_entry_ids.filtered(
                    lambda e: e.state == 'tersedia'
                ).mapped('material_id').ids
            )

        data = {'points': [_point_summary(p) for p in points]}
        return _json_response(data)

    # ------------------------------------------------------------------
    # GET /smi/api/inventory_points/<id>
    # ------------------------------------------------------------------

    @http.route(
        '/smi/api/inventory_points/<int:point_id>',
        type='http', auth='user', methods=['GET'], csrf=False,
    )
    def get_inventory_point(self, point_id, **kwargs):
        point = request.env['smi.inventory_point'].browse(point_id)
        if not point.exists() or not point.active:
            return _json_response({'error': 'Titik tidak ditemukan'}, 404)

        all_entries = point.stock_entry_ids
        entries_detail = []
        for entry in all_entries:
            entries_detail.append({
                'entry_id': entry.id,
                'material_id': entry.material_id.id,
                'material_name': entry.material_id.name,
                'jumlah_awal': entry.jumlah_awal,
                'jumlah_tersisa': entry.jumlah_tersisa,
                'satuan': entry.material_id.uom_id.name,
                'state': entry.state,
                'tanggal_masuk': (
                    entry.tanggal_masuk.isoformat() if entry.tanggal_masuk else None
                ),
                'catatan': entry.catatan or '',
                'user': entry.user_id.name or '',
            })

        data = {
            'id': point.id,
            'name': point.name,
            'x': point.koordinat_x,
            'y': point.koordinat_y,
            'deskripsi': point.deskripsi or '',
            'entries': entries_detail,
        }
        return _json_response(data)

    # ------------------------------------------------------------------
    # POST /smi/api/inventory_points  (Kepala / Admin only)
    # ------------------------------------------------------------------

    @http.route(
        '/smi/api/inventory_points',
        type='http', auth='user', methods=['POST'], csrf=False,
    )
    def create_inventory_point(self, **kwargs):
        err = _require_kepala()
        if err:
            return err

        name = kwargs.get('name', '').strip()
        if not name:
            return _json_response({'error': 'Nama titik wajib diisi'}, 400)
        try:
            x = float(kwargs.get('koordinat_x', 50))
            y = float(kwargs.get('koordinat_y', 50))
        except (ValueError, TypeError):
            return _json_response({'error': 'Koordinat tidak valid'}, 400)

        try:
            point = request.env['smi.inventory_point'].create({
                'name': name,
                'koordinat_x': x,
                'koordinat_y': y,
                'deskripsi': kwargs.get('deskripsi', ''),
            })
        except Exception as exc:
            return _json_response({'error': str(exc)}, 400)

        return _json_response({'id': point.id, 'name': point.name}, 201)

    # ------------------------------------------------------------------
    # POST /smi/api/inventory_points/<id>/archive  (Kepala / Admin only)
    # ------------------------------------------------------------------

    @http.route(
        '/smi/api/inventory_points/<int:point_id>/archive',
        type='http', auth='user', methods=['POST'], csrf=False,
    )
    def delete_inventory_point(self, point_id, **kwargs):
        err = _require_kepala()
        if err:
            return err

        point = request.env['smi.inventory_point'].browse(point_id)
        if not point.exists():
            return _json_response({'error': 'Titik tidak ditemukan'}, 404)

        # prevent deletion if there are still available stock entries in this point
        entries_available = point.stock_entry_ids.filtered(lambda e: e.state == 'tersedia')
        if entries_available:
            return _json_response({'error': 'Titik masih memiliki stok, pindahkan stok terlebih dahulu'}, 400)

        try:
            point.write({'active': False})
        except AccessError:
            return _json_response({'error': 'Akses ditolak'}, 403)

        # log point deletion in activity log
        try:
            request.env['smi.activity.log']._log(
                'titik_dihapus',
                'Menghapus titik inventori: %s' % (point.name or ''),
                ref_model='smi.inventory_point',
                ref_id=point.id,
            )
        except Exception:
            pass

        # notify clients to update map
        try:
            request.env['bus.bus']._sendone(
                'smi_point_change',
                {
                    'type': 'point_deleted',
                    'id': point.id,
                    'name': point.name,
                },
            )
        except Exception:
            pass

        return _json_response({'success': True, 'id': point_id})

    # ------------------------------------------------------------------
    # GET /smi/api/materials
    # ------------------------------------------------------------------

    @http.route(
        '/smi/api/materials',
        type='http', auth='user', methods=['GET'], csrf=False,
    )
    def get_materials(self, **kwargs):
        materials = request.env['smi.material'].search([('active', '=', True)])
        data = {
            'materials': [
                {
                    'id': m.id,
                    'name': m.name,
                    'satuan': m.uom_id.name,
                    'kategori': m.category_id.name,
                    'total_stok': m.total_stok,
                    'stok_minimum': m.stok_minimum,
                    'is_low_stock': m.is_low_stock,
                    'last_added_date': (
                        m.last_added_date.isoformat() if m.last_added_date else None
                    ),
                }
                for m in materials
            ]
        }
        return _json_response(data)
