from odoo import http
from odoo.http import request
import io
import csv
import subprocess
import tempfile
import os
import logging
from datetime import datetime
from werkzeug.exceptions import NotFound

_logger = logging.getLogger(__name__)


def _clean_text(value):
    text = str(value or '')
    text = text.replace('\r', ' ').replace('\n', ' ').strip()
    return text


class ReportController(http.Controller):
    @http.route('/smi/api/report/stock', auth='user', methods=['GET'], csrf=False)
    def stock_report(self, **kw):
        user = request.env.user
        if not user.has_group('inventory_smi.group_direktur'):
            _logger.warning(f'Unauthorized report access attempt by {user.name}')
            raise NotFound()

        fmt = kw.get('format', 'csv').lower()
        date_from = kw.get('from')
        date_to = kw.get('to')
        _logger.info(f'Generating {fmt.upper()} report from {date_from} to {date_to}')

        try:
            Stock = request.env['smi.stock_entry']
            domain = []
            if date_from:
                domain.append(('tanggal_masuk', '>=', date_from))
            if date_to:
                domain.append(('tanggal_masuk', '<=', date_to))
            entries = Stock.search(domain, order='tanggal_masuk')
            _logger.info(f'Found {len(entries)} stock entries')

            rows = []
            for e in entries:
                rows.append({
                    'tanggal_masuk': e.tanggal_masuk or '',
                    'material': _clean_text(e.material_id.name if e.material_id else ''),
                    'inventory_point': _clean_text(e.inventory_point_id.name if e.inventory_point_id else ''),
                    'jumlah_awal': e.jumlah_awal,
                    'jumlah_tersisa': e.jumlah_tersisa,
                    'state': _clean_text(e.state),
                    'catatan': _clean_text(getattr(e, 'catatan', '')),
                })

            if fmt == 'csv':
                sio = io.StringIO(newline='')
                writer = csv.writer(sio, lineterminator='\n')
                writer.writerow(['Tanggal Masuk', 'Material', 'Titik', 'Jumlah Awal', 'Jumlah Tersisa', 'State', 'Catatan'])
                for r in rows:
                    writer.writerow([
                        r['tanggal_masuk'],
                        r['material'],
                        r['inventory_point'],
                        r['jumlah_awal'],
                        r['jumlah_tersisa'],
                        r['state'],
                        r['catatan'],
                    ])
                data = sio.getvalue().encode('utf-8-sig')
                headers = [
                    ('Content-Type', 'text/csv; charset=utf-8'),
                    ('Content-Disposition', 'attachment; filename=stock_report.csv'),
                ]
                _logger.info(f'CSV report generated successfully ({len(data)} bytes)')
                return request.make_response(data, headers)

            elif fmt == 'pdf':
                # Find wkhtmltopdf
                candidates = ['/usr/local/bin/wkhtmltopdf', '/usr/bin/wkhtmltopdf', '/bin/wkhtmltopdf']
                wkpath = None
                for c in candidates:
                    if os.path.exists(c) and os.access(c, os.X_OK):
                        wkpath = c
                        _logger.info(f'Found wkhtmltopdf at {c}')
                        break
                
                if not wkpath:
                    _logger.error('wkhtmltopdf binary not found in any candidate location')
                    raise NotFound()

                try:
                    html = request.env['ir.qweb']._render(
                        'inventory_smi.report_stock_template',
                        {
                            'entries': entries,
                            'rows': rows,
                            'date_from': date_from,
                            'date_to': date_to,
                            'generated_on': datetime.now().strftime('%d %B %Y %H:%M'),
                        }
                    )
                    if isinstance(html, bytes):
                        html = html.decode('utf-8', errors='ignore')
                    _logger.info(f'Template rendered successfully ({len(html)} chars)')
                except Exception as e:
                    _logger.error(f'Template render error: {str(e)}', exc_info=True)
                    raise NotFound()

                # Convert to PDF
                with tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w', encoding='utf-8') as tf_html:
                    tf_html.write(html)
                    tf_html.flush()
                    html_path = tf_html.name

                tmp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
                tmp_pdf.close()
                pdf_path = tmp_pdf.name

                try:
                    cmd = [wkpath, '--enable-local-file-access', html_path, pdf_path]
                    _logger.info(f'Running wkhtmltopdf: {" ".join(cmd)}')
                    result = subprocess.run(cmd, capture_output=True, timeout=30, text=True)
                    
                    if result.returncode != 0:
                        _logger.error(f'wkhtmltopdf failed with code {result.returncode}')
                        _logger.error(f'stderr: {result.stderr}')
                        _logger.error(f'stdout: {result.stdout}')
                        raise NotFound()

                    with open(pdf_path, 'rb') as f:
                        pdf_bytes = f.read()
                    
                    _logger.info(f'PDF generated successfully ({len(pdf_bytes)} bytes)')
                    headers = [
                        ('Content-Type', 'application/pdf'),
                        ('Content-Disposition', 'attachment; filename=stock_report.pdf')
                    ]
                    return request.make_response(pdf_bytes, headers)
                
                finally:
                    try:
                        os.unlink(html_path)
                        os.unlink(pdf_path)
                    except Exception as e:
                        _logger.warning(f'Failed to cleanup temp files: {str(e)}')

        except NotFound:
            raise
        except Exception as e:
            _logger.error(f'Unexpected error in stock_report: {str(e)}', exc_info=True)
            raise NotFound()

        raise NotFound()
