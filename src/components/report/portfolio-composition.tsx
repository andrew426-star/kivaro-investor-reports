"use client"

import { PieChartIcon } from "lucide-react"
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { InvestorReportSnapshot } from "@/lib/data/report"

const ALLOCATION_COLORS = [
  "hsl(152 76% 46%)",
  "hsl(162 72% 55%)",
  "hsl(82 80% 55%)",
  "hsl(160 80% 42%)",
  "hsl(155 50% 15%)",
]

const money = (value: number) =>
  value >= 1_000_000 ? `$${(value / 1_000_000).toFixed(1)}M` : `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`

export function PortfolioComposition({ snapshot }: { snapshot: InvestorReportSnapshot }) {
  const topHoldings = snapshot.holdings.slice(0, 10)

  return (
    <Card className="glow-border print-avoid-break">
      <CardHeader>
        <CardTitle className="flex items-center gap-1.5">
          <PieChartIcon className="size-4 text-primary" />
          Portfolio Composition
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="lg:col-span-1">
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie data={snapshot.allocation} dataKey="value" nameKey="assetClass" innerRadius={45} outerRadius={70} paddingAngle={2}>
                  {snapshot.allocation.map((slice, i) => (
                    <Cell key={slice.assetClass} fill={ALLOCATION_COLORS[i % ALLOCATION_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value) => money(Number(value))}
                  contentStyle={{ background: "hsl(150 15% 7%)", border: "1px solid hsl(150 12% 14%)", fontSize: 12 }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="mt-2 flex flex-col gap-1">
              {snapshot.allocation.map((slice, i) => (
                <div key={slice.assetClass} className="flex items-center justify-between text-xs">
                  <span className="flex items-center gap-1.5 text-muted-foreground">
                    <span className="size-2 rounded-full" style={{ background: ALLOCATION_COLORS[i % ALLOCATION_COLORS.length] }} />
                    {slice.assetClass}
                  </span>
                  <span className="text-foreground">{slice.percent.toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>

          <div className="overflow-x-auto lg:col-span-2">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs text-muted-foreground uppercase">
                  <th className="pb-2 font-medium">Symbol</th>
                  <th className="pb-2 font-medium">Asset Class</th>
                  <th className="pb-2 text-right font-medium">Weight</th>
                  <th className="pb-2 text-right font-medium">Period Return</th>
                </tr>
              </thead>
              <tbody>
                {topHoldings.map((h) => (
                  <tr key={h.symbol} className="border-b border-border/60 last:border-0">
                    <td className="py-2">
                      <div className="font-heading text-sm text-foreground">{h.symbol}</div>
                      <div className="text-xs text-muted-foreground">{h.name}</div>
                    </td>
                    <td className="py-2 text-muted-foreground">{h.assetClass}</td>
                    <td className="py-2 text-right text-muted-foreground">{h.weight.toFixed(1)}%</td>
                    <td className={`py-2 text-right ${h.periodReturnPercent >= 0 ? "text-primary" : "text-destructive"}`}>
                      {h.periodReturnPercent >= 0 ? "+" : ""}
                      {h.periodReturnPercent.toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-2 text-xs text-muted-foreground/70">Showing top {topHoldings.length} of {snapshot.holdings.length} holdings by market value.</p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
