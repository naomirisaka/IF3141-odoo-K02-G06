from odoo import http
from odoo.http import request
import io
import csv
import subprocess
import tempfile
import os


class ReportController(http.Controller):
    @http.route('/smi/api/report/stock', auth='user', methods=['GET'], csrf=False)
    def stock_report(self, **kw):
        fmt = kw.get('format', 'csv').lower()
        date_from = kw.get('from')
        date_to = kw.get('to')

        Stock = request.env['smi.stock_entry']
        domain = []
        if date_from:
            domain.append(('tanggal_masuk', '>=', date_from))
        if date_to:
            domain.append(('tanggal_masuk', '<=', date_to))
        entries = Stock.search(domain, order='tanggal_masuk')

        rows = []
        for e in entries:
            rows.append({
                'tanggal_masuk': e.tanggal_masuk or '',
                'material': e.material_id.name if e.material_id else '',
                'inventory_point': e.inventory_point_id.name if e.inventory_point_id else '',
                'jumlah_awal': e.jumlah_awal,
                'jumlah_tersisa': e.jumlah_tersisa,
                'state': e.state,
                'keterangan': e.keterangan or '',
            })

        if fmt == 'csv':
            sio = io.StringIO()
            writer = csv.writer(sio)
            writer.writerow(['Tanggal Masuk', 'Material', 'Titik', 'Jumlah Awal', 'Jumlah Tersisa', 'State', 'Keterangan'])
            for r in rows:
                writer.writerow([r['tanggal_masuk'], r['material'], r['inventory_point'], r['jumlah_awal'], r['jumlah_tersisa'], r['state'], r['keterangan']])
            data = sio.getvalue().encode('utf-8')
            headers = [
                ('Content-Type', 'text/csv; charset=utf-8'),
                ('Content-Disposition', 'attachment; filename=stock_report.csv'),
            ]
            return request.make_response(data, headers)

        if fmt == 'pdf':
            # Render QWeb template to HTML
            html = request.env['ir.ui.view'].render_template('inventory_smi.report_stock_template', {'entries': entries, 'rows': rows, 'date_from': date_from, 'date_to': date_to})
            # check common locations for wkhtmltopdf
            candidates = ['/usr/local/bin/wkhtmltopdf', '/usr/bin/wkhtmltopdf', '/bin/wkhtmltopdf']
            wkpath = None
            for c in candidates:
                if os.path.exists(c) and os.access(c, os.X_OK):
                    wkpath = c
                    break
            if not wkpath:
                return request.not_found()

            with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tf_html:
                tf_html.write(html.encode('utf-8'))
                tf_html.flush()
                html_path = tf_html.name

            tmp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            tmp_pdf.close()
            try:
                cmd = [wkpath, '--enable-local-file-access', html_path, tmp_pdf.name]
                subprocess.check_call(cmd)
                with open(tmp_pdf.name, 'rb') as f:
                    pdf_bytes = f.read()
                headers = [('Content-Type', 'application/pdf'), ('Content-Disposition', 'attachment; filename=stock_report.pdf')]
                return request.make_response(pdf_bytes, headers)
            finally:
                try:
                    os.unlink(html_path)
                    os.unlink(tmp_pdf.name)
                except Exception:
                    pass

        return request.not_found()
