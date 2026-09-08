import { Add, Document, Image, TrashCan } from '@carbon/icons-react'
import { Alert, Button, Card } from '@heroui/react'
import { useEffect, useRef, useState, type FormEvent } from 'react'

import { useAuth } from '../auth/AuthProvider'
import { ClaimsApiError, getEvidenceContent } from './claimsApi'
import { useUploadEvidence } from './useClaims'
import type { EvidenceCategory, EvidenceItem, EvidenceUploadItem } from './types'

const categoryLabel: Record<EvidenceCategory, string> = {
  VEHICLE_DAMAGE_IMAGE: 'Vehicle damage images',
  ID_CARD: 'ID cards',
  INSURANCE_POLICY: 'Insurance policies',
  VEHICLE_REGISTRATION: 'Vehicle registrations',
  DRIVER_LICENSE: 'Driver licenses',
  OTHER_DOCUMENT: 'Other documents',
}

const categories = Object.keys(categoryLabel) as EvidenceCategory[]

type EvidencePanelProps = {
  claimId: string
  evidence: EvidenceItem[]
}

export function EvidencePanel({ claimId, evidence }: EvidencePanelProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const uploadEvidence = useUploadEvidence(claimId)
  const [items, setItems] = useState<EvidenceUploadItem[]>([])
  const [error, setError] = useState('')

  function addFiles(fileList: FileList | null) {
    if (!fileList) return
    setItems((current) => [
      ...current,
      ...Array.from(fileList).map((file) => ({ file, category: 'VEHICLE_DAMAGE_IMAGE' as const })),
    ])
  }

  function updateCategory(index: number, category: EvidenceCategory) {
    setItems((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, category } : item)))
  }

  async function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!items.length) return
    setError('')
    try {
      await uploadEvidence.mutateAsync(items)
      setItems([])
      if (inputRef.current) inputRef.current.value = ''
    } catch (caughtError) {
      setError(caughtError instanceof ClaimsApiError ? caughtError.message : 'Unable to upload evidence')
    }
  }

  return (
    <Card className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <Card.Header className="flex flex-col gap-4 border-b border-slate-100 px-6 py-5 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-lg bg-cyan-50 text-cyan-700 ring-1 ring-cyan-100"><Document size={20} /></div>
          <div>
            <Card.Title className="text-lg text-slate-950">Evidence</Card.Title>
            <Card.Description className="text-sm text-slate-500">Damage photos and supporting claim documents.</Card.Description>
          </div>
        </div>
        <Button onPress={() => inputRef.current?.click()} variant="outline"><Add size={18} />Select files</Button>
        <input
          aria-label="Select evidence files"
          className="sr-only"
          multiple
          onChange={(event) => addFiles(event.target.files)}
          ref={inputRef}
          type="file"
        />
      </Card.Header>
      <Card.Content className="grid gap-6 p-6">
        {items.length ? (
          <form className="grid gap-3 border-b border-slate-100 pb-6" onSubmit={submitUpload}>
            {error ? <Alert status="danger"><Alert.Title>Upload failed</Alert.Title><Alert.Description>{error}</Alert.Description></Alert> : null}
            {items.map((item, index) => (
              <div className="grid gap-3 border border-slate-200 p-3 sm:grid-cols-[minmax(0,1fr)_12rem_auto] sm:items-center" key={`${item.file.name}-${item.file.lastModified}-${index}`}>
                <div className="min-w-0"><p className="truncate text-sm font-medium text-slate-950">{item.file.name}</p><p className="mt-1 text-xs text-slate-500">{formatFileSize(item.file.size)}</p></div>
                <label className="grid gap-1 text-xs font-semibold text-slate-600">
                  Category
                  <select aria-label={`Category for ${item.file.name}`} className="h-9 border border-slate-300 bg-white px-2 text-sm text-slate-900" onChange={(event) => updateCategory(index, event.target.value as EvidenceCategory)} value={item.category}>
                    {categories.map((category) => <option key={category} value={category}>{categoryLabel[category]}</option>)}
                  </select>
                </label>
                <Button aria-label={`Remove ${item.file.name}`} onPress={() => setItems((current) => current.filter((_, itemIndex) => itemIndex !== index))} variant="ghost"><TrashCan size={18} /></Button>
              </div>
            ))}
            <div className="flex justify-end"><Button isPending={uploadEvidence.isPending} type="submit" variant="primary">Upload evidence</Button></div>
          </form>
        ) : null}

        {evidence.length ? <EvidenceGroups evidence={evidence} /> : <p className="text-sm text-slate-500">No evidence has been uploaded to this claim.</p>}
      </Card.Content>
    </Card>
  )
}

function EvidenceGroups({ evidence }: { evidence: EvidenceItem[] }) {
  return (
    <div className="grid gap-6">
      {categories.map((category) => {
        const groupedEvidence = evidence.filter((item) => item.category === category)
        if (!groupedEvidence.length) return null
        return <section className="grid gap-3" key={category}><h2 className="text-sm font-semibold text-slate-950">{categoryLabel[category]}</h2><div className="grid gap-3 sm:grid-cols-2">{groupedEvidence.map((item) => <EvidenceItemCard item={item} key={item.id} />)}</div></section>
      })}
    </div>
  )
}

function EvidenceItemCard({ item }: { item: EvidenceItem }) {
  const isDamageImage = item.category === 'VEHICLE_DAMAGE_IMAGE' && item.content_type?.startsWith('image/')
  return <article className="overflow-hidden border border-slate-200 bg-slate-50"><div className="flex min-h-28 items-center justify-center bg-slate-100">{isDamageImage ? <EvidencePreview item={item} /> : <Document className="text-slate-500" size={28} />}</div><div className="p-3"><p className="truncate text-sm font-medium text-slate-950">{item.original_filename}</p><p className="mt-1 text-xs text-slate-500">{formatFileSize(item.file_size)}</p></div></article>
}

function EvidencePreview({ item }: { item: EvidenceItem }) {
  const { session } = useAuth()
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)

  useEffect(() => {
    let objectUrl: string | null = null
    let active = true
    getEvidenceContent(item.content_url, session!.access_token)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob)
        if (active) setPreviewUrl(objectUrl)
      })
      .catch(() => active && setPreviewUrl(null))
    return () => {
      active = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [item.content_url, session])

  return previewUrl ? <img alt={item.original_filename} className="h-32 w-full object-cover" src={previewUrl} /> : <Image className="text-slate-500" size={28} />
}

function formatFileSize(fileSize: number) {
  if (fileSize < 1024) return `${fileSize} B`
  return `${Math.round(fileSize / 1024)} KB`
}
