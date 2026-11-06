"use client"

import { useEffect, useState } from "react"
import { useParams } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ArrowLeftIcon, PlusIcon, CheckCircle2Icon } from "lucide-react"
import Link from "next/link"

export default function ReviewPage() {
  const params = useParams()
  const id = params.id as string
  const [feedback, setFeedback] = useState<any[]>([])
  const [newComment, setNewComment] = useState("")
  const [section, setSection] = useState("general")
  const [author, setAuthor] = useState("Analyst")

  useEffect(() => {
    fetch("/api/feedback?reportId=" + id).then(r => r.json()).then(d => setFeedback(d.feedback || []))
  }, [id])

  async function addFeedback() {
    if (!newComment) return
    const res = await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reportId: id, author, section, comment: newComment })
    })
    const data = await res.json()
    setFeedback([...feedback, data.feedback])
    setNewComment("")
  }

  async function resolveFeedback(fid: string) {
    await fetch("/api/feedback", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ feedbackId: fid, reportId: id, updates: { status: "resolved", resolvedAt: new Date().toISOString() } })
    })
    setFeedback(feedback.map(f => f.id === fid ? { ...f, status: "resolved" } : f))
  }

  return (
    <div className="mx-auto max-w-4xl p-6 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Review & Iteration</h1>
        <Link href={"/report/" + id}><Button variant="outline"><ArrowLeftIcon className="size-4" />Back to Report</Button></Link>
      </div>
      <Card>
        <CardHeader><CardTitle>Add Feedback</CardTitle></CardHeader>
        <CardContent className="flex flex-col gap-2">
          <div className="flex gap-2">
            <input className="flex-1 p-2 rounded bg-secondary" placeholder="Author" value={author} onChange={e => setAuthor(e.target.value)} />
            <select className="p-2 rounded bg-secondary" value={section} onChange={e => setSection(e.target.value)}>
              <option value="general">General</option>
              <option value="performance">Performance</option>
              <option value="holdings">Holdings</option>
              <option value="commentary">Commentary</option>
              <option value="disclosures">Disclosures</option>
            </select>
          </div>
          <textarea className="w-full p-2 rounded bg-secondary" rows={3} placeholder="Add feedback or requested changes..." value={newComment} onChange={e => setNewComment(e.target.value)} />
          <Button onClick={addFeedback}><PlusIcon className="size-4" />Add Feedback</Button>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Feedback Items ({feedback.length})</CardTitle></CardHeader>
        <CardContent className="flex flex-col gap-3">
          {feedback.map(f => (
            <div key={f.id} className="p-3 rounded border border-border flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-medium">{f.author}</span> <span className="text-xs text-muted-foreground">• {f.section} • {new Date(f.createdAt).toLocaleString()}</span>
                </div>
                {f.status === "open" && <Button size="sm" onClick={() => resolveFeedback(f.id)}><CheckCircle2Icon className="size-4" />Mark Resolved</Button>}
                {f.status === "resolved" && <span className="text-xs text-primary">Resolved</span>}
              </div>
              <p className="text-sm">{f.comment}</p>
            </div>
          ))}
          {feedback.length === 0 && <p className="text-sm text-muted-foreground">No feedback yet. Add the first item above.</p>}
        </CardContent>
      </Card>
    </div>
  )
}
