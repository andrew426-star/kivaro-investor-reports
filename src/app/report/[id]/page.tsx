import { CapitalAccountSummary } from "@/components/report/capital-account-summary"
import { CommentaryPanel } from "@/components/report/commentary-panel"
import { Disclosures } from "@/components/report/disclosures"
import { DistributionPanel } from "@/components/report/distribution-panel"
import { PerformanceSummary } from "@/components/report/performance-summary"
import { PortfolioComposition } from "@/components/report/portfolio-composition"
import { PrintButton } from "@/components/report/print-button"
import { ReportCover } from "@/components/report/report-cover"
import { SampleDataBanner } from "@/components/sample-data-banner"
import { getInvestorReportSnapshot } from "@/lib/data/report"

export default function Home() {
  const snapshot = getInvestorReportSnapshot()

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-4 px-4 py-6 sm:px-8">
      <header className="flex flex-col gap-1 py-2 print:hidden">
        <span className="text-xs tracking-[0.2em] text-muted-foreground uppercase">
          Reporting & Investor Communications
        </span>
        <h1 className="font-heading text-2xl text-gradient-green sm:text-3xl">
          A Real Investor Report, Generated and Ready to Distribute
        </h1>
        <p className="text-sm text-muted-foreground">
          Every figure below is computed, not guessed — the AI only writes the commentary section, grounded in
          those already-final numbers. Print it, export it to PDF, or simulate sending it to the distribution list.
        </p>
      </header>

      <div className="print:hidden">
        <PrintButton />
      </div>

      <ReportCover snapshot={snapshot} />
      {/* Deliberately NOT print:hidden — an exported/printed report is a
          portable artifact that can leave the browser tab, so this
          disclaimer needs to survive into the exported document. */}
      <SampleDataBanner />
      <PerformanceSummary snapshot={snapshot} />
      <CapitalAccountSummary account={snapshot.capitalAccount} />
      <PortfolioComposition snapshot={snapshot} />
      <CommentaryPanel />
      <Disclosures snapshot={snapshot} />
      <DistributionPanel />
    </div>
  )
}
