import { NextRequest, NextResponse } from "next/server"
import { reportStorage } from "@/lib/storage/reports"

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const reportId = searchParams.get("reportId")
    
    if (!reportId) {
      return NextResponse.json({ error: "Report ID required" }, { status: 400 })
    }
    
    const feedback = reportStorage.getFeedback(reportId)
    return NextResponse.json({ feedback })
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to fetch feedback" },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { reportId, author, section, comment, suggestedChanges } = body
    
    if (!reportId || !comment) {
      return NextResponse.json({ error: "Report ID and comment required" }, { status: 400 })
    }
    
    const feedback = reportStorage.addFeedback({
      reportId,
      author: author || "Analyst",
      section: section || "general",
      comment,
      status: "open",
      suggestedChanges,
    })
    
    return NextResponse.json({ feedback })
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to add feedback" },
      { status: 500 }
    )
  }
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json()
    const { feedbackId, reportId, updates } = body
    
    if (!feedbackId || !reportId) {
      return NextResponse.json({ error: "Feedback ID and Report ID required" }, { status: 400 })
    }
    
    const feedback = reportStorage.updateFeedback(feedbackId, reportId, updates)
    if (!feedback) {
      return NextResponse.json({ error: "Feedback not found" }, { status: 404 })
    }
    
    return NextResponse.json({ feedback })
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to update feedback" },
      { status: 500 }
    )
  }
}
