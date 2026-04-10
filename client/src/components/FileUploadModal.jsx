import { useState } from 'react'

const FileUploadModal = ({
  isOpen,
  onClose,
  message,
  jobId,
  hasApi,
  uploadBusy,
  onLiveUpload,
}) => {
  const [fileName, setFileName] = useState('')
  const [file, setFile] = useState(null)

  if (!isOpen) return null

  const submitLive = async () => {
    if (!file) return
    try {
      await onLiveUpload(file)
      setFile(null)
      setFileName('')
      onClose()
    } catch {
      /* parent shows error; keep modal open */
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-sm">
      <div className="glass w-full max-w-lg rounded-2xl p-6">
        <h3 className="text-xl font-semibold text-slate-100">Upload Trace CSV</h3>
        <p className="mt-2 text-sm text-slate-300">
          CSV must include <code className="text-cyan-300">timestamp</code>,{' '}
          <code className="text-cyan-300">lat</code>, <code className="text-cyan-300">lon</code>. Processing uses the
          currently selected pollutant from the top navbar.
        </p>

        <label className="mt-4 block text-sm text-slate-200">
          CSV file
          <input
            type="file"
            accept=".csv"
            className="mt-2 w-full rounded-lg border border-white/20 bg-slate-900/50 p-2 text-slate-100"
            onChange={(event) => {
              const f = event.target.files?.[0] ?? null
              setFile(f)
              setFileName(f?.name ?? '')
            }}
          />
        </label>

        <div className="mt-4 rounded-xl border border-white/10 bg-slate-900/50 p-3 text-xs text-slate-300">
          {message ? <p>{message}</p> : <p className="text-slate-500">No active job yet.</p>}
          {jobId != null ? <p className="mt-1">Job ID: {jobId}</p> : null}
          {fileName ? <p className="mt-1 text-cyan-200">Selected: {fileName}</p> : null}
          {!hasApi ? (
            <p className="mt-2 text-amber-200/90">
              API disabled (<code className="text-cyan-200">VITE_USE_SAMPLE_ONLY</code>). Set it to{' '}
              <code className="text-cyan-200">false</code> and run Flask after ingesting monthly CSVs into
              Postgres.
            </p>
          ) : null}
        </div>

        <div className="mt-6 flex flex-wrap justify-end gap-3">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          {hasApi ? (
            <button
              type="button"
              className="btn btn-primary disabled:opacity-50"
              disabled={!file || uploadBusy}
              onClick={() => void submitLive()}
            >
              {uploadBusy ? 'Processing…' : 'Upload & process'}
            </button>
          ) : null}
        </div>
      </div>
    </div>
  )
}

export default FileUploadModal
