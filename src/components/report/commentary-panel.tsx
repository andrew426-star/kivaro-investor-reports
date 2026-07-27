"use client"

import { useEffect, useState } from "react"
import { Loader2Icon, RefreshCwIcon, SparklesIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface NotableHolding {
  symbol: string
  note: string
}

interface Commentary {
  performanceCommentary: string
  notableHoldings: NotableHolding[]
  marketContext: string
  outlookNote: string
}

type CommentaryState =
  | { status: "loading" }
  | { status: "ready"; commentary: Commentary }
  | { status: "error"; message: string }

export function CommentaryPanel() {
  const [state, setState] = useState<CommentaryState>({ status: "loading" })

  async function loadCommentary() {
    setState({ status: "loading" })
    try {
      const res = await fetch("/api/commentary", { method: "POST" })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || "Failed to generate commentary.")
      setState({ status: "ready", commentary: data.commentary })
    } catch (err) {
      setState({ status: "error", message: err instanceof Error ? err.message : "Failed to generate commentary." })
    }
  }

  useEffect(() => {
    loadCommentary()
  }, [])

  return (
    <Card className="glow-border print-avoid-break">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-1.5">
          <SparklesIcon className="size-4 text-primary" />
          Market & Portfolio Commentary
        </CardTitle>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          onClick={loadCommentary}
          disabled={state.status === "loading"}
          aria-label="Regenerate commentary"
          className="print:hidden"
        >
          <RefreshCwIcon className={state.status === "loading" ? "animate-spin" : ""} />
        </Button>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {state.status === "loading" && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2Icon className="size-4 animate-spin" />
            Drafting commentary...
          </div>
        )}
        {state.status === "error" && <p className="text-sm text-destructive">{state.message}</p>}
        {state.status === "ready" && (
          <>
            <p className="text-sm leading-relaxed text-foreground">{state.commentary.performanceCommentary}</p>
            {state.commentary.notableHoldings.length > 0 && (
              <div className="flex flex-col gap-1.5">
                <span className="text-xs tracking-wide text-muted-foreground uppercase">Notable Holdings</span>
                <ul className="flex flex-col gap-1.5">
                  {state.commentary.notableHoldings.map((h) => (
                    <li key={h.symbol} className="text-sm text-foreground">
                      <span className="font-medium">{h.symbol}</span> — {h.note}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <p className="text-sm leading-relaxed text-muted-foreground">{state.commentary.marketContext}</p>
            <p className="text-sm leading-relaxed text-muted-foreground italic">{state.commentary.outlookNote}</p>
          </>
        )}
      </CardContent>
    </Card>
  )
}
