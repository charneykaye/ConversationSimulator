// SPDX-License-Identifier: Apache-2.0
fn main() {
    // Rerun when the DLC App ID registry changes so the build picks up updated
    // pack-id ↔ DLC App ID mappings without requiring a manual `cargo clean`.
    println!("cargo:rerun-if-env-changed=VITE_STEAM_DLC_APP_IDS");

    // Validate the format at build time so a malformed mapping fails loudly
    // rather than silently producing a binary that treats all DLC as not-owned.
    if let Ok(raw) = std::env::var("VITE_STEAM_DLC_APP_IDS") {
        if !raw.is_empty() {
            for entry in raw.split(',') {
                let entry = entry.trim();
                if entry.is_empty() {
                    continue;
                }
                let colon = entry.find(':').unwrap_or(0);
                let pack_id = entry[..colon].trim();
                let app_id_str = entry[colon + 1..].trim();
                if colon == 0 || pack_id.is_empty() || app_id_str.parse::<u32>().is_err() {
                    panic!(
                        "VITE_STEAM_DLC_APP_IDS contains a malformed entry: {:?}\n\
                         Expected format: pack_id:dlc_app_id  \
                         (e.g. official.pack:2123456)\n\
                         Full value: {}",
                        entry, raw
                    );
                }
            }
        }
    }

    // Product edition (issue #495). `lib.rs` bakes CONVSIM_EDITION into the
    // binary with option_env! and hands it to convsim-core at launch. Rerun
    // when it changes so switching between a demo and a full build never
    // reuses a stale object, and reject anything but the two known values so
    // a typo cannot silently produce a full build labelled as a demo.
    println!("cargo:rerun-if-env-changed=CONVSIM_EDITION");
    if let Ok(raw) = std::env::var("CONVSIM_EDITION") {
        // Exact match, no trimming: lib.rs compares option_env!("CONVSIM_EDITION")
        // against "demo" byte for byte, so a padded "demo " (a stray newline in
        // a shell export) must be rejected here rather than quietly compiled
        // as the full app.
        if !raw.is_empty() && raw != "full" && raw != "demo" {
            panic!(
                "CONVSIM_EDITION must be exactly \"full\" or \"demo\" (got {:?}). \
                 See docs/steam-next-fest-demo.md.",
                raw
            );
        }
    }

    // Shared data-root key (issue #495). Every edition keys its per-user data
    // directory to the FULL app's bundle identifier so the demo and the full
    // app share models, sessions and the logbook. Read it from tauri.conf.json
    // here — the base config; the demo's overlay is applied by the Tauri CLI
    // at build time, never to this file — so the value lib.rs uses can never
    // drift from the identifier the full app actually installs under.
    println!("cargo:rerun-if-changed=tauri.conf.json");
    let conf = std::fs::read_to_string("tauri.conf.json")
        .expect("tauri.conf.json must be readable next to build.rs");
    let conf: serde_json::Value =
        serde_json::from_str(&conf).expect("tauri.conf.json must be valid JSON");
    let identifier = conf
        .get("identifier")
        .and_then(|v| v.as_str())
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .expect("tauri.conf.json must set a non-empty `identifier`");
    println!("cargo:rustc-env=CONVSIM_DATA_ROOT_IDENTIFIER={identifier}");

    tauri_build::build()
}
