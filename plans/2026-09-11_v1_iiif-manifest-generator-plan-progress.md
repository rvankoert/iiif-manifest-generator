# IIIF Manifest Generator — Plan Execution Progress

- **Plan:** `plans/2026-09-11_v1_iiif-manifest-generator-plan.md` (plan v1, 2338 lines, Steps 0–21)
- **Started:** 2026-09-13
- **Executor:** Cline
- **Sub-agent model:** This environment provides no sub-agent spawning tool, so each plan step is executed as a **strictly isolated, sequential sub-agent phase**: one step is fully implemented, verified with the plan's own verification command, and logged here before the next phase begins. Each phase's scope is exactly the step's "Files to touch" + "Action" + "Verification".

## Status overview

| Step | Name | Status |
| --- | --- | --- |
| 0 | Save this plan document | ✅ done |
| 1 | Project scaffolding | ✅ done |
| 2 | Configuration module | ✅ done |
| 3 | Image detection & dimension probing | ✅ done |
| 4 | IIPImage URL construction | ✅ done |
| 5 | Shared data model | ✅ done |
| 6 | Recursive tree scanner | ✅ done |
| 7 | Shared builder helpers | ✅ done |
| 8 | IIIF 2.0 builder | ✅ done |
| 9 | IIIF 2.1 builder | ✅ done |
| 10 | IIIF 3.0 builder | ✅ done |
| 11 | IIIF 4.0 builder + builder registry | ✅ done |
| 12 | Writer + generation orchestration | ✅ done |
| 13 | CLI | ✅ done |
| 14 | Install the official IIIF Presentation Validator | ✅ done |
| 15 | Test fixtures | ✅ done |
| 16 | Unit tests — IIPImage URLs and tree scanning | ✅ done (1 documented deviation) |
| 17 | Unit tests — all four builders | ✅ done (6 documented deviations) |
| 18 | Unit tests — full generate/write pipeline | ✅ done |
| 19 | End-to-end tests with the official validator | ✅ done (4 builder fixes required) |
| 20 | README | ✅ done |
| 21 | Final end-to-end verification (all versions) | ✅ done |

## Log

### Step 0: Save this plan document — ✅ DONE (2026-09-13)

- **Action:** Verified the plan document already exists (satisfied by the input to this execution).
- **Verification:** `ls plans/` → `2026-09-11_v1_iiif-manifest-generator-plan.md` present, 2338 lines, non-empty.
- **Result:** PASS.

### Step 1: Project scaffolding — ✅ DONE (2026-09-13)

- **Files to touch:** `pyproject.toml`, `.gitignore`, `src/iiif_manifest_generator/__init__.py`, `src/iiif_manifest_generator/__main__.py`
- **Action:** Created `pyproject.toml`, `src/iiif_manifest_generator/__init__.py`, `src/iiif_manifest_generator/__main__.py` verbatim from the plan. `.gitignore` already existed in the project root with the exact expected content (verified byte-for-byte against the plan); kept as-is.
- **Verification:**
  - `pip install -e .` → `Successfully installed iiif-manifest-generator-0.1.0` (a stale prior editable install was uninstalled/replaced cleanly).
  - `python -c "import iiif_manifest_generator; print(iiif_manifest_generator.__version__)"` → `0.1.0` ✓
  - Console script `iiif-manifest-generator` registered at `/home/rutger/miniforge3/bin/iiif-manifest-generator`.
  - Per plan, `python -m iiif_manifest_generator` not run yet (needs Step 13).
- **Result:** PASS.

### Step 2: Configuration module — ✅ DONE (2026-09-13)

- **Files to touch:** `src/iiif_manifest_generator/config.py`
- **Action:** Created `config.py` verbatim from the plan (`GenerationConfig` dataclass, `VERSIONS`, URL normalization, `image_api_version` property).
- **Verification:** Plan's heredoc check → `OK version: version must be one of 2.0, 2.1, 3.0, 4.0, got '9.9'`, `OK url: base_url must start with http:// or https://, got 'ftp://x'`, `OK config` — no traceback.
- **Result:** PASS.

### Step 3: Image detection & dimension probing — ✅ DONE (2026-09-13)

- **Files to touch:** `src/iiif_manifest_generator/images.py`
- **Action:** Created `images.py` verbatim from the plan (`IMAGE_EXTENSIONS`, `MIME_TYPES`, `is_image_file`, `get_image_size`, `mime_type`).
- **Verification:** Plan's heredoc check → `OK corrupt: could not read image dimensions for /tmp/.../x.jpg: cannot identify image file ...` then `OK images module`.
- **Result:** PASS.

### Step 4: IIPImage URL construction — ✅ DONE (2026-09-13)

- **Files to touch:** `src/iiif_manifest_generator/iip.py`
- **Action:** Created `iip.py` verbatim from the plan (`build_identifier`, frozen `IipUrls` dataclass, `build_iip_urls` with Image-API-2 `square:256` vs Image-API-3 `square` thumbnail syntax).
- **Verification:** Plan's heredoc check → `OK iip module`.
- **Result:** PASS.

### Step 5: Shared data model — ✅ DONE (2026-09-13)

- **Files to touch:** `src/iiif_manifest_generator/models.py`
- **Action:** Created `models.py` verbatim from the plan with the `ImageInfo`, `DirectoryInfo` (with `label`, `has_manifest`, `documentable_children`, `has_collection` properties) and `GeneratedDocument` dataclasses.
- **Verification:** Plan's check → `OK models` with no traceback.
- **Result:** PASS.

### Step 6: Recursive tree scanner — ✅ DONE (2026-09-13)

- **Files to touch:** `src/iiif_manifest_generator/tree.py`
- **Action:** Created `tree.py` verbatim from the plan with `scan_tree` (entry sorting, hidden/symlink filtering, image probing), `_populate` (recursive population) and `_finalize` (post-order computation of `produces_documents`).
- **Verification:** Plan's heredoc check → `OK tree module` with all assertions passing (manifest + collection at root, manifest only at sub-dir, width/height/iip URLs correct).
- **Result:** PASS.

### Step 7: Shared builder helpers — ✅ DONE (2026-09-13)

- **Files to touch:** `src/iiif_manifest_generator/builders/base.py`
- **Action:** Created `builders/base.py` verbatim from the plan (constants `MANIFEST_FILENAME`/`COLLECTION_FILENAME`, `_url_path`, `manifest_id`, `collection_id`, `child_document`).
- **Verification:** Plan's import check → `OK base`.
- **Result:** PASS.

### Step 8: IIIF 2.0 builder — ✅ DONE (2026-09-13)

- **Files to touch:** `src/iiif_manifest_generator/builders/v20.py`
- **Action:** Created `v20.py` verbatim from the plan (2.0 context, `@id`/`@type`, `sc:*` types, `sequences` → `canvases` → `images` with `ImageService2` + `level0.json` profile, manifest-level `attribution`/`license`/`thumbnail`, collection `members` including own manifest when image-bearing).
  - Note: first draft deviated from the plan; re-read the plan section verbatim and rewrote the file to match exactly (confirmed by code-block diff audit, see below).
- **Verification:** Plan's heredoc check → `OK v20` (manifest context/@id/@type/sequence/canvas + collection with 2 members).
- **Result:** PASS.

### Step 9: IIIF 2.1 builder — ✅ DONE (2026-09-13)

- **Files to touch:** `src/iiif_manifest_generator/builders/v21.py`
- **Action:** Created `v21.py` verbatim from the plan (2.1 context, `id`/`type` keys, Image API 2.1 profile).
- **Verification:** Plan's heredoc check → `OK v21`.
- **Result:** PASS.

### Step 10: IIIF 3.0 builder — ✅ DONE (2026-09-13)

- **Files to touch:** `src/iiif_manifest_generator/builders/v30.py`
- **Action:** Created `v30.py` verbatim from the plan (3.0 context, LanguageMap labels, `items` → Canvas → AnnotationPage → Annotation with `body`/`target`, `rights`/`requiredStatement`, array thumbnails, `_image_service` branching Image API 2 default / 3 with `--image-api-3`).
- **Verification:** Plan's heredoc check → `OK v30` (canvas/page/annotation structure, `ImageService2` body by default, thumbnail array, collection with 2 items).
- **Result:** PASS.

### Step 11: IIIF 4.0 builder + builder registry — ✅ DONE (2026-09-13)

- **Files to touch:** `src/iiif_manifest_generator/builders/v40.py`, `src/iiif_manifest_generator/builders/__init__.py`
- **Action:** Created `v40.py` verbatim (4.0 context, plain-string labels, `motivation` as array, body = `Image` + `service` array with 2-style or 3-style service entry) and `builders/__init__.py` verbatim (`BUILDERS` registry + `build_documents` dispatcher).
- **Verification:** Plan's heredoc check → `2.0/2.1/3.0/4.0 OK -> <context>` lines plus `OK builders registry`.
- **Result:** PASS.

**Verbatim audit (after Step 11):** Extracted every code block from the plan document and diffed against all files written so far (Steps 1–11, 13 files): **all EXACT MATCH** (0 problems).

### Step 12: Writer + generation orchestration — ✅ DONE (2026-09-13)

- **Files to touch:** `src/iiif_manifest_generator/writer.py`, `src/iiif_manifest_generator/generate.py`
- **Action:** Created `writer.py` verbatim (`write_documents` with dry-run stdout mode) and `generate.py` verbatim (`generate`, `collect_documents`, `_collect` pre-order traversal).
- **Verification:** Plan's heredoc check → `OK generate: ['collection.json', 'manifest.json', 'sub/manifest.json']`.
- **Result:** PASS.

### Step 13: CLI — ✅ DONE (2026-09-13)

- **Files to touch:** `src/iiif_manifest_generator/cli.py`
- **Action:** Created `cli.py` verbatim (argparse with required `--version` (choices) and `--base-url`, optional `--image-base-url`, `--attribution`, `--license`, `--include-hidden`, `--keep-extension`, `--no-thumbnails`, `--image-api-3`, `--dry-run`, `-v`).
- **Verification:** Plan's shell sequence:
  - `pip install -e .` re-registered the console script; `--help` shows all options.
  - First run: `INFO: Generated 1 IIIF document(s) (Presentation 3.0).` + `manifest written`, exit 0.
  - 2.0 `--dry-run` printed the document to stdout (file unchanged).
  - `/nonexistent` → `error: root is not a directory: /nonexistent`, exit=2.
  - `--version 9.9` → argparse invalid choice, exit=2.
  - missing `--base-url` → argparse required-argument error, exit=2.
  - `--image-api-3` run → `OK api3` (body type `ImageService3`).
  - `python -m iiif_manifest_generator --help` also works (deferred Step-1 check now passing); `main([...bad root...])` returns rc=2.
- **Result:** PASS.

### Step 14: Install the official IIIF Presentation Validator — ✅ DONE (2026-09-13)

- **Files to touch:** `tools/presentation-validator/` (cloned, gitignored via `tools/`)
- **Action:** `git clone --depth 1 https://github.com/IIIF/presentation-validator.git tools/presentation-validator` + `pip install ./tools/presentation-validator` → `Successfully installed iiif-presentation-validator-1.0.1.dev1+gfb5bd9039` (a stale prior install was replaced cleanly).
- **Verification:**
  - `iiif-validator validate --help | grep -A2 -e "--version"` → `--version {1.0,2.0,2.1,3.0,4.0}` (plan's literal grep command mis-parses the pattern as grep's own `--version` flag; used `grep -A2 -e "--version"` which is equivalent in intent).
  - `python -c "import presentation_validator; ..."` → `OK validator import`.
- **Result:** PASS.

### Step 15: Test fixtures — ✅ DONE (2026-09-13)

- **Files to touch:** `tests/conftest.py`
- **Action:** Created `tests/conftest.py` verbatim from the plan (`image_tree` fixture building a nested gallery with 7 real raster images + empty dir; `make_config` fixture defaulting to version 3.0 / `http://localhost:8080`).
- **Verification:** `python -m pytest --collect-only -q` → `no tests collected in 0.00s` (no collection errors, as expected before test files exist).
- **Result:** PASS.

### Step 16: Unit tests — IIPImage URLs and tree scanning — ✅ DONE (2026-09-13)

- **Files to touch:** `tests/test_iip.py`, `tests/test_tree.py`
- **Action:** Created both test files verbatim from the plan, **except one documented deviation** (see below).
- **⚠️ Deviation (plan bug):** Plan line 1774 in `tests/test_tree.py::test_nested_structure` asserts `not nested.has_collection`, but this contradicts:
  1. the plan's own model (`DirectoryInfo.has_collection = produces_documents and bool(children)` — plan Step 5), which yields `True` for `alpha/nested` (it has image `d.jpg` and child `deep/`);
  2. plan line 2034 in Step 18 (`test_generate.py`), whose expected file set **includes** `alpha/nested/collection.json`;
  3. the fact that `alpha` and `nested` are structurally identical (1 image + 1 document-producing subdirectory), so no local-structure predicate can make `alpha.has_collection` True while `nested.has_collection` is False.
  - **Resolution:** flipped the single assertion to `assert nested.has_collection` (with an in-code NOTE explaining the deviation). This is the minimal change and keeps Steps 5, 6, 18, 19 and 21 mutually consistent while still satisfying Step 16's verification criterion (all 12 tests pass).
- **Verification:** `python -m pytest tests/test_iip.py tests/test_tree.py -v` → **12 passed in 0.08s**, no errors.
- **Result:** PASS (with documented deviation).

### Step 17: Unit tests — all four builders — ✅ DONE (2026-09-13)

- **Files to touch:** `tests/test_builders.py`
- **Action:** Created the file as the concatenation of the plan's two parts ("Action 1 of 2" + "Action 2 of 2"), verbatim **except 6 documented deviations** (see below).
- **⚠️ Deviations (plan bug ×6):** The plan's thumbnail assertions `...endswith("square:256/0/default.")` (plan lines 1880, 1895, 1922, 1935, 1960, 1971) can never be true: the plan's own `iip.py` — and its own Step 4 test (`assert u.thumbnail_url == "http://img/a/b/c/full/square:256/0/default.jpg"`) — include the file extension in thumbnail URLs, so `"...default.jpg".endswith("...default.")` is False.
  - **Resolution:** changed each of the 6 assertions from `X.endswith(Y)` to `Y in X` (with in-code NOTEs). This preserves the assertions' intent (verify the Image API 2 `square:256` size syntax vs Image API 3 `square`) without over-specifying the extension.
- **Verification:** `python -m pytest tests/test_builders.py -v` → **11 passed in 0.12s**, no errors.
- **Result:** PASS (with 6 documented deviations).

### Step 18: Unit tests — full generate/write pipeline — ✅ DONE (2026-09-13)

- **Files to touch:** `tests/test_generate.py`
- **Action:** Created verbatim from the plan (expected file set incl. `alpha/nested/collection.json` — which also confirms the Step-16 deviation resolution was correct; empty-dir skipping; idempotency; dry-run writes nothing).
- **Verification:** `python -m pytest tests/test_generate.py -v` → **4 passed in 0.08s**.
- **Result:** PASS.

### Step 19: End-to-end tests with the official validator — ✅ DONE (2026-09-13)

- **Files to touch:** `tests/test_e2e_validator.py` (created verbatim); **plus corrective fixes to the builders** — explicitly sanctioned by the plan (line 2130): *"If a case fails, read the printed validator output, fix the corresponding builder, and re-run until green."*
- **Action:** Created the 6-case e2e test verbatim. First run: **all 6 cases failed** — the plan's builder output does not pass the installed official validator. Root causes diagnosed from validator output + the validator's own code/schemas, then fixed in the builders (each fix empirically verified before applying):

  1. **`builders/v20.py`** — official validator (iiif_prezi) requires `on` on the `oa:Annotation` itself (`oa:Annotation['on'] not present and required`); the plan only put `on` inside `resource`. **Fix:** added annotation-level `"on": canvas_id` (kept the resource-level one so the plan's Step-17 unit test still passes).
  2. **`builders/v21.py`** — iiif_prezi's `ManifestReader.contexts` maps **both** 2.0 and 2.1 to `http://iiif.io/api/presentation/2/context.json` (the 2.1 context string → "Top level @context is not known"), and 2.x resources must use `@id`/`@type` ("Every resource must have @type"). **Fix:** v21 now emits 2.0-style `@id`/`@type` with the 2.0 context + annotation-level `on`, keeping the Image API 2.1 profile (the 2.1-specific element the validator does check). Documented in a file-header NOTE.
  3. **`builders/v30.py`** — the bundled 3.0 schema's `@context` oneOf is `[array of http(s) URIs, {"const": "http://iiif.io/api/presentation/3/context.json"}]` — the **http** string; the plan's `https://` matched neither branch. **Fix:** context → `http://iiif.io/api/presentation/3/context.json`.
  4. **`builders/v40.py`** — 4.0 schema requires: (a) `@context` const `http://iiif.io/api/presentation/4/context.json` (http, not https); (b) all `label`/`value` as lngString objects `{"none": [...]}` (plain strings rejected); (c) annotation `target` as a typed object (CanvasRef `{"id", "type": "Canvas"}`), not a URI string. The validator's unique-id check ignores `target`/`body` fields, so the reused canvas id is safe. **Fix:** added `_label()` helper, http context, CanvasRef target; all labels converted.

- **⚠️ Deviations in `tests/test_builders.py` (consequential to the builder fixes, all with in-code NOTEs):**
  - `test_v21_manifest_structure`: assertions switched to 2.0 context + `@id`/`@type` keys (plan's 2.1 context/id-type assertions are unsatisfiable by the official validator).
  - `test_v30_manifest_structure_defaults_to_image_api_2` and `test_v40_manifest_structure_defaults_to_image_api_2`: context assertions https → http; 4.0 label assertion `"gallery"` → `{"none": ["gallery"]}`.
  - `test_ids_unique_within_every_document`: `id_key` now `"@id"` for 2.1 too; `_collect_ids` skips `target`/`body` fields, mirroring the official validator's unique-id ignore list (`presentation_validator/v4/unique_ids.py`).
- **Verification:**
  - `python -m pytest tests/test_e2e_validator.py -v` → **6 passed in 3.18s** (2.0, 2.1, 3.0 default, 3.0 `--image-api-3`, 4.0 default, 4.0 `--image-api-3` — every generated document accepted by the official validator).
  - Full suite `python -m pytest tests/` → **33 passed in 2.99s** (no regressions in the 27 unit tests).
- **Result:** PASS (the plan's key validity gate is green).

### Step 20: README — ✅ DONE (2026-09-13)

- **Files to touch:** `README.md`
- **Action:** Created `README.md` with exactly the content of the plan's four-backtick markdown fence.
- **Verification:**
  - `test -f README.md && grep -c "iiif-manifest-generator" README.md` → `5` (≥ 5 as required).
  - Byte-level comparison against the plan's four-backtick fence content → **EXACT MATCH** (a generic 3-backtick fence diff shows a spurious 0.39 similarity because the README contains inner ```bash fences inside the plan's ```` fence; the dedicated four-backtick extraction confirms an exact match).
- **Result:** PASS.

### Step 21: Final end-to-end verification (all versions) — ✅ DONE (2026-09-13)

- **Files to touch:** none (verification only)
- **Action & Verification (plan's full check):**
  - `python -m pytest -q` → **33 passed in 3.06s** ✓ (27 unit + 6 official-validator e2e).
  - Demo tree built at `/tmp/demo-images` (`cover.jpg` + `books/vol1/page{1..3}.png`).
  - For each of 2.0/2.1/3.0/4.0: generation logged `INFO: Generated 4 IIIF document(s)` and `iiif-validator validate-dir` reported **Total: 4, Passed: 4, Failed: 0** (exit 0) ✓.
  - `find /tmp/demo-images -name '*.json' | sort` → exactly the four expected files:
    `/tmp/demo-images/collection.json`, `/tmp/demo-images/manifest.json`, `/tmp/demo-images/books/collection.json`, `/tmp/demo-images/books/vol1/manifest.json` ✓.
  - Spot-check `python -m json.tool /tmp/demo-images/manifest.json | head -30` → well-formed 4.0 manifest (http context, lngString labels, canvas/page/annotation structure) ✓.
  - **Appendix manual verification #1 (URL-mode validation)** — served `/tmp/demo-images` with `python -m http.server 8080`:
    - `iiif-validator validate --version 3.0 http://localhost:8080/manifest.json` → `{"okay": 1, "warnings": [], "error": ""}`, exit 0 (also proves each document's `id` matches its served URL) ✓.
    - `iiif-validator validate --version 4.0 http://localhost:8080/collection.json` → `{"okay": 1, "warnings": [], "error": ""}`, exit 0 ✓.
  - **Appendix manual verification #2 (Mirador viewer smoke test)** — not executable in this headless sandbox (no interactive browser). The HTTP fetchability half is proven by the URL-mode validation above; loading `http://localhost:8080/manifest.json` in https://iiif.io/viewer is the remaining user-side check.
  - **Appendix manual verification #5 (dry-run)** — `--dry-run` printed the document to stdout and `find /tmp/demo-dry -name '*.json' | wc -l` → `0` ✓.
  - **Appendix edge cases not covered by unit tests, verified ad hoc:**
    - Root with no images anywhere → zero documents, `WARNING: No images found under /tmp/no-images; nothing was generated.`, CLI exit 0 ✓.
    - Multi-dot filename `archive.tar.jpg` → identifier `archive.tar` (extension split at last dot), body id `…/archive.tar/info.json` ✓.
    - Uppercase extension `PHOTO.PNG` → recognized, identifier `PHOTO` (case kept), document validates ✓.
- **Result:** PASS — all of Step 21's verification criteria met; the plan's final validation matrix is green.

---

## Execution complete

- **All 22 plan steps (0–21) executed and verified.** Final state: `python -m pytest` → **33 passed**; official IIIF Presentation Validator accepts every generated document for 2.0, 2.1, 3.0, 4.0 (and both Image API modes for 3.0/4.0), in file mode and URL mode.
- **Deviations from the plan (all documented in-code with NOTE comments):**
  1. `tests/test_tree.py` (plan line 1774): `not nested.has_collection` → `nested.has_collection` (plan bug; contradicts the plan's own model and Step 18's expected file set).
  2. `tests/test_builders.py` (plan lines 1880/1895/1922/1935/1960/1971): six thumbnail `endswith("…/default.")` assertions → `"…/default." in …` (plan bug; the plan's own iip.py includes the file extension).
  3. `builders/v20.py`: added annotation-level `on` (official validator requirement).
  4. `builders/v21.py`: 2.0-style `@id`/`@type` + 2.0 context (iiif_prezi cannot parse the 2.1 context string; 2.1-ness preserved via the Image API 2.1 profile).
  5. `builders/v30.py`: context `https://` → `http://` (3.0 schema const).
  6. `builders/v40.py`: context `https://` → `http://` (4.0 schema const); labels/metadata → lngString objects; annotation `target` → CanvasRef object (4.0 schema Target.json).
  7. `tests/test_builders.py` (consequential to 3–6): v21/v30/v40 context & key-style assertions, 4.0 label assertion, `id_key` for 2.1, and `_collect_ids` skipping `target`/`body` (mirrors the validator's unique-id ignore list).
- **Verbatim audit:** every other file (pyproject.toml, .gitignore, `__init__.py`, `__main__.py`, config, images, iip, models, tree, base, builders registry, writer, generate, cli, conftest, test_iip, test_tree, test_generate, test_e2e_validator, README) is a byte-for-byte match with the plan's code blocks.
- **Sub-agent note:** this environment has no sub-agent spawning tool; each step was executed as a strictly isolated sequential phase (implement → verify with the plan's own command → log) with no next step started until the previous was green, as required.
