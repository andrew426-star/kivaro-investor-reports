import { BookOpenIcon } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { CapitalAccountSummary as CapitalAccountSummaryData } from "@/lib/data/report"

function money(n: number): string {
  return n.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 })
}

interface Row {
  label: string
  value: number
  sign: "" | "+" | "-"
  emphasize?: boolean
}

export function CapitalAccountSummary({ account }: { account: CapitalAccountSummaryData }) {
  const rows: Row[] = [
    { label: "Beginning Capital", value: account.beginningCapital, sign: "" },
    { label: "Contributions", value: account.contributions, sign: "+" },
    { label: "Distributions", value: account.distributions, sign: "-" },
    { label: "Net Investment Income", value: account.netInvestmentIncome, sign: "+" },
    { label: "Net Realized Gain", value: account.netRealizedGain, sign: "+" },
    { label: "Net Unrealized Gain", value: account.netUnrealizedGain, sign: "+" },
    { label: "Management Fees", value: account.managementFees, sign: "-" },
  ]

  return (
    <Card className="glow-border print-avoid-break">
      <CardHeader>
        <CardTitle className="flex items-center gap-1.5">
          <BookOpenIcon className="size-4 text-primary" />
          Capital Account Summary
        </CardTitle>
      </CardHeader>
      <CardContent>
        <table className="w-full text-sm">
          <tbody>
            {rows.map((row) => (
              <tr key={row.label} className="border-b border-border/50">
                <td className="py-1.5 text-muted-foreground">{row.label}</td>
                <td className="py-1.5 text-right text-foreground">
                  {row.sign === "-" ? "(" : ""}
                  {money(row.value)}
                  {row.sign === "-" ? ")" : ""}
                </td>
              </tr>
            ))}
            <tr>
              <td className="pt-2 font-medium text-foreground">Ending Capital</td>
              <td className="pt-2 text-right font-heading text-lg text-primary">{money(account.endingCapital)}</td>
            </tr>
          </tbody>
        </table>
      </CardContent>
    </Card>
  )
}
