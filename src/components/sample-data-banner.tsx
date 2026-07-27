import { AlertTriangleIcon } from "lucide-react"

export function SampleDataBanner() {
  return (
    <div className="glow-border flex items-center justify-center gap-2 rounded-lg bg-secondary/60 px-4 py-2 text-center text-xs font-medium tracking-[0.15em] text-muted-foreground uppercase">
      <AlertTriangleIcon className="size-3.5 text-primary" />
      Sample data — for demonstration only. No real fund, client, or capital is represented.
    </div>
  )
}
