const $ = (s) => document.querySelector(s)
const $$ = (s) => Array.from(document.querySelectorAll(s))
const API_BASE = () => window.API_BASE // index.html에서 세팅됨
let __lastRedactedBlob = null // 레닥션된 PDF blob 저장용

// 간단 정규화 유틸
const digitsOnly = (s) => String(s || '').replace(/\D+/g, '')
const lower = (s) => String(s || '').toLowerCase()

// 규칙별 비교용 정규화 함수
function normalizeByRule(rule, value) {
  switch (rule) {
    case 'email':
      return lower(value)
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
// 규칙 목록 불러오기 → 체크박스 생성 (선택적)
// ===============================
async function loadRules() {
  const container = $('#rules-container')
  if (!container) {
    // index.html에 정적 체크박스가 있는 경우: 동적 렌더링 생략
    return
  }
  try {
    const resp = await fetch(`${API_BASE()}/text/rules`)
    if (!resp.ok) throw new Error(`rules ${resp.status}`)
    const rules = await resp.json()

    container.innerHTML = ''
    rules.forEach((rule) => {
      const label = document.createElement('label')
      label.className = 'block'
      label.innerHTML = `<input type="checkbox" name="rule" value="${rule}" checked> ${rule}`
      container.appendChild(label)
    })
  } catch (err) {
    console.error('규칙 불러오기 실패:', err)
    container.textContent = '규칙을 불러오지 못했습니다.'
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
// 파일 변경 시 → 미리보기 & 버튼 초기화
// ===============================
$('#file')?.addEventListener('change', async (e) => {
  try {
    await renderPdfPreview(e.target.files[0])
  } catch (_) {}
  __lastRedactedBlob = null
  const saveBtn = $('#btn-save-redacted')
  if (saveBtn) {
    saveBtn.classList.add('hidden')
    saveBtn.setAttribute('disabled', 'disabled')
  }
})

// ===============================
// 스캔 실행 (추출 → match → detect → apply)
// ===============================
$('#btn-scan')?.addEventListener('click', async () => {
  const f = $('#file').files[0]
  if (!f) {
    alert('파일을 선택하세요')
    return
  }
  $('#status').textContent = '처리 중...'

  try {
    // 1. 텍스트 추출
    const fd = new FormData()
    fd.append('file', f)
    const extResp = await fetch(`${API_BASE()}/text/extract`, {
      method: 'POST',
      body: fd,
    })
    if (!extResp.ok) throw new Error(`extract ${extResp.status}`)
    const ext = await extResp.json()

    // 2. match
    const rules = $$('input[name="rule"]:checked').map((x) => x.value)
    const body = {
      text: ext.full_text,
      rules,
      normalize: true,
    }
    const matchResp = await fetch(`${API_BASE()}/text/match`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!matchResp.ok) throw new Error(`match ${matchResp.status}`)
    const res = await matchResp.json()

    // 결과 렌더링
    $('#txt-out').value = ext.full_text
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
      Object.entries(res.counts)
        .map(([k, v]) => `${k}=${v}`)
        .join(', ')

    // 3. detect (PDF일 때만)
    let boxes = []
    if (f.type === 'application/pdf') {
      const fd2 = new FormData()
      fd2.append('file', f)
      const detResp = await fetch(`${API_BASE()}/redactions/detect`, {
        method: 'POST',
        body: fd2,
      })
      if (!detResp.ok) throw new Error(`detect ${detResp.status}`)
      const det = await detResp.json()

      // match(valid=True) 기준으로 detect 결과 필터링 (정규화 비교)
      const validMap = new Map() // rule -> Set(normalized values)
      for (const it of res.items) {
        if (!it.valid) continue
        const key = it.rule
        const norm = normalizeByRule(it.rule, it.value)
        if (!validMap.has(key)) validMap.set(key, new Set())
        validMap.get(key).add(norm)
      }

      boxes = (det.boxes || []).filter((b) => {
        const rule = b.pattern_name || ''
        const set = validMap.get(rule)
        if (!set) return false
        const norm = normalizeByRule(rule, b.matched_text)
        return set.has(norm)
      })
    }

    // 4. apply (PDF + box 있을 때만)
    __lastRedactedBlob = null
    const saveBtn = $('#btn-save-redacted')

    if (f.type === 'application/pdf' && boxes.length > 0) {
      const req = { boxes, fill: 'black' }
      const fd3 = new FormData()
      fd3.append('file', f)
      fd3.append('req', JSON.stringify(req))

      const redResp = await fetch(`${API_BASE()}/redactions/apply`, {
        method: 'POST',
        body: fd3,
      })
      if (!redResp.ok) {
        const t = await redResp.text()
        throw new Error(`apply ${redResp.status}: ${t}`)
      }

      __lastRedactedBlob = await redResp.blob()
      if (saveBtn) {
        saveBtn.classList.remove('hidden')
        saveBtn.removeAttribute('disabled')
      }
      $('#status').textContent = `완료 (레닥션 ${boxes.length}개)`
    } else {
      if (saveBtn) {
        saveBtn.classList.add('hidden')
        saveBtn.setAttribute('disabled', 'disabled')
      }
      $('#status').textContent = '완료 (레닥션 대상 없음 또는 PDF 아님)'
    }
  } catch (err) {
    console.error(err)
    $('#status').textContent = '오류: ' + (err?.message || err)
  }
})

// 레닥션 PDF 저장
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
