document.addEventListener('DOMContentLoaded', function () {
  try {
    const fromInput = document.getElementById('report_from');
    const toInput = document.getElementById('report_to');
    const btnCsv = document.getElementById('download_csv');
    const btnPdf = document.getElementById('download_pdf');

    if (!fromInput || !toInput || !btnCsv || !btnPdf) return;

    // default: last 30 days
    const now = new Date();
    const toDefault = now.toISOString().slice(0, 10);
    const fromDefault = new Date(now.getTime() - 29 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    if (!fromInput.value) fromInput.value = fromDefault;
    if (!toInput.value) toInput.value = toDefault;

    function buildUrl(fmt) {
      const f = encodeURIComponent(fromInput.value || '');
      const t = encodeURIComponent(toInput.value || '');
      return `/smi/api/report/stock?format=${fmt}&from=${f}&to=${t}`;
    }

    async function download(fmt) {
      try {
        const url = buildUrl(fmt);
        console.log('Downloading report:', url);
        
        // Use fetch with credentials to preserve session
        const response = await fetch(url, {
          method: 'GET',
          credentials: 'same-origin',
          headers: { 'Accept': fmt === 'csv' ? 'text/csv' : 'application/pdf' }
        });
        
        if (!response.ok) {
          console.error('Report download failed:', response.status, response.statusText);
          alert('Gagal mengunduh laporan. Status: ' + response.status);
          return;
        }
        
        // Get content type to validate response
        const contentType = response.headers.get('content-type') || '';
        console.log('Response content-type:', contentType);
        
        // If redirected to login, show error
        if (contentType.includes('text/html')) {
          console.error('Received HTML response - likely redirected to login');
          alert('Sesi Anda telah berakhir. Silakan login kembali.');
          return;
        }
        
        const blob = await response.blob();
        console.log('Blob size:', blob.size, 'bytes');
        
        if (blob.size === 0) {
          alert('Laporan kosong atau tidak ada data.');
          return;
        }
        
        // Create download link
        const blobUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = fmt === 'csv' ? 'laporan_stok.csv' : 'laporan_stok.pdf';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(blobUrl);
        
        console.log('Report downloaded successfully');
        
      } catch (err) {
        console.error('Download error:', err);
        alert('Koneksi gagal: ' + err.message);
      }
    }

    btnCsv.addEventListener('click', function (e) { 
      e.preventDefault(); 
      download('csv'); 
    });
    
    btnPdf.addEventListener('click', function (e) { 
      e.preventDefault(); 
      download('pdf'); 
    });
    
  } catch (err) { console.error('report_download init error', err); }
});
