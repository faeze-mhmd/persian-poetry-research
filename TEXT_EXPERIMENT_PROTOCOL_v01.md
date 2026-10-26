# Persian poetry text experiment — design v0.1

Specified 2026-10-22, after the 100-poem development audit and before any model fitting or test performance. Status: DESIGN SPECIFIED; EXECUTION GATES PENDING. This is a local versioned design, not a public preregistration or a completed experiment.

The companion text_experiment_v01.json gives the exact decisions. Data IDs, implementations and source hashes cannot yet be frozen: they will be recorded at the pre-training gate. Any design revision must receive a new version and explanation before test performance, preserving this version.

## Research question and primary comparison

Does a character TF-IDF model lose less macro-F1 than a word TF-IDF model under a fixed synthetic letter-error stress test? One fixed, five-author, poem-level split is the assessment context. A positive primary DeltaDrop favors lower degradation for characters, not necessarily better clean accuracy or universal superiority.

Use one shared LinearSVC specification: C=1.0, l2/squared_hinge, dual=auto, tol=0.0001, one-vs-rest, intercept enabled, class_weight=None, random_state=20261025, max_iter=10000. TF-IDF word n-grams are 1–2; character n-grams are 3–5. Shared parameters include min_df=2, max_df=1.0 (FLOAT), max_features=50000, L2 row normalization and sublinear TF. Vocabulary and IDF are fitted on training only. Equal caps do not establish matched model capacity.

Run 8 clean conditions: two feature families × minimal/canonical input normalization × shared-author masking off/on. Add a training-label majority classifier, for 9 clean readouts. The declared primary pair is canonical normalization plus shared-author masking, word versus character. The other six learned models are secondary clean-only sensitivity comparisons; no noisy-result search across all conditions.

The installed sklearn 1.9.0 constructors were checked against local signatures. Online stable documentation currently describes 1.9.1, so that is not a claim that 1.9.1 was installed. No fresh environment or packages were installed.

## Source, acquisition and eligibility

Pinned Ganjoor revision: 86455ef602c55f64282ce9a0fba4b1084153b5a7.
Five candidate categories: Hafez ghazal; Saadi divan/ghazals; Molana shams/ghazalsh; Saeb divan-saeb/ghazalkasa; Bidel ghazalbi.

Target, not an acquired dataset: 200 retained independent-component representatives per author (1000 poems). At most 300 new source files per author/1500 total, 30 MiB total and 512 KiB/file. Inspect in the recorded selection-priority order, skipping the 100 previously inspected IDs; preserve all requests, hashes and rejection reasons. If any quality, count or resource gate fails, stop and version the design rather than silently relaxing it.

Require matching positive IDs; VOrder exactly 1..N; nonempty verse text; one WholePoem section tagged Ghazal; 4–30 couplets with two verses per couplet; 40–600 audit-canonical whitespace tokens; at least 90% Arabic-script letters among letters. The script check does not certify Persian-only language. Text is ordered Verses.Text once. Never use titles, summaries, paths, author/source metadata or duplicated Sections text as features.

The 100 inspected audit poems remain development material. The structurally valid Saadi MultiBand record 9374 illustrates why the ghazal category name is insufficient. Candidate eligibility remains untested beyond the bounded audit; no final usable corpus size is claimed.

## Duplicate graph and development exclusion

Build a deterministic graph on inspected development poems plus new candidates, using audit-v1 normalization. Connect:
1. identical full normalized poems;
2. normalized character-5 set Jaccard >=0.80;
3. at least two distinct identical normalized couplets, each with >=6 whitespace tokens.

Use exact checks; safe cardinality pruning is allowed, but an approximate search cannot silently replace them. Preserve edges/components and their reasons. Exclude every component touching a development poem, and every mixed-author component. Such exclusion is conservative about quotation/attribution, not a finding that the source's author labels are false.

Retain one representative per remaining single-author component: lowest SHA-256 priority of ASCII 'poetry-text-v1|20261023|PoetId|PoemId', then integer Id for exact hash ties. Select the first 200 representatives per author in that order. These heuristics do not guarantee the absence of all partial quotations or shared editorial provenance.

## Frozen split planned before fitting

Within each author's 200 representatives, order by SHA-256 of ASCII 'split-v1|20261024|PoetId|PoemId', then integer Id:
- first 120 training;
- next 40 validation;
- final 40 test.

Totals are 600/200/200 if the acquisition/grouping gates succeed. One representative per component prevents graph components crossing the split. Save all IDs, component membership, labels and hashes; no validation refit or post-test reselection.

This is a closed-set, five-author task on full poems. Unknown-author detection, short-query retrieval, cross-era generalization and modern poets are separate questions. It is not a replication of the 67-author PARSI evaluation or a directly comparable benchmark score.

## Masking and normalization

Use the same predeclared list in every class: حافظ، سعدی، مولانا، مولوی، رومی، شمس، صائب، بیدل.
Find maximal Unicode L/M runs in the source; canonicalize each run only for exact alias lookup and replace matching source spans once with the shared ASCII token MASKEDAUTHOR before either normalization. Do not supply the true class to a label-specific mask.

Minimal input preserves marks, script variants, ZWNJ and punctuation, apart from joining verses and normalizing CRLF. Canonical input applies NFKC, documented ya/kaf mappings, Arabic-mark/tatweel stripping, ZWNJ-to-space and whitespace collapsing; punctuation is preserved. This model canonicalization differs from the punctuation-removing audit duplicate view.

The mask is incomplete and deliberately includes some ordinary words. It changes the task; mask positions/counts remain possible cues. Report it as sensitivity control, not proof of pure stylistic authorship. Human-reviewed additions or changed normalization require a versioned pre-test change.

## Synthetic corruption, pairing and achieved error

Only the primary pair plus majority receive noisy evaluation. Start from the same clean canonical, already masked string. Corrupt eligible characters in the explicitly listed 33-symbol Persian alphabet. The ASCII mask token, punctuation and whitespace are protected. Thus the stress test excludes known masked-name letters; it is not a natural OCR or ASR error distribution.

Rates are 0, 2%, 5%, 10% of eligible original letter positions; 5% is primary. Use development seeds 1101–1103 and held-out test corruption seeds 2101–2103. Derive each PCG64 seed from the first eight SHA-256 bytes of ASCII 'noise-v1|Seed|PoemId', big endian.

For each poem/seed, use one permutation of eligible source positions. At integer percentage p, choose k=(p*N+50)//100; severities use nested prefixes. Each selected source position has a stable insertion/deletion/substitution draw with equal probability. Insert a uniformly chosen alphabet symbol before the original; delete the original; or substitute uniformly excluding the original. No position is recursively edited.

The same generated query is passed to both primary feature models and majority. No fitting or noisy-data augmentation occurs. Report selected positions, operation counts and actual Levenshtein CER/WER. Remove the exact artificial mask token from reference/query before computing errors; CER uses remaining codepoints and WER uses whitespace tokens. Nominal letter-selection rate is not achieved CER.

All 9 clean readouts plus 3 noisy readouts × 3 nonzero rates × 3 noise seeds produce 36 readout-condition records. There are 9 fitted classifiers, not 36 independent models.

## Outcomes, uncertainty and interpretation

Save accuracy, fixed-label macro-F1, per-author precision/recall/F1/confusion, all predictions, warning/iteration/feature counts and timings.

Primary:
DeltaDrop = [word clean F1 - mean(word F1 at 5%, three noise seeds)] - [char clean F1 - mean(char F1 at 5%, three noise seeds)].

Report clean accuracies too: less degradation may simply start from a lower clean score. Use 2000 paired stratified bootstrap resamples (seed 20261028), drawing 40 poems with replacement within each test author and sharing indices across models/conditions/seeds. Report the 2.5/97.5 percentile interval for DeltaDrop. This is conditional on this fixed split and fitted models, not training-seed or unseen-author uncertainty; no p-values or universal superiority claim.

Length, period, vocabulary, editing and imperfect aliases can confound style. Synthetic robustness does not establish real-image/real-recitation performance. Keep later indexed retrieval outcomes separate from unseen-poem attribution.

## Execution and exit gates

CPU, one thread; no new package planned. First benchmark on audit/development material only. Acquisition/grouping cap: 1800s; all classifier fitting cap: 900s; Python peak working set cap: 1 GiB. Keep warnings; never increase iterations or drop a weak model silently. If the gate cannot be met, preserve artifacts and explicitly revise the design before test.

Before any test metrics: clear provenance/use scope, complete eligibility/rejection and duplicate manifests, frozen split IDs, meaningful normalizer/mask/noise/group/split/metric tests, source/config/environment fingerprints, recorded clean/noisy validation readouts and a separate final test plan with an exclusive per-output start marker. A marker prevents accidental overwrite of that output, not global deliberate re-evaluation.

No acquisition of the planned 1000 poems, model fitting, test outcome or Git/publication is performed by recording this design.

References:
- PARSI: https://arxiv.org/abs/2506.21840
- TF-IDF API: https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html
- LinearSVC API: https://scikit-learn.org/stable/modules/generated/sklearn.svm.LinearSVC.html
