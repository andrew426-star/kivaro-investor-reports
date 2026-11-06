"use client"

import { useEffect, useState } from "react"
import { useParams } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ArrowLeftIcon, DownloadIcon, PrinterIcon } from "lucide-react"
import Link from "next/link"

export default function ExportPage() {
  const params = useParams()
  const id = params.id as string
  const [exporting, setExporting] = useState(false)

  function exportPDF() {
    setExporting(true)
    window.print()
    setTimeout(() => setExporting(false), 1000)
  }

  function exportHTML() {
    const blob = new Blob([document.documentElement.outerHTML], { type: "text/html" })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "investor-report.html"
    a.click()
  }

  return (
    <div className="mx-auto max-w-3xl p-6 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Export & Distribute</h1>
        <Link href={"/report/" + id}><Button variant="outline"><ArrowLeftIcon className="size-4" />Back to Report</Button></Link>
      </div>
      <Card>
        <CardHeader><CardTitle>Export Options</CardTitle></CardHeader>
        <CardContent className="flex flex-col gap-3">
          <Button onClick={exportPDF} disabled={exporting}><PrinterIcon className="size-4" />{exporting ? "Preparing..." : "Export as PDF (Print)"}</Button>
          <Button variant="outline" onClick={exportHTML}><DownloadIcon className="size-4" />Download as HTML</Button>
          <p className="text-xs text-muted-foreground">Use Print to PDF from your browser for best PDF results. HTML export preserves styling.</p>
        </CardContent>
      </Card>
    </div>
  )
}
