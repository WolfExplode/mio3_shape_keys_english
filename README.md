<p align="center">
  <a href="README.md">English</a> |
  <a href="README-JP.md">日本語</a>
</p>

# Mio3 Shape Keys

An integrated shape key management tool specialized for character modeling.

## About this fork

This repository is an English-language fork of the upstream addon:

**Upstream:** [mio3io/mio3_shape_keys](https://github.com/mio3io/mio3_shape_keys)

It tracks upstream `master` and adds an English UI (`translation_dict` with `ja_JP` locale), performance and workflow improvements, and extra operators listed in the changelog below. For the original Japanese README and official releases, see the upstream repo.

## Download

https://addon.mio3io.com/

## Documentation

[Mio3 Shape Keys Ver3 Documentation (WIP)](https://addon.mio3io.com/#/ja/mio3shapekeys/)


## Main Features Added in Ver3

(From upstream — see [mio3io/mio3_shape_keys](https://github.com/mio3io/mio3_shape_keys) for the authoritative list.)

-   Shape key sync and automatic editing
-   Apply modifiers while preserving shape keys
-   Batch transfer of shape keys between meshes with different topology
-   Create left/right shape keys
-   Create opposite-side shape keys
-   Tagging
-   Shape key value preset registration
-   Grouping (default: keys with names starting with "===" are grouped)
-   Move and sort by group
-   Multi-select system
-   Batch operations on selected keys
-   Find keys matching specific conditions (unused, error causes, etc.)
-   Shape key smoothing
-   Symmetrize shape
-   Mirror shape (left/right)
-   Invert shape movement amount
-   Copy and paste shape
-   Clear vertices that have not moved beyond a threshold
-   Materialize shape keys as objects
-   Protect and repair shape keys (e.g., blink) that break when applied to Basis

## Ver2

Ver2 can be downloaded from [releases](https://github.com/mio3io/mio3_shape_keys/releases).


## Changelog (fork additions)

Base: upstream Ver3 (`3.0.0-beta-20260315`)

[Added transfer properties](https://github.com/WolfExplode/mio3_shape_keys_english/commit/08a26b8643530a09e708ecf5639c438badd04c75)
- Transfer Properties option added to the Transfer Shape Key dialog (mute, slider range, vertex group, tags, composer rules).

[Optimized Transfer](https://github.com/WolfExplode/mio3_shape_keys_english/commit/3df7a487d14fda53a59486bdcfe647b3497fecd6)
- Vectorized interpolation, scipy cKDTree fallback, buffer reuse, matrix precomputation. ~60% faster on large meshes.

[Added transfer properties operator](https://github.com/WolfExplode/mio3_shape_keys_english/commit/909662d7b383b003dd79630e94ae5847b15b0604)
- Standalone Transfer Properties operator for two objects with matching shape key names.

[Added Transfer Shape Key operator](https://github.com/WolfExplode/mio3_shape_keys_english/commit/7b92102b26e9e012bf0bad162ba0750fe81ce05a)
- Transfers the drivers according to shape key name

[Create vertex group from selected shape keys](https://github.com/WolfExplode/mio3_shape_keys_english/commit/41536d34ffc962b8293f53d767f7d4df8a16eff6) — Builds a vertex group from the selected keys; weights are copied correctly from shape key influence.

[Added new operator "Set Value To Zero"](https://github.com/WolfExplode/mio3_shape_keys_english/commit/9e1b6ea22cf99bc06eabd21c2f55356f9bdfbdd8)
- sets the selected shape keys value to zero

[Added new operator create vertex group from selected shape keys](https://github.com/WolfExplode/mio3_shape_keys_english/commit/41536d34ffc962b8293f53d767f7d4df8a16eff6)

[Expanded presets + import/export](https://github.com/WolfExplode/mio3_shape_keys_english/commit/aecbc7b3d1353c7a355086a92562d2bdd90db410)
— Fixed presets not saving some keys; options for selected keys only and including keys at zero value.

### Other changes
- Added ability to remove drivers from selected shape keys

### UI behavior

- **Show used keys only** — Also shows shape key groups so you can expand or collapse them while the filter is on.
- **Group expand/collapse** — Clicking the triangle sets that group header as the active shape key so the list stays focused on the group you clicked.
- **Search** — Groups that contain a matching key auto-expand during search.

### Fixes and compatibility

- **Blender 5.0** — Fixed selection on shape key blocks (`key_blocks[...]` has no `select` attribute).
- **Blender 5.1** — Crash fix in shape key list handling.
- **Transfer** — Patched `operators/transfer.py` for runtime regressions after upstream merges.
- **Vertex groups from shape keys** — Weight copy corrected when creating groups from keys.


### [Experimental Changes in other branches](https://github.com/WolfExplode/mio3_shape_keys_english/tree/Morph_Brush)

- **Morph Brush** — Paint localized shape-key blends with vertex paint. Setup creates a `mio3sk_morph` color attribute (white = no effect, black = full blend). Apply Morph blends the active shape key toward the morph target (set in Copy Source). Optional **Auto apply on stroke end** applies after each sculpt stroke in vertex paint mode.
