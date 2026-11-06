"use client"

import { useState } from "react"
import { UploadIcon, FileTextIcon, CheckCircle2Icon, AlertCircleIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface DataImportProps {
  onImportComplete: (data: any) => void
}

export function DataImport({ onImportComplete }: DataImportProps) {
  const [dragActive, setDragActive] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleFile(file: File) {
    setUploading(true)
    setError(null)
    setResult(null)

    try {
      const formData = new FormData()
      formData.append("file", file)

      const res = await fetch("/api/import", {
        method: "POST",
        body: formData,
      })

      const data = await res.json()
      if (!res.ok) throw new Error(data.error || "Import failed")

      setResult(data)
      onImportComplete(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed")
    } finally {
      setUploading(false)
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0])
    }
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    e.preventDefault()
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0])
    }
  }

  return (
    <Card className="glow-border">
      <CardHeader>
        <CardTitle className="flex items-center gap-1.5">
          <UploadIcon className="size-4 text-primary" />
          Import Data Source
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div
          className={`relative flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 transition-colors ${
            dragActive ? "border-primary bg-primary/5" : "border-border"
          } ${uploading ? "opacity-50" : ""}`}
          onDragEnter={(e) => { e.preventDefault(); e.stopPropagation(); setDragActive(true) }}
          onDragLeave={(e) => { e.preventDefault(); e.stopPropagation(); setDragActive(false) }}
          onDragOver={(e) => { e.preventDefault(); e.stopPropagation() }}
          onDrop={handleDrop}
        >
          <input
            type="file"
            id="file-upload"
            className="absolute inset-0 cursor-pointer opacity-0"
            onChange={handleChange}
            accept=".csv,.xlsx,.xls,.json"
            disabled={uploading}
          />
          <UploadIcon className="size-8 text-muted-foreground" />
          <div className="text-center">
            <p className="text-sm font-medium">
              {uploading ? "Uploading..." : "Drop files here or click to browse"}
            </p>
            <p className="text-xs text-muted-foreground">
              Supports CSV, Excel (.xlsx, .xls), and JSON
            </p>
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
            <AlertCircleIcon className="size-4" />
            {error}
          </div>
        )}

        {result && (
          <div className="flex items-center gap-2 rounded-lg bg-primary/10 p-3 text-sm text-primary">
            <CheckCircle2Icon className="size-4" />
            Imported {result.filename} successfully - {result.rawData?.length || 0} rows
          </div>
        )}

        <div className="flex flex-col gap-2 text-xs text-muted-foreground">
          <p className="font-medium">Or start from:</p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => window.location.href = "/"}>Use Sample Data</Button>
            <Button variant="outline" size="sm" onClick={() => onImportComplete({ manual: true })}>Manual Entry</Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
