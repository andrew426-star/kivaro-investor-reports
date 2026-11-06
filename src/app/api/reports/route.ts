import { NextRequest, NextResponse } from "next/server"
import { reportStorage } from "@/lib/storage/reports"
import { getInvestorReportSnapshot } from "@/lib/data/report"

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const id = searchParams.get("id")
    
    if (id) {
      const report = reportStorage.getReport(id)
      if (!report) {
        return NextResponse.json({ error: "Report not found" }, { status: 404 })
      }
      const feedback = reportStorage.getFeedback(id)
      return NextResponse.json({ report, feedback })
    }
    
    const reports = reportStorage.getAllReports()
    return NextResponse.json({ reports })
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to fetch reports" },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const action = body.action
    
    if (action === "create_from_sample") {
      const snapshot = getInvestorReportSnapshot()
      const report = reportStorage.createReport(snapshot)
      return NextResponse.json({ report })
    }
    
    if (action === "create") {
      const report = reportStorage.createReport(body.data)
      return NextResponse.json({ report })
    }
    
    return NextResponse.json({ error: "Invalid action" }, { status: 400 })
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to create report" },
      { status: 500 }
    )
  }
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json()
    const { id, updates } = body
    
    if (!id) {
      return NextResponse.json({ error: "Report ID required" }, { status: 400 })
    }
    
    const report = reportStorage.updateReport(id, updates)
    if (!report) {
      return NextResponse.json({ error: "Report not found" }, { status: 404 })
    }
    
    return NextResponse.json({ report })
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to update report" },
      { status: 500 }
    )
  }
}
