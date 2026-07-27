import { NextResponse } from "next/server"
import { Type } from "@google/genai"

import { GEMINI_MODEL, getGeminiClient } from "@/lib/gemini-client"
import { getInvestorReportSnapshot } from "@/lib/data/report"

const RESPONSE_SCHEMA = {
  type: Type.OBJECT,
  properties: {
    performanceCommentary: {
      type: Type.STRING,
      description:
        "2-3 sentences discussing the fund's period performance relative to the benchmark, in qualitative terms only (e.g. 'modest gains', 'meaningfully ahead of benchmark'). Do not state any specific percentage, dollar figure, or number — those are already shown elsewhere in the report. Plain prose only — no markdown formatting of any kind (no **bold**, no #headers, no bullet dashes).",
    },
    notableHoldings: {
      type: Type.ARRAY,
      items: {
        type: Type.OBJECT,
        properties: {
          symbol: {
            type: Type.STRING,
            description: "Must exactly match a symbol supplied in the holdings list below. Never invent a symbol not present in the input.",
          },
          note: {
            type: Type.STRING,
            description: "One sentence on this holding's role as a contributor or detractor this period, qualitative only — no specific numbers. Plain prose only, no markdown.",
          },
        },
        required: ["symbol", "note"],
      },
    },
    marketContext: {
      type: Type.STRING,
      description:
        "1-2 sentences of general market-tone context consistent with the performance direction described (e.g. risk-on sentiment, rate-sensitive positioning, elevated volatility). Do not reference any specific real-world event, date, central bank decision, company outside the holdings list, or news item — this is illustrative commentary for a sample report, not real market reporting. Plain prose only, no markdown.",
    },
    outlookNote: {
      type: Type.STRING,
      description:
        "1-2 sentence forward-looking closing note in a professional quarterly-letter tone, appropriately hedged (e.g. 'the manager will continue to monitor...'), never a guarantee or promise of future results, no specific numbers. Plain prose only, no markdown.",
    },
  },
  required: ["performanceCommentary", "notableHoldings", "marketContext", "outlookNote"],
}

function buildPrompt(snapshot: ReturnType<typeof getInvestorReportSnapshot>): string {
  const periodReturnsText = snapshot.periodReturns
    .map((p) => `${p.label}: fund ${p.fundReturnPercent.toFixed(1)}% vs. benchmark ${p.benchmarkReturnPercent.toFixed(1)}%`)
    .join("; ")

  const allocationText = snapshot.allocation.map((a) => `${a.assetClass} ${a.percent.toFixed(1)}%`).join(", ")

  const holdingsText = snapshot.holdings
    .map((h) => `${h.symbol} (${h.name}, ${h.assetClass}, ${h.weight.toFixed(1)}% of portfolio): ${h.periodReturnPercent >= 0 ? "+" : ""}${h.periodReturnPercent.toFixed(1)}% this period`)
    .join("\n")

  return `You are writing the market and portfolio commentary section of a quarterly investor letter for ${snapshot.fundName}, period ${snapshot.periodLabel} (ended ${snapshot.periodEndDate}), benchmarked against "${snapshot.benchmarkName}".

All figures below are already final and will be displayed elsewhere in the report exactly as given — your job is narrative interpretation only, never computation or restatement of numbers. Do not state any specific percentage, dollar amount, or figure anywhere in your response. Do not reference any specific real-world event, news item, central bank action, or company not in the holdings list below — this is illustrative sample commentary, not real market reporting, and must not read as a factual account of actual events. Output plain prose only in every field — no markdown formatting of any kind (no **bold**, no #headers, no bullet lists or dashes).

PERIOD RETURNS (fund vs. benchmark): ${periodReturnsText}

ALLOCATION: ${allocationText}

HOLDINGS AND THEIR PERIOD RETURNS:
${holdingsText}`
}

export async function POST() {
  try {
    const snapshot = getInvestorReportSnapshot()

    const client = getGeminiClient()
    const response = await client.models.generateContent({
      model: GEMINI_MODEL,
      contents: buildPrompt(snapshot),
      config: {
        responseMimeType: "application/json",
        responseSchema: RESPONSE_SCHEMA,
      },
    })

    const raw = response.text
    if (!raw) throw new Error("Gemini returned an empty response.")
    const parsed = JSON.parse(raw)

    const validSymbols = new Set(snapshot.holdings.map((h) => h.symbol))
    const notableHoldings = (parsed.notableHoldings as { symbol: string; note: string }[]).filter((n) =>
      validSymbols.has(n.symbol)
    )

    return NextResponse.json({
      commentary: {
        performanceCommentary: parsed.performanceCommentary,
        notableHoldings,
        marketContext: parsed.marketContext,
        outlookNote: parsed.outlookNote,
      },
      generatedAt: Date.now(),
    })
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Failed to generate commentary." },
      { status: 502 }
    )
  }
}
