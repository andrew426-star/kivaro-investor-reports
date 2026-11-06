import { NextRequest, NextResponse } from "next/server"
import Papa from "papaparse"
import * as XLSX from "xlsx"
import type { ImportResult } from "@/lib/types/report"

function parseCSV(text: string): any[] {
  const result = Papa.parse(text, { header: true, skipEmptyLines: true })
  return result.data as any[]
}

function parseExcel(buffer: ArrayBuffer): any[] {
  const workbook = XLSX.read(buffer, { type: "array" })
  const firstSheet = workbook.Sheets[workbook.SheetNames[0]]
  return XLSX.utils.sheet_to_json(firstSheet)
}

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()
    const file = formData.get("file") as File
    
    if (!file) {
      return NextResponse.json({ error: "No file uploaded" }, { status: 400 })
    }
    
    const filename = file.name.toLowerCase()
    const buffer = await file.arrayBuffer()
    let rawData: any[] = []
    
    if (filename.endsWith(".csv")) {
      const text = new TextDecoder().decode(buffer)
      rawData = parseCSV(text)
    } else if (filename.endsWith(".xlsx") || filename.endsWith(".xls")) {
      rawData = parseExcel(buffer)
    } else if (filename.endsWith(".json")) {
      const text = new TextDecoder().decode(buffer)
      rawData = JSON.parse(text)
    } else {
      return NextResponse.json({ error: "Unsupported file type. Please upload CSV, Excel, or JSON." }, { status: 400 })
    }
    
    // Basic validation and transformation - this is a flexible parser
    const result: ImportResult = {
      success: true,
      data: {},
      warnings: [],
    }
    
    // Try to extract common report fields
    if (Array.isArray(rawData) && rawData.length > 0) {
      result.warnings?.push("Data imported successfully. Review and map fields in the report editor.")
result.data = { importedRows: rawData } as any
    }
    
    return NextResponse.json({ 
      result,
      rawData,
      filename: file.name 
    })
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to import file" },
      { status: 500 }
    )
  }
}
