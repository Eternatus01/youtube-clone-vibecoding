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

/** 1234 -> "1.2K views" */
export function formatViews(views: number | null | undefined): string {
  if (views == null || !Number.isFinite(views) || views < 0) return '0 views'
  if (views < 1000) return `${Math.round(views)} views`
  if (views < 1_000_000) {
    const k = views / 1000
    return `${k < 100 ? trimZero(k.toFixed(1)) : Math.round(k)}K views`
  }
  const m = views / 1_000_000
  return `${m < 100 ? trimZero(m.toFixed(1)) : Math.round(m)}M views`
}

function trimZero(s: string): string {
  return s.endsWith('.0') ? s.slice(0, -2) : s
}

/** Relative age: "3 minutes ago", "2 months ago" */
export function timeAgo(iso: string | Date): string {
  const date = typeof iso === 'string' ? new Date(iso) : iso
  if (Number.isNaN(date.getTime())) return ''
  const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000))
  const units: Array<[number, string]> = [
    [60, 'second'],
    [60, 'minute'],
    [24, 'hour'],
    [7, 'day'],
    [4.345, 'week'],
    [12, 'month'],
    [Number.POSITIVE_INFINITY, 'year'],
  ]
  let value = seconds
  for (const [step, name] of units) {
    if (value < step) {
      const v = Math.max(1, Math.floor(value))
      return `${v} ${name}${v === 1 ? '' : 's'} ago`
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
