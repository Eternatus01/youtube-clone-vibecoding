/** 2110 -> "35:10"; 4272 -> "1:11:12" */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || !Number.isFinite(seconds) || seconds < 0) return ''
  const s = Math.floor(seconds)
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  const mm = h > 0 ? String(m).padStart(2, '0') : String(m)
  const ss = String(sec).padStart(2, '0')
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`
}

/** Russian plural: pluralRu(1, ['просмотр','просмотра','просмотров']) -> "просмотр" */
export function pluralRu(n: number, forms: [string, string, string]): string {
  const n10 = n % 10
  const n100 = n % 100
  if (n10 === 1 && n100 !== 11) return forms[0]
  if (n10 >= 2 && n10 <= 4 && (n100 < 12 || n100 > 14)) return forms[1]
  return forms[2]
}

function plural(n: number, forms: [string, string, string]): string {
  return pluralRu(n, forms)
}

function ruDecimal(s: string): string {
  return s.replace('.', ',')
}

/** 1234 -> "1,2 тыс. просмотров"; 123 -> "123 просмотра" */
export function formatViews(views: number | null | undefined): string {
  if (views == null || !Number.isFinite(views) || views < 0) return '0 просмотров'
  if (views < 1000) {
    const n = Math.round(views)
    return `${n} ${plural(n, ['просмотр', 'просмотра', 'просмотров'])}`
  }
  if (views < 1_000_000) {
    const k = views / 1000
    const short = k < 100 ? trimZero(k.toFixed(1)) : String(Math.round(k))
    return `${ruDecimal(short)} тыс. просмотров`
  }
  const m = views / 1_000_000
  const short = m < 100 ? trimZero(m.toFixed(1)) : String(Math.round(m))
  return `${ruDecimal(short)} млн просмотров`
}

/** 1234 -> "1,2 тыс. подписчиков"; 123 -> "123 подписчика" */
export function formatSubscribers(subs: number | null | undefined): string {
  if (subs == null || !Number.isFinite(subs) || subs < 0) return '0 подписчиков'
  if (subs < 1000) {
    const n = Math.round(subs)
    return `${n} ${plural(n, ['подписчик', 'подписчика', 'подписчиков'])}`
  }
  if (subs < 1_000_000) {
    const k = subs / 1000
    const short = k < 100 ? trimZero(k.toFixed(1)) : String(Math.round(k))
    return `${ruDecimal(short)} тыс. подписчиков`
  }
  const m = subs / 1_000_000
  const short = m < 100 ? trimZero(m.toFixed(1)) : String(Math.round(m))
  return `${ruDecimal(short)} млн подписчиков`
}

function trimZero(s: string): string {
  return s.endsWith('.0') ? s.slice(0, -2) : s
}

/** Relative age: "только что", "3 минуты назад", "2 месяца назад" */
export function timeAgo(iso: string | Date): string {
  const date = typeof iso === 'string' ? new Date(iso) : iso
  if (Number.isNaN(date.getTime())) return ''
  const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000))
  if (seconds < 60) return 'только что'
  const units: Array<[number, [string, string, string]]> = [
    [60, ['минуту', 'минуты', 'минут']],
    [60, ['час', 'часа', 'часов']],
    [24, ['день', 'дня', 'дней']],
    [7, ['неделю', 'недели', 'недель']],
    [4.345, ['месяц', 'месяца', 'месяцев']],
    [Number.POSITIVE_INFINITY, ['год', 'года', 'лет']],
  ]
  let value = seconds
  for (const [step, forms] of units) {
    if (value < step) {
      const v = Math.max(1, Math.floor(value))
      return `${v} ${plural(v, forms)} назад`
    }
    value /= step
  }
  return ''
}

/** "3 months ago" style short form for card badges */
export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) return ''
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let value = bytes
  let i = 0
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024
    i++
  }
  return `${i === 0 ? value : value.toFixed(1)} ${units[i]}`
}
