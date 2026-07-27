"use client"

import { useState } from "react"
import { CheckCircle2Icon, SendIcon, UsersIcon } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

const RECIPIENTS = [
  { name: "Harbor Point Capital", entity: "Institutional LP", email: "investor-relations@h•••••••.com" },
  { name: "Ridgeline Family Office", entity: "Family Office LP", email: "reporting@r•••••••.com" },
  { name: "Cascadia Pension Trust", entity: "Institutional LP", email: "ops@c•••••••.com" },
  { name: "Elena Marsh", entity: "Individual LP", email: "e.marsh@•••••.com" },
  { name: "Northfield Endowment", entity: "Institutional LP", email: "reports@n•••••••.org" },
]

export function DistributionPanel() {
  const [sent, setSent] = useState(false)
  const [sending, setSending] = useState(false)

  function handleSend() {
    setSending(true)
    setTimeout(() => {
      setSending(false)
      setSent(true)
    }, 900)
  }

  return (
    <Card className="glow-border print:hidden">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-1.5">
          <UsersIcon className="size-4 text-primary" />
          Distribution List
        </CardTitle>
        <span className="text-xs text-muted-foreground">{RECIPIENTS.length} recipients</span>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <ul className="flex flex-col gap-2">
          {RECIPIENTS.map((r) => (
            <li key={r.name} className="glow-border-hover flex items-center justify-between rounded-lg p-2.5 text-sm">
              <div className="flex flex-col">
                <span className="text-foreground">{r.name}</span>
                <span className="text-xs text-muted-foreground">
                  {r.entity} · {r.email}
                </span>
              </div>
              {sent && (
                <Badge variant="outline" className="border-primary/30 text-primary">
                  <CheckCircle2Icon className="size-3" />
                  Sent
                </Badge>
              )}
            </li>
          ))}
        </ul>
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">
            {sent ? "Distribution simulated — no real email was sent." : "Simulated distribution — demonstrates the automation workflow only."}
          </span>
          <Button type="button" onClick={handleSend} disabled={sending || sent}>
            <SendIcon />
            {sent ? "Sent" : sending ? "Sending..." : "Send to Distribution List"}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
