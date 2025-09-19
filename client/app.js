const $  = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
const API_BASE = () => window.API_BASE; // index.html에서 세팅됨
let __lastRedactedBlob = null;          // 레닥션된 PDF blob 저장용

async function renderPdfPreview(file) {
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

// 파일 변경 시 미리보기 + 저장 버튼 초기화
$('#file')?.addEventListener('change', async (e) => {
    try { await renderPdfPreview(e.target.files[0]); } catch (_) {}
    __lastRedactedBlob = null;
    const saveBtn = $('#btn-save-redacted');
    if (saveBtn) { saveBtn.classList.add('hidden'); saveBtn.setAttribute('disabled', 'disabled'); }
});

// 스캔 실행: 추출 → 탐지/렌더 → 좌표탐지 → 레닥션 적용
$('#btn-scan')?.addEventListener('click', async () => {
    const f = $('#file').files[0];
    if (!f) { alert('파일을 선택하세요'); return; }
    $('#status').textContent = '처리 중...';

    try {
    // 업로드 → 텍스트 추출
    const fd = new FormData();
    fd.append('file', f);
    const extResp = await fetch(`${API_BASE()}/extract`, { method: 'POST', body: fd });
    if (!extResp.ok) throw new Error(`extract ${extResp.status}`);
    const ext = await extResp.json();

    // 선택 규칙만 서버에 전달 (정규화는 서버 측 코드가 수행)
    const rules = $$('input[name="rule"]:checked').map(x => x.value);
    const body = { text: ext.full_text, rules };
    const matchResp = await fetch(`${API_BASE()}/match`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    if (!matchResp.ok) throw new Error(`match ${matchResp.status}`);
    const res = await matchResp.json();

    // 화면 렌더
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
        <td class="py-2 px-2 mono">${String(r.context).replace(/</g,'&lt;')}</td>`;
        tbody.appendChild(tr);
    }
    $('#summary').textContent = '검출: ' + Object.entries(res.counts).map(([k, v]) => `${k}=${v}`).join(', ');

    //  PDF일 때만 좌표 탐지
    let boxes = [];
    if (f.type === 'application/pdf') {
        const fd2 = new FormData();
        fd2.append('file', f);
        const detResp = await fetch(`${API_BASE()}/redactions/detect`, { method: 'POST', body: fd2 });
        if (!detResp.ok) throw new Error(`detect ${detResp.status}`);
        const det = await detResp.json();
        boxes = det.boxes || [];
    }

    // PDF이고 박스가 있으면 레닥션 적용 → blob 저장 → 저장 버튼 활성화
    __lastRedactedBlob = null;
    const saveBtn = $('#btn-save-redacted');

    if (f.type === 'application/pdf' && boxes.length > 0) {
      const req = { boxes, fill: 'black' }; // 기본 검정 마스킹
        const fd3 = new FormData();
        fd3.append('file', f);
        fd3.append('req', JSON.stringify(req));

        const redResp = await fetch(`${API_BASE()}/redactions/apply`, { method: 'POST', body: fd3 });
        if (!redResp.ok) {
        const t = await redResp.text();
        throw new Error(`apply ${redResp.status}: ${t}`);
        }

        __lastRedactedBlob = await redResp.blob();
        if (saveBtn) {
        saveBtn.classList.remove('hidden');
        saveBtn.removeAttribute('disabled');
        }
        $('#status').textContent = `완료 (레닥션 ${boxes.length}개)`;
    } else {
        if (saveBtn) { saveBtn.classList.add('hidden'); saveBtn.setAttribute('disabled', 'disabled'); }
        $('#status').textContent = '완료 (레닥션 대상 없음 또는 PDF 아님)';
    }
    } catch (err) {
    console.error(err);
    $('#status').textContent = '오류: ' + (err?.message || err);
    }
});

// 레닥션 PDF 저장
$('#btn-save-redacted')?.addEventListener('click', () => {
    if (!__lastRedactedBlob) { alert('레닥션된 파일이 없습니다'); return; }
    const a = document.createElement('a');
    a.href = URL.createObjectURL(__lastRedactedBlob);
    a.download = 'redacted.pdf';
    a.click();
});
