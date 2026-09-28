// SPDX-License-Identifier: Apache-2.0
/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Product edition baked into the bundle: 'full' (default) or 'demo'. See src/edition.tsx. */
  readonly VITE_CONVSIM_EDITION?: string
  /** Shows the developer debug drawer when 'true'. */
  readonly VITE_DEV_TOOLS?: string
  /** pack_id:dlc_app_id pairs, comma-separated. See hooks/useSteamDlc.ts. */
  readonly VITE_STEAM_DLC_APP_IDS?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
