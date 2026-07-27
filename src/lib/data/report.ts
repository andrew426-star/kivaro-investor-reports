// Fully synthetic — no real fund, client, or capital is represented. See
// SampleDataBanner. Deliberately deterministic (a seeded LCG, not
// Math.random()) so the report reads the same across reloads and
// deployments. This is a fresh generator (not a cross-repo import of
// kivaro-strategy-dashboard's portfolio.ts) — each service-line repo is
// standalone by design — though it reuses "Meridian Capital Partners" as
// the fund name for continuity across the demo suite, same as
// kivaro-fund-ops does independently.

export type AssetClass = "Equities" | "Fixed Income" | "Alternatives" | "Digital Assets" | "Cash"

export interface Holding {
  symbol: string
  name: string
  assetClass: AssetClass
  marketValue: number
  weight: number
  periodReturnPercent: number // this holding's own return over the reporting period
}

export interface AllocationSlice {
  assetClass: string
  value: number
  percent: number
}

export interface PeriodReturn {
  label: "QTD" | "YTD" | "1-Year" | "Since Inception"
  fundReturnPercent: number
  benchmarkReturnPercent: number
}

export interface CapitalAccountSummary {
  beginningCapital: number
  contributions: number
  distributions: number
  netInvestmentIncome: number
  netRealizedGain: number
  netUnrealizedGain: number
  managementFees: number
  endingCapital: number // computed from the fields above, never hardcoded separately
}

export interface InvestorReportSnapshot {
  fundName: string
  reportTitle: string
  periodLabel: string
  periodEndDate: string
  inceptionDate: string
  preparedFor: string
  asOf: string
  benchmarkName: string
  periodReturns: PeriodReturn[]
  fundPerformanceHistory: { date: string; value: number }[]
  benchmarkPerformanceHistory: { date: string; value: number }[]
  holdings: Holding[] // full set, for accurate allocation math — UI renders top 10 only
  allocation: AllocationSlice[]
  capitalAccount: CapitalAccountSummary
}

// A small deterministic LCG — reproducible "randomness," same technique
// as kivaro-strategy-dashboard's portfolio.ts.
function createSeededRandom(seed: number) {
  let state = seed
  return function random() {
    state = (state * 1103515245 + 12345) & 0x7fffffff
    return state / 0x7fffffff
  }
}

interface RawHolding {
  symbol: string
  name: string
  assetClass: AssetClass
  marketValue: number
  periodReturnPercent: number
}

const RAW_HOLDINGS: RawHolding[] = [
  // Equities
  { symbol: "AAPL", name: "Apple Inc.", assetClass: "Equities", marketValue: 9_000_000, periodReturnPercent: 6.2 },
  { symbol: "MSFT", name: "Microsoft Corp.", assetClass: "Equities", marketValue: 8_500_000, periodReturnPercent: 8.1 },
  { symbol: "NVDA", name: "NVIDIA Corp.", assetClass: "Equities", marketValue: 7_800_000, periodReturnPercent: 14.3 },
  { symbol: "GOOGL", name: "Alphabet Inc.", assetClass: "Equities", marketValue: 6_200_000, periodReturnPercent: 3.8 },
  { symbol: "JPM", name: "JPMorgan Chase & Co.", assetClass: "Equities", marketValue: 5_900_000, periodReturnPercent: 2.1 },
  { symbol: "V", name: "Visa Inc.", assetClass: "Equities", marketValue: 5_100_000, periodReturnPercent: 4.6 },
  { symbol: "COST", name: "Costco Wholesale Corp.", assetClass: "Equities", marketValue: 4_700_000, periodReturnPercent: -1.2 },
  { symbol: "UNH", name: "UnitedHealth Group", assetClass: "Equities", marketValue: 4_000_000, periodReturnPercent: -9.8 },
  { symbol: "XOM", name: "Exxon Mobil Corp.", assetClass: "Equities", marketValue: 3_800_000, periodReturnPercent: -2.4 },

  // Fixed Income
  { symbol: "TLT", name: "iShares 20+ Year Treasury Bond ETF", assetClass: "Fixed Income", marketValue: 8_600_000, periodReturnPercent: -3.1 },
  { symbol: "AGG", name: "iShares Core U.S. Aggregate Bond ETF", assetClass: "Fixed Income", marketValue: 7_900_000, periodReturnPercent: 0.8 },
  { symbol: "LQD", name: "iShares iBoxx Investment Grade Corp Bond ETF", assetClass: "Fixed Income", marketValue: 6_400_000, periodReturnPercent: 1.4 },

  // Alternatives
  { symbol: "GLD", name: "SPDR Gold Shares", assetClass: "Alternatives", marketValue: 7_200_000, periodReturnPercent: 5.9 },
  { symbol: "VNQ", name: "Vanguard Real Estate ETF", assetClass: "Alternatives", marketValue: 5_600_000, periodReturnPercent: -2.7 },

  // Digital Assets
  { symbol: "BTC", name: "Bitcoin (spot-equivalent exposure)", assetClass: "Digital Assets", marketValue: 3_800_000, periodReturnPercent: 11.2 },

  // Cash
  { symbol: "CASH", name: "Cash & Equivalents", assetClass: "Cash", marketValue: 6_000_000, periodReturnPercent: 0 },
]

function buildHoldings(): { holdings: Holding[]; totalValue: number } {
  const totalValue = RAW_HOLDINGS.reduce((sum, h) => sum + h.marketValue, 0)
  const holdings: Holding[] = RAW_HOLDINGS.map((h) => ({
    symbol: h.symbol,
    name: h.name,
    assetClass: h.assetClass,
    marketValue: h.marketValue,
    weight: (h.marketValue / totalValue) * 100,
    periodReturnPercent: h.periodReturnPercent,
  }))
  return { holdings: holdings.sort((a, b) => b.marketValue - a.marketValue), totalValue }
}

function buildAllocation(holdings: Holding[], totalValue: number): AllocationSlice[] {
  const byClass = new Map<string, number>()
  for (const h of holdings) {
    byClass.set(h.assetClass, (byClass.get(h.assetClass) ?? 0) + h.marketValue)
  }
  return Array.from(byClass.entries())
    .map(([assetClass, value]) => ({ assetClass, value, percent: (value / totalValue) * 100 }))
    .sort((a, b) => b.value - a.value)
}

// Forward monthly index walk from inception (index = 100) to periodEndDate,
// inclusive of both ends (monthsCount + 1 points). A seeded LCG, not
// Math.random(), so the series is reproducible across reloads/deploys.
function buildMonthlySeries(
  monthsCount: number,
  periodEndDate: Date,
  seed: number,
  monthlyDrift: number,
  noiseAmplitude: number
): { date: string; value: number }[] {
  const random = createSeededRandom(seed)
  const values: number[] = [100]
  for (let i = 1; i <= monthsCount; i++) {
    const noise = (random() - 0.5) * 2 * noiseAmplitude
    values.push(values[i - 1] * (1 + monthlyDrift + noise))
  }
  const series: { date: string; value: number }[] = []
  for (let i = 0; i <= monthsCount; i++) {
    const monthsAgo = monthsCount - i
    const date = new Date(Date.UTC(periodEndDate.getUTCFullYear(), periodEndDate.getUTCMonth() - monthsAgo + 1, 0))
    series.push({ date: date.toISOString().slice(0, 10), value: Math.round(values[i] * 100) / 100 })
  }
  return series
}

function indexValueAtMonthsAgo(series: { value: number }[], monthsAgo: number): number {
  const i = series.length - 1 - monthsAgo
  return series[Math.max(0, i)].value
}

function pctReturn(startValue: number, endValue: number): number {
  return Math.round(((endValue / startValue - 1) * 100) * 100) / 100
}

function getReportingPeriod(now: Date): { periodEndDate: Date; periodLabel: string; quarterStartMonthsAgo: number; yearStartMonthsAgo: number } {
  const year = now.getUTCFullYear()
  const month = now.getUTCMonth() // 0-11
  const currentQuarter = Math.floor(month / 3) + 1
  let reportYear = year
  let reportQuarter = currentQuarter - 1
  if (reportQuarter === 0) {
    reportQuarter = 4
    reportYear -= 1
  }
  const quarterEndMonth = reportQuarter * 3 - 1 // 0-indexed: 2, 5, 8, or 11
  const periodEndDate = new Date(Date.UTC(reportYear, quarterEndMonth + 1, 0))

  // Months between Jan 1 of periodEndDate's year and periodEndDate.
  const yearStartMonthsAgo = quarterEndMonth - 0 // e.g. Q2 end (month index 5) is 5 months after Jan (index 0)

  return { periodEndDate, periodLabel: `Q${reportQuarter} ${reportYear}`, quarterStartMonthsAgo: 3, yearStartMonthsAgo }
}

const INCEPTION_MONTHS = 36

export function getInvestorReportSnapshot(): InvestorReportSnapshot {
  const { holdings, totalValue } = buildHoldings()
  const allocation = buildAllocation(holdings, totalValue)

  const { periodEndDate, periodLabel, quarterStartMonthsAgo, yearStartMonthsAgo } = getReportingPeriod(new Date())
  const inceptionDate = new Date(Date.UTC(periodEndDate.getUTCFullYear(), periodEndDate.getUTCMonth() - INCEPTION_MONTHS + 1, 1))

  const fundPerformanceHistory = buildMonthlySeries(INCEPTION_MONTHS, periodEndDate, 42, 0.0022, 0.03)
  const benchmarkPerformanceHistory = buildMonthlySeries(INCEPTION_MONTHS, periodEndDate, 1337, 0.0016, 0.025)

  const periods: { label: PeriodReturn["label"]; monthsAgo: number }[] = [
    { label: "QTD", monthsAgo: quarterStartMonthsAgo },
    { label: "YTD", monthsAgo: yearStartMonthsAgo },
    { label: "1-Year", monthsAgo: 12 },
    { label: "Since Inception", monthsAgo: INCEPTION_MONTHS },
  ]

  const periodReturns: PeriodReturn[] = periods.map(({ label, monthsAgo }) => ({
    label,
    fundReturnPercent: pctReturn(indexValueAtMonthsAgo(fundPerformanceHistory, monthsAgo), fundPerformanceHistory[fundPerformanceHistory.length - 1].value),
    benchmarkReturnPercent: pctReturn(indexValueAtMonthsAgo(benchmarkPerformanceHistory, monthsAgo), benchmarkPerformanceHistory[benchmarkPerformanceHistory.length - 1].value),
  }))

  const capitalAccountInputs = {
    beginningCapital: 118_000_000,
    contributions: 3_500_000,
    distributions: 2_000_000,
    netInvestmentIncome: 850_000,
    netRealizedGain: 1_200_000,
    netUnrealizedGain: 4_650_000,
    managementFees: 600_000,
  }
  const endingCapital =
    capitalAccountInputs.beginningCapital +
    capitalAccountInputs.contributions -
    capitalAccountInputs.distributions +
    capitalAccountInputs.netInvestmentIncome +
    capitalAccountInputs.netRealizedGain +
    capitalAccountInputs.netUnrealizedGain -
    capitalAccountInputs.managementFees

  return {
    fundName: "Meridian Capital Partners, L.P.",
    reportTitle: "Quarterly Investor Report",
    periodLabel,
    periodEndDate: periodEndDate.toISOString().slice(0, 10),
    inceptionDate: inceptionDate.toISOString().slice(0, 10),
    preparedFor: "Limited Partners of Meridian Capital Partners, L.P.",
    asOf: new Date().toISOString(),
    benchmarkName: "Meridian Reference Index (Blended 60/40, Illustrative)",
    periodReturns,
    fundPerformanceHistory,
    benchmarkPerformanceHistory,
    holdings,
    allocation,
    capitalAccount: { ...capitalAccountInputs, endingCapital },
  }
}
