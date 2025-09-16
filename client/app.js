const $ = (s)=>document.querySelector(s);
const $$= (s)=>Array.from(document.querySelectorAll(s));

const API_BASE = () => window.API_BASE;
$("#api-url").textContent = API_BASE();
$("#api-input").value = API_BASE();
$("#api-save").addEventListener("click", ()=>{
    const v = $("#api-input").value.trim();
    if(!v) return;
    localStorage.setItem("API_BASE", v);
    window.API_BASE = v;
    $("#api-url").textContent = v;
});

async function renderPdfPreview(file){
    if(!file || file.type!=='application/pdf'){
    const c = $('#pdf-preview'); const g = c.getContext('2d');
    g.clearRect(0,0,c.width,c.height); return;
    }
    const arr = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument({data: arr}).promise;
    const page = await pdf.getPage(1);
    const viewport = page.getViewport({scale: 1.2});
    const canvas = $('#pdf-preview');
    canvas.width = viewport.width; canvas.height = viewport.height;
    await page.render({canvasContext: canvas.getContext('2d'), viewport}).promise;
}

$('#file').addEventListener('change', async (e)=>{
    await renderPdfPreview(e.target.files[0]).catch(()=>{});
});

$('#btn-scan').addEventListener('click', async ()=>{
    const f = $('#file').files[0];
    if(!f){ alert('파일을 선택하세요'); return; }
    $('#status').textContent = '처리 중...';

    try{
    // 1) 서버에 파일 업로드 → 텍스트 추출
    const fd = new FormData();
    fd.append('file', f);
    const ext = await fetch(`${API_BASE()}/extract`, { method:'POST', body: fd })
        .then(r=>r.json());

    // 2) /match 호출(서버에서 정규화/검증 수행)
    const rules = $$('input[name="rule"]:checked').map(x=>x.value);
    const body = {
        text: ext.full_text,
        rules,
        options: { rrn_checksum: $('#opt-rrn-checksum').checked },
        normalize: $('#opt-normalize').checked
    };
    const res = await fetch(`${API_BASE()}/match`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify(body)
    }).then(r=>r.json());

    // 3) 결과 렌더
    $('#txt-out').value = body.normalize ? body.text ?? ext.full_text : ext.full_text;

    const tbody = $('#result-rows'); tbody.innerHTML = '';
    for(const r of res.items){
        const tr = document.createElement('tr'); tr.className='border-b align-top';
        tr.innerHTML = `
        <td class="py-2 px-2 mono">${r.rule}</td>
        <td class="py-2 px-2 mono">${r.value}</td>
        <td class="py-2 px-2 ${r.valid?'text-emerald-700':'text-rose-700'}">${r.valid?'OK':'FAIL'}</td>
        <td class="py-2 px-2 mono">${r.context.replace(/</g,'&lt;')}</td>
        `;
        tbody.appendChild(tr);
    }
    $('#summary').textContent = '검출: ' + Object.entries(res.counts).map(([k,v])=>`${k}=${v}`).join(', ');
    window.__lastReport = { createdAt: new Date().toISOString(), ...res };
    $('#status').textContent = '완료';
    }catch(err){
    console.error(err);
    $('#status').textContent = '오류: ' + (err?.message||err);
    }
});

$('#btn-export').addEventListener('click', ()=>{
    const report = window.__lastReport || { createdAt: new Date().toISOString(), note: 'no data' };
    const blob = new Blob([JSON.stringify(report, null, 2)], {type:'application/json'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'deid_report.json';
    a.click();
});
