import { v4 as uuidv4 } from "uuid"
import type { ReportData, FeedbackItem } from "@/lib/types/report"

class ReportStorage {
  private reports: Map<string, ReportData> = new Map()
  private feedback: Map<string, FeedbackItem[]> = new Map()

  createReport(data: ReportData): ReportData {
    const id = uuidv4()
    const now = new Date().toISOString()
    const report: ReportData = {
      ...data,
      metadata: {
        id,
        name: data.reportTitle || "Investor Report",
        createdAt: now,
        updatedAt: now,
        status: "draft",
        version: 1,
      },
    }
    this.reports.set(id, report)
    this.feedback.set(id, [])
    return report
  }

  getReport(id: string): ReportData | undefined {
    return this.reports.get(id)
  }

  getAllReports(): ReportData[] {
    return Array.from(this.reports.values()).sort((a, b) => 
      new Date(b.metadata?.updatedAt || 0).getTime() - new Date(a.metadata?.updatedAt || 0).getTime()
    )
  }

  updateReport(id: string, updates: Partial<ReportData>): ReportData | undefined {
    const report = this.reports.get(id)
    if (!report) return undefined
    const now = new Date().toISOString()
    const updated: ReportData = {
      ...report,
      ...updates,
      metadata: {
        id: report.metadata?.id || id,
        name: updates.reportTitle || report.metadata?.name || report.reportTitle,
        createdAt: report.metadata?.createdAt || now,
        updatedAt: now,
        status: updates.metadata?.status || report.metadata?.status || "draft",
        version: (report.metadata?.version || 1) + 1,
        createdBy: report.metadata?.createdBy,
      },
    }
    this.reports.set(id, updated)
    return updated
  }

  deleteReport(id: string): boolean {
    this.feedback.delete(id)
    return this.reports.delete(id)
  }

  addFeedback(feedback: Omit<FeedbackItem, "id" | "createdAt">): FeedbackItem {
    const id = uuidv4()
    const item: FeedbackItem = {
      ...feedback,
      id,
      createdAt: new Date().toISOString(),
    }
    const list = this.feedback.get(feedback.reportId) || []
    list.push(item)
    this.feedback.set(feedback.reportId, list)
    return item
  }

  getFeedback(reportId: string): FeedbackItem[] {
    return this.feedback.get(reportId) || []
  }

  updateFeedback(feedbackId: string, reportId: string, updates: Partial<FeedbackItem>): FeedbackItem | undefined {
    const list = this.feedback.get(reportId) || []
    const idx = list.findIndex(f => f.id === feedbackId)
    if (idx === -1) return undefined
    list[idx] = { ...list[idx], ...updates }
    this.feedback.set(reportId, list)
    return list[idx]
  }
}

export const reportStorage = new ReportStorage()
