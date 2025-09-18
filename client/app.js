const $  = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
const API_BASE = () => window.API_BASE; // HTML에서 세팅됨

async function renderPdfPreview(file){
    const canvas = $('#pdf-preview');
    const g = canvas.getContext('2d');
    if (!file || file.type !== 'application/pdf') {
    g.clearRect(0, 0, canvas.width, canvas.height);
    return;
    }
    const arr = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument({ data: arr }).promise;
    const page = await pdf.getPage(1);
    const viewport = page.getViewport({ scale: 1.2 });
    canvas.width = viewport.width;
    canvas.height = viewport.height;
    await page.render({ canvasContext: g, viewport }).promise;
}

$('#file')?.addEventListener('change', async (e) => {
    try { await renderPdfPreview(e.target.files[0]); } catch(_) {}
});

$('#btn-scan')?.addEventListener('click', async () => {
    const f = $('#file').files[0];
    if (!f) { alert('파일을 선택하세요'); return; }
    $('#status').textContent = '처리 중...';

    try {
    // 1) 업로드 → 텍스트 추출
    const fd = new FormData();
    fd.append('file', f);
    const ext = await fetch(`${API_BASE()}/extract`, { method: 'POST', body: fd })
        .then(r => r.json());

    // 2) 선택한 규칙만 서버에 전달
    const rules = $$('input[name="rule"]:checked').map(x => x.value);
    const body = { text: ext.full_text, rules };

    const res = await fetch(`${API_BASE()}/match`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    }).then(r => r.json());

    // 3) 결과 렌더
    $('#txt-out').value = ext.full_text;

    const tbody = $('#result-rows'); 
    tbody.innerHTML = '';
    for (const r of res.items) {
        const tr = document.createElement('tr'); 
        tr.className = 'border-b align-top';
        tr.innerHTML = `
        <td class="py-2 px-2 mono">${r.rule}</td>
        <td class="py-2 px-2 mono">${r.value}</td>
        <td class="py-2 px-2 ${r.valid ? 'text-emerald-700' : 'text-rose-700'}">${r.valid ? 'OK' : 'FAIL'}</td>
        <td class="py-2 px-2 mono">${String(r.context).replace(/</g,'&lt;')}</td>
        `;
        tbody.appendChild(tr);
    }

    $('#summary').textContent =
        '검출: ' + Object.entries(res.counts).map(([k,v]) => `${k}=${v}`).join(', ');
    window.__lastReport = { createdAt: new Date().toISOString(), ...res };
    $('#status').textContent = '완료';
    } catch (err) {
    console.error(err);
    $('#status').textContent = '오류: ' + (err?.message || err);
    }
});

$('#btn-export')?.addEventListener('click', () => {
    const report = window.__lastReport || { createdAt: new Date().toISOString(), note: 'no data' };
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'deid_report.json';
    a.click();
});
