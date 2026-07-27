import { ShieldAlertIcon } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { InvestorReportSnapshot } from "@/lib/data/report"

// Static, not AI-generated — legal/compliance language should never be
// left to an LLM to phrase, the same principle that keeps materiality
// and NAV arithmetic out of the LLM's hands in kivaro-fund-ops.
export function Disclosures({ snapshot }: { snapshot: InvestorReportSnapshot }) {
  return (
    <Card className="glow-border print-avoid-break">
      <CardHeader>
        <CardTitle className="flex items-center gap-1.5">
          <ShieldAlertIcon className="size-4 text-primary" />
          Disclosures
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 text-xs leading-relaxed text-muted-foreground">
        <p>
          <strong className="text-foreground">Sample Document.</strong> This report is a fully synthetic,
          illustrative sample produced for demonstration purposes only. No real fund, client, investor, or capital
          is represented. All figures, holdings, performance results, and commentary contained herein are
          fictional and generated for the purpose of illustrating Kivaro AI&apos;s reporting automation
          capabilities. This document has no legal, financial, or investment significance.
        </p>
        <p>
          <strong className="text-foreground">Past Performance.</strong> Past performance is not indicative of
          future results. The value of an investment in {snapshot.fundName} may fluctuate, and investors may not
          receive back the full amount originally invested. All performance figures shown are presented net of
          fees unless otherwise noted and are unaudited.
        </p>
        <p>
          <strong className="text-foreground">Benchmark Comparison.</strong> {snapshot.benchmarkName} is a
          hypothetical, blended reference constructed solely for illustrative comparison in this sample report. It
          does not correspond to any real, investable, or third-party-published index, is not adjusted for fees or
          transaction costs, and should not be relied upon as an indicator of the fund&apos;s actual relative
          performance against any real benchmark.
        </p>
        <p>
          <strong className="text-foreground">Forward-Looking Statements.</strong> Any statements regarding future
          outlook, strategy, or expectations contained in this report are forward-looking in nature, are subject to
          significant uncertainty, and are not guarantees of future performance. Actual results could differ
          materially from any such statements. The manager undertakes no obligation to update any forward-looking
          statement.
        </p>
        <p>
          <strong className="text-foreground">Confidentiality.</strong> This document is intended solely for the
          use of the limited partners of {snapshot.fundName} and their authorized representatives. It may not be
          reproduced, distributed, or disclosed to any third party, in whole or in part, without prior written
          consent.
        </p>
        <p>
          <strong className="text-foreground">No Offer or Solicitation.</strong> This report does not constitute
          an offer to sell, or a solicitation of an offer to buy, any security or investment product, and should
          not be construed as investment, legal, or tax advice.
        </p>
      </CardContent>
    </Card>
  )
}
