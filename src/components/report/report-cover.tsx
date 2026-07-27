import { Card, CardContent } from "@/components/ui/card"
import type { InvestorReportSnapshot } from "@/lib/data/report"

export function ReportCover({ snapshot }: { snapshot: InvestorReportSnapshot }) {
  return (
    <Card className="glow-border print-avoid-break">
      <CardContent className="flex flex-col gap-2 py-8 text-center">
        <span className="text-xs tracking-[0.25em] text-muted-foreground uppercase">Confidential — For Limited Partner Use Only</span>
        <h1 className="font-heading text-3xl text-gradient-green">{snapshot.fundName}</h1>
        <h2 className="font-heading text-xl text-foreground">{snapshot.reportTitle}</h2>
        <span className="text-sm text-muted-foreground">
          {snapshot.periodLabel} — Period Ended {snapshot.periodEndDate}
        </span>
        <span className="mt-2 text-xs text-muted-foreground">Prepared for {snapshot.preparedFor}</span>
        <span className="text-xs text-muted-foreground">Fund inception: {snapshot.inceptionDate}</span>
      </CardContent>
    </Card>
  )
}
