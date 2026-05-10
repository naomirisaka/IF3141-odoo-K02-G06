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

    function download(fmt) {
      const url = buildUrl(fmt);
      // create a hidden link to preserve session cookie
      const a = document.createElement('a');
      a.href = url;
      a.style.display = 'none';
      document.body.appendChild(a);
      a.click();
      a.remove();
    }

    btnCsv.addEventListener('click', function (e) { e.preventDefault(); download('csv'); });
    btnPdf.addEventListener('click', function (e) { e.preventDefault(); download('pdf'); });
  } catch (err) { console.error('report_download init error', err); }
});
