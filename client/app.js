const $ = (s) => document.querySelector(s)
const $$ = (s) => Array.from(document.querySelectorAll(s))
const API_BASE = () => window.API_BASE || "http://127.0.0.1:8000" // 기본값
let __lastRedactedBlob = null

// ===============================
// 간단 정규화 유틸
// ===============================
const digitsOnly = (s) => String(s || '').replace(/\D+/g, '')
const lower = (s) => String(s || '').toLowerCase()

function normalizeByRule(rule, value) {
  switch (rule) {
    case 'email': return lower(value)
    case 'rrn':
    case 'fgn':
    case 'card':
    case 'phone_mobile':
    case 'phone_city':
    case 'bizno':
      return digitsOnly(value)
    default:
      return String(value || '').trim()
  }
}

// ===============================
// 규칙 목록 불러오기
// ===============================
async function loadRules() {
  try {
    const resp = await fetch(`${API_BASE()}/text/rules`)
    if (!resp.ok) throw new Error(`rules ${resp.status}`)
    const rules = await resp.json()
    const container = $('#rules-container')
    container.innerHTML = ''
    rules.forEach(rule => {
      const label = document.createElement('label')
      label.className = "block"
      label.innerHTML = `<input type="checkbox" name="rule" value="${rule}" checked> ${rule}`
      container.appendChild(label)
    })
  } catch (err) {
    console.error("규칙 불러오기 실패:", err)
    $('#rules-container').textContent = '규칙을 불러오지 못했습니다.'
  }
}
document.addEventListener('DOMContentLoaded', loadRules)

// ===============================
// PDF 미리보기
// ===============================
async function renderPdfPreview(file) {
  const canvas = $('#pdf-preview')
  const g = canvas.getContext('2d')
  if (!file || file.type !== 'application/pdf') {
    g.clearRect(0, 0, canvas.width, canvas.height)
    return
  }
  const arr = await file.arrayBuffer()
  const pdf = await pdfjsLib.getDocument({ data: arr }).promise
  const page = await pdf.getPage(1)
  const viewport = page.getViewport({ scale: 1.2 })
  canvas.width = viewport.width
  canvas.height = viewport.height
  await page.render({ canvasContext: g, viewport }).promise
}

// ===============================
// 파일 변경 시 초기화
// ===============================
$('#file')?.addEventListener('change', async (e) => {
  try { await renderPdfPreview(e.target.files[0]) } catch (_) {}
  __lastRedactedBlob = null
  const saveBtn = $('#btn-save-redacted')
  if (saveBtn) {
    saveBtn.classList.add('hidden')
    saveBtn.setAttribute('disabled', 'disabled')
  }
})

// ===============================
// 스캔 실행 (추출 → match)
// ===============================
$('#btn-scan')?.addEventListener('click', async () => {
  const f = $('#file').files[0]
  if (!f) {
    alert('파일을 선택하세요')
    return
  }
  $('#status').textContent = '처리 중...'

  const ext = f.name.split('.').pop().toLowerCase()

  try {
    const fd = new FormData()
    fd.append('file', f)

    // 추출
    const extResp = await fetch(`${API_BASE()}/text/extract`, {
      method: 'POST',
      body: fd,
    })
    if (!extResp.ok) throw new Error(`extract ${extResp.status}`)
    const extData = await extResp.json()

    // 미리보기
    if (ext === 'pdf') {
      $('#pdf-preview-block').classList.remove('hidden')
      $('#text-preview-block').classList.remove('hidden')
      await renderPdfPreview(f)
    } else if (ext === 'xls') {
      $('#pdf-preview-block').classList.add('hidden')
      $('#text-preview-block').classList.remove('hidden')
    } else {
      $('#pdf-preview-block').classList.add('hidden')
      $('#text-preview-block').classList.remove('hidden')
    }
    $('#txt-out').value = extData.full_text || ''

    // 매칭
    const rules = $$('input[name="rule"]:checked').map((x) => x.value)
    const body = { text: extData.full_text, rules, normalize: true }
    const matchResp = await fetch(`${API_BASE()}/text/match`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!matchResp.ok) throw new Error(`match ${matchResp.status}`)
    const res = await matchResp.json()

    // 결과 표시
    $('#match-result-block').classList.remove('hidden')
    const tbody = $('#result-rows')
    tbody.innerHTML = ''
    for (const r of res.items) {
      const tr = document.createElement('tr')
      tr.className = 'border-b align-top'
      const ctx = String(r.context).replace(/</g, '&lt;')
      const highlighted = ctx.replace(
        r.value,
        `<mark class="bg-yellow-200 text-black font-semibold">${r.value}</mark>`
      )
      tr.innerHTML = `
        <td class="py-2 px-2 mono">${r.rule}</td>
        <td class="py-2 px-2 mono">${r.value}</td>
        <td class="py-2 px-2 ${r.valid ? 'text-emerald-700' : 'text-rose-700'}">
          ${r.valid ? 'OK' : 'FAIL'}
        </td>
        <td class="py-2 px-2 mono context">${highlighted}</td>`
      tbody.appendChild(tr)
    }
    $('#summary').textContent =
      '검출: ' +
      Object.entries(res.counts).map(([k, v]) => `${k}=${v}`).join(', ')

    // 상태 표시
    if (ext === 'xls') {
      $('#status').textContent = '완료 (XLS 텍스트 추출)'
    } else {
      $('#status').textContent = `완료 (${ext.toUpperCase()} 처리)`
    }
  } catch (err) {
    console.error(err)
    $('#status').textContent = '오류: ' + (err?.message || err)
  }
})

// ===============================
// 레닥션 PDF 저장 (PDF 전용)
// ===============================
$('#btn-save-redacted')?.addEventListener('click', () => {
  if (!__lastRedactedBlob) {
    alert('레닥션된 파일이 없습니다')
    return
  }
  const a = document.createElement('a')
  a.href = URL.createObjectURL(__lastRedactedBlob)
  a.download = 'redacted.pdf'
  a.click()
})
