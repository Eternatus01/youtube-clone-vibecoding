/**
 * Upload a file to a presigned URL with real progress reporting.
 * Uses XHR (not fetch) because fetch has no upload progress events.
 */
export function putFile(
  url: string,
  file: File,
  onProgress: (percent: number) => void,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('PUT', url)
    if (file.type) {
      // Presigned PUT URLs are usually signed for a specific content type.
      xhr.setRequestHeader('Content-Type', file.type)
    }
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        onProgress(Math.min(100, Math.round((e.loaded / e.total) * 100)))
      }
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve()
      } else {
        reject(new Error(`Upload failed (HTTP ${xhr.status})`))
      }
    }
    xhr.onerror = () => reject(new Error('Network error during upload'))
    xhr.onabort = () => reject(new Error('Upload cancelled'))
    xhr.send(file)
  })
}
