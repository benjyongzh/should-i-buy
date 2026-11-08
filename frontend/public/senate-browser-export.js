/* Trading Lab: run as a reviewed DevTools Snippet on the normal Senate search page.
   Personal non-commercial use only. No cookies/tokens are exported; no third-party requests.
   This exports CURRENT access evidence, never historical first-public timestamps. */
;(async () => {
  const origin = 'https://efdsearch.senate.gov'
  if (location.origin !== origin)
    throw new Error('Open the official Senate search page normally first.')
  const scopeNote = prompt(
    'Describe the actual selected query: date range, PTR report type, filer types and any name filters. This will remain an unverified scope attestation.',
  )
  if (!scopeNote || scopeNote.length < 20)
    throw new Error('A precise query-scope description is required.')
  const reportPattern = /^\/search\/view\/(ptr|paper)\/[A-Za-z0-9-]+\/?$/
  function sanitize(node) {
    const copy = node.cloneNode(true)
    copy
      .querySelectorAll('script,input[type="hidden"],input[type="password"],meta,iframe')
      .forEach((e) => e.remove())
    copy.querySelectorAll('input').forEach((e) => {
      if (/csrf|token|password/i.test(e.name)) e.remove()
    })
    copy.querySelectorAll('*').forEach((e) =>
      [...e.attributes].forEach((a) => {
        if (/^on/i.test(a.name) || /csrf|token|nonce/i.test(a.name)) e.removeAttribute(a.name)
      }),
    )
    return copy.outerHTML
  }
  const tables = [...document.querySelectorAll('table')]
  const table = tables.find((t) =>
    [...t.querySelectorAll('a[href]')].some((a) =>
      reportPattern.test(new URL(a.href, origin).pathname),
    ),
  )
  if (!table)
    throw new Error(
      'No PTR/paper report table found. Select and submit the intended search normally; do not bypass a challenge.',
    )
  const jq = window.jQuery
  const dt = jq?.fn?.dataTable?.isDataTable(table) ? jq(table).DataTable() : null
  const pages = [],
    urls = new Set()
  async function page(number) {
    if (!dt) return
    if (dt.page.info().page === number) return
    await new Promise((resolve, reject) => {
      const timer = setTimeout(
        () => reject(new Error('Normal table paging timed out; no completion claimed.')),
        30000,
      )
      jq(table).one('draw.dt', () => {
        clearTimeout(timer)
        resolve()
      })
      dt.page(number).draw('page')
    })
  }
  const info = dt?.page.info()
  const totalPages = info?.pages || 1
  if (totalPages > 500)
    throw new Error('Search is too large; split it into explicitly named year queries.')
  for (let number = 0; number < totalPages; number++) {
    await page(number)
    pages.push(sanitize(table))
    for (const a of table.querySelectorAll('a[href]')) {
      const u = new URL(a.href, origin)
      if (u.origin === origin && reportPattern.test(u.pathname) && !u.search && !u.hash)
        urls.add(u.href)
    }
    await new Promise((resolve) => setTimeout(resolve, 500))
  }
  if (urls.size > 10000) throw new Error('Too many reports; split the query.')
  const expected = info?.recordsDisplay ?? urls.size
  const complete = !!dt && urls.size === expected
  const exportId = crypto.randomUUID(),
    chunks = []
  let chunk = []
  for (const url of urls) {
    const response = await fetch(url, { credentials: 'same-origin', redirect: 'error' })
    if ([403, 429].includes(response.status))
      throw new Error(
        'Access denied/rate-limited. Stopped without bypass; narrow the query or use normal downloads.',
      )
    const report = { url, captured_at: new Date().toISOString(), http_status: response.status }
    if ((response.headers.get('Content-Type') || '').includes('pdf')) {
      const bytes = new Uint8Array(await response.arrayBuffer())
      if (bytes.length > 4000000)
        throw new Error('Report exceeds4MB; download and review separately.')
      let binary = ''
      for (let i = 0; i < bytes.length; i += 8192)
        binary += String.fromCharCode(...bytes.subarray(i, i + 8192))
      report.pdf_base64 = btoa(binary)
    } else {
      const html = await response.text()
      const doc = new DOMParser().parseFromString(html, 'text/html')
      report.html = sanitize(doc.body)
    }
    chunk.push(report)
    if (chunk.length === 10) {
      chunks.push(chunk)
      chunk = []
    }
    await new Promise((resolve) => setTimeout(resolve, 500))
  }
  if (chunk.length) chunks.push(chunk)
  for (let index = 0; index < chunks.length; index++) {
    const packet = {
      export_id: exportId,
      part_number: index + 1,
      total_parts: chunks.length,
      scope_note: scopeNote,
      expected_report_count: expected,
      pagination_complete: complete,
      search_pages: index === 0 ? pages : [],
      reports: chunks[index],
      acknowledge_personal_noncommercial_use: true,
    }
    const body = JSON.stringify(packet, null, 2)
    if (new Blob([body]).size > 20000000)
      throw new Error('Export part exceeds20MB; use a smaller search/page query.')
    const href = URL.createObjectURL(new Blob([body], { type: 'application/json' }))
    const a = document.createElement('a')
    a.href = href
    a.download = `senate-${exportId}-${index + 1}-of-${chunks.length}.json`
    a.click()
    URL.revokeObjectURL(href)
    await new Promise((resolve) => setTimeout(resolve, 500))
  }
  console.info(
    'Local export complete:',
    urls.size,
    'reports;',
    chunks.length,
    'parts. Pagination attested:',
    complete,
    '. Historical posting clocks and source eligibility remain unverified.',
  )
})()
