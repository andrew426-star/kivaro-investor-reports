import { GoogleGenAI } from "@google/genai"

let client: GoogleGenAI | null = null

export function getGeminiClient(): GoogleGenAI {
  if (!client) {
    const apiKey = process.env.GEMINI_API_KEY
    if (!apiKey) throw new Error("GEMINI_API_KEY is not set")
    client = new GoogleGenAI({ apiKey })
  }
  return client
}

// gemini-flash-latest is a live-updating alias (currently Gemini 3.5
// Flash) rather than a dated snapshot — same reasoning as GROQ_MODEL /
// ELEVENLABS_MODEL_ID elsewhere in this codebase: these get superseded on
// their own cadence and shouldn't be hardcoded inline. Configurable via
// env var, defaulted here.
export const GEMINI_MODEL = process.env.GEMINI_MODEL || "gemini-flash-latest"
