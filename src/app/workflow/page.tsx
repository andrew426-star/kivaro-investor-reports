"use client"

import { useState } from "react"
import { DataImport } from "@/components/workflow/data-import"
import { WorkflowStepper } from "@/components/workflow/workflow-stepper"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { ArrowRightIcon, FileTextIcon } from "lucide-react"
import Link from "next/link"

const STEPS = [
  { id: "import", title: "Import Data", description: "Drop files or enter data" },
  { id: "generate", title: "Generate Report", description: "Create investor report" },
  { id: "review", title: "Review & Iterate", description: "Analyst feedback" },
  { id: "export", title: "Export & Distribute", description: "Finalize & share" },
]

export default function WorkflowPage() {
  const [currentStep, setCurrentStep] = useState(0)
  const [importData, setImportData] = useState<any>(null)
  const [reportId, setReportId] = useState<string | null>(null)

  async function handleImportComplete(data: any) {
    setImportData(data)

    try {
      const res = await fetch("/api/reports", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "create_from_sample" }),
      })
      const result = await res.json()
      setReportId(result.report.metadata.id)
      setCurrentStep(1)
    } catch (err) {
      console.error(err)
    }
  }

  function handleGenerate() {
    setCurrentStep(2)
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 py-6 sm:px-8">
      <header className="flex flex-col gap-1 py-2">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-xs tracking-[0.2em] text-muted-foreground uppercase">
              Drop-and-Generate Workflow
            </span>
            <h1 className="font-heading text-2xl text-gradient-green sm:text-3xl">
              Investor Report Generator
            </h1>
            <p className="text-sm text-muted-foreground">
              Transform raw data into a polished investor report with AI commentary and analyst iteration
            </p>
          </div>
          <Link href="/">
            <Button variant="outline">View Current Report</Button>
          </Link>
        </div>
      </header>

      <WorkflowStepper currentStep={currentStep} steps={STEPS} />

      <Card className="glow-border">
        <CardContent className="p-6">
          {currentStep === 0 && (
            <div className="flex flex-col gap-4">
              <h2 className="text-lg font-semibold">Step 1: Bring in Your Data</h2>
              <p className="text-sm text-muted-foreground">
                Upload portfolio data, financial statements, or any relevant files. You can also use sample data or enter manually.
              </p>
              <DataImport onImportComplete={handleImportComplete} />
            </div>
          )}

          {currentStep === 1 && (
            <div className="flex flex-col gap-4">
              <h2 className="text-lg font-semibold">Step 2: Generate Investor Report</h2>
              <p className="text-sm text-muted-foreground">
                We'll generate a comprehensive report with performance metrics, portfolio composition, and AI-powered commentary.
              </p>
              <div className="flex gap-2">
                {reportId && (
                  <Link href={`/report/${reportId}`}>
                    <Button>
                      <FileTextIcon className="size-4" />
                      Generate & View Report
                    </Button>
                  </Link>
                )}
                <Button variant="outline" onClick={() => setCurrentStep(0)}>Back</Button>
                <Button onClick={handleGenerate}>
                  Continue to Review
                  <ArrowRightIcon className="size-4" />
                </Button>
              </div>
            </div>
          )}

          {currentStep === 2 && (
            <div className="flex flex-col gap-4">
              <h2 className="text-lg font-semibold">Step 3: Review & Iterate with Analyst Feedback</h2>
              <p className="text-sm text-muted-foreground">
                Add feedback, request changes, and iterate until the report meets analyst standards.
              </p>
              <div className="flex gap-2">
                {reportId && (
                  <Link href={`/report/${reportId}/review`}>
                    <Button>Open Review Workspace</Button>
                  </Link>
                )}
                <Button variant="outline" onClick={() => setCurrentStep(1)}>Back</Button>
                <Button onClick={() => setCurrentStep(3)}>
                  Continue to Export
                  <ArrowRightIcon className="size-4" />
                </Button>
              </div>
            </div>
          )}

          {currentStep === 3 && (
            <div className="flex flex-col gap-4">
              <h2 className="text-lg font-semibold">Step 4: Export & Distribute</h2>
              <p className="text-sm text-muted-foreground">
                Export your completed report as PDF or prepare for distribution to stakeholders.
              </p>
              <div className="flex gap-2">
                {reportId && (
                  <Link href={`/report/${reportId}/export`}>
                    <Button>Export Options</Button>
                  </Link>
                )}
                <Button variant="outline" onClick={() => setCurrentStep(2)}>Back</Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
