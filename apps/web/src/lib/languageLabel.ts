// SPDX-License-Identifier: Apache-2.0
//
// Player-facing names for the language codes a scenario declares in
// `supported_languages`. Shared by the scenario setup page and the demo
// edition's conversation picker so an ISO code never reaches the player.

const LANGUAGE_LABELS: Record<string, string> = {
  en: 'English',
  es: 'Spanish',
  fr: 'French',
  ja: 'Japanese',
  de: 'German',
  zh: 'Chinese',
  pt: 'Portuguese',
  it: 'Italian',
  ko: 'Korean',
  nl: 'Dutch',
}

/** The display name for a language code, or the code itself when unknown. */
export function languageLabel(code: string): string {
  return LANGUAGE_LABELS[code] ?? code
}
