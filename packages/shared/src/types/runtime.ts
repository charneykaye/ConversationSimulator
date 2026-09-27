export interface RuntimeReadiness {
  llm_ready: boolean;
  llm_model_name: string | null;
  stt_ready: boolean;
  tts_ready: boolean;
  tts_voice_name: string | null;
  network_required: boolean;
  last_error?: string | null;
}

/** Product edition reported by convsim-core (issue #495). */
export type Edition = 'full' | 'demo';

/** What the demo edition exposes; absent (null) in the full app. */
export interface DemoInfo {
  /** Registry id of the single model the demo installs. */
  model_id: string | null;
  /** The curated demo conversations, in display order. */
  scenario_ids: string[];
  /** The packs those conversations come from. */
  pack_ids: string[];
}

export interface HealthResponse {
  status: 'ok' | 'degraded' | 'error';
  runtime: RuntimeReadiness;
  version: string;
  /** Omitted by older cores and the interim TS backend; treat as 'full'. */
  edition?: Edition;
  demo?: DemoInfo | null;
}
