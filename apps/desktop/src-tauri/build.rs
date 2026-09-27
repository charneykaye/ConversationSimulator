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
        let edition = raw.trim();
        if !edition.is_empty() && edition != "full" && edition != "demo" {
            panic!(
                "CONVSIM_EDITION must be \"full\" or \"demo\" (got {:?}). \
                 See docs/steam-next-fest-demo.md.",
                raw
            );
        }
    }

    tauri_build::build()
}
