import type { AssetClass, Holding, AllocationSlice, PeriodReturn, CapitalAccountSummary, InvestorReportSnapshot } from "@/lib/data/report"

export type { AssetClass, Holding, AllocationSlice, PeriodReturn, CapitalAccountSummary, InvestorReportSnapshot }

export interface ReportMetadata {
  id: string
  name: string
  createdAt: string
  updatedAt: string
  status: "draft" | "in_review" | "approved" | "exported"
  version: number
  createdBy?: string
}

export interface ReportData extends InvestorReportSnapshot {
  metadata?: ReportMetadata
}

export interface FeedbackItem {
  id: string
  reportId: string
  author: string
  section: string
  comment: string
  status: "open" | "addressed" | "resolved"
  createdAt: string
  resolvedAt?: string
  suggestedChanges?: string
}

export interface ImportSource {
  type: "file" | "manual" | "api"
  filename?: string
  rawData?: any
}

export interface ImportResult {
  success: boolean
  data?: Partial<ReportData>
  errors?: string[]
  warnings?: string[]
}
