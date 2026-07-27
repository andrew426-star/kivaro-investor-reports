"use client"

import { TrendingUpIcon } from "lucide-react"
import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { InvestorReportSnapshot } from "@/lib/data/report"

function pct(v: number): string {
  return `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`
}

export function PerformanceSummary({ snapshot }: { snapshot: InvestorReportSnapshot }) {
  const chartData = snapshot.fundPerformanceHistory.map((point, i) => ({
    date: point.date,
    fund: point.value,
    benchmark: snapshot.benchmarkPerformanceHistory[i]?.value,
  }))

  return (
    <Card className="glow-border print-avoid-break">
      <CardHeader>
        <CardTitle className="flex items-center gap-1.5">
          <TrendingUpIcon className="size-4 text-primary" />
          Performance Summary
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted-foreground uppercase">
                <th className="pb-2 pr-3 font-medium">Period</th>
                <th className="pb-2 pr-3 font-medium text-right">Fund</th>
                <th className="pb-2 font-medium text-right">{snapshot.benchmarkName}</th>
              </tr>
            </thead>
            <tbody>
              {snapshot.periodReturns.map((p) => (
                <tr key={p.label} className="border-b border-border/50 last:border-0">
                  <td className="py-2 pr-3 text-foreground">{p.label}</td>
                  <td className={`py-2 pr-3 text-right ${p.fundReturnPercent >= 0 ? "text-primary" : "text-destructive"}`}>
                    {pct(p.fundReturnPercent)}
                  </td>
                  <td className={`py-2 text-right ${p.benchmarkReturnPercent >= 0 ? "text-primary" : "text-destructive"}`}>
                    {pct(p.benchmarkReturnPercent)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="fundGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(152 76% 46%)" stopOpacity={0.35} />
                <stop offset="95%" stopColor="hsl(152 76% 46%)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(150 12% 14%)" />
            <XAxis dataKey="date" tick={{ fontSize: 10, fill: "hsl(140 10% 55%)" }} minTickGap={40} />
            <YAxis tick={{ fontSize: 10, fill: "hsl(140 10% 55%)" }} width={50} domain={["auto", "auto"]} />
            <Tooltip
              contentStyle={{ background: "hsl(150 15% 7%)", border: "1px solid hsl(150 12% 14%)", fontSize: 12 }}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Area type="monotone" dataKey="fund" name="Fund" stroke="hsl(152 76% 46%)" fill="url(#fundGradient)" strokeWidth={2} />
            <Area type="monotone" dataKey="benchmark" name={snapshot.benchmarkName} stroke="hsl(82 80% 55%)" fill="none" strokeWidth={2} strokeDasharray="4 3" />
          </AreaChart>
        </ResponsiveContainer>
        <p className="text-xs text-muted-foreground italic">
          {snapshot.benchmarkName} is a hypothetical blended benchmark constructed for illustration and does not
          track any real-world index.
        </p>
      </CardContent>
    </Card>
  )
}
