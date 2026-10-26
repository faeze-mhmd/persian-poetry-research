# Actual OCR/ASR engineering pilot
Executed 2026-10-25. The original text classification and retrieval studies remain frozen.

OCR used project-local tesserocr2.12.0/Tesseract5.5.3, pinned fas language data, PSM6, and20 frozen couplets with two fixed renderings each. ASR used vosk0.3.45/vosk-model-small-fa-0.42 on three actual recitation excerpts. No training, grammar hints or tuning on pilot outcomes occurred.

| Condition | N | Pooled CER | Pooled WER | Known-item Recall@1 |
|---|---:|---:|---:|---:|
| rendered_ocr/clean | 20 | 0.4214 | 0.4305 | 0.8000 |
| rendered_ocr/degraded | 20 | 0.1814 | 0.2152 | 1.0000 |
| recitation_asr/upstream_timed | 3 | 0.2282 | 0.4808 | 1.0000 |

Inference pilot wall time 8.96s; peak working set 406.6MiB. Download/install time is excluded. CER/WER pools character/token counts after canonical normalization without author masking. Retrieval uses the existing masked character TF-IDF index.

The40 images are synthetic renderings, not photographs or handwriting. The transformed images outperformed clean images on this small set; that does not establish that blur helps OCR. Geometry and segmentation changed along with quality. Empty OCR on a separate greeting fixture was retained in MEDIA_ENGINE_DIAGNOSTIC.md. The UI returns no author guess for empty recognition.

Three speech clips are an exploratory integration pilot, not a representative ASR benchmark. Upstream timestamps/reference verses were checked against pinned source text but were not independently human-listened/verified. Two preselected poems had no eligible reading and were skipped without post-transcript substitution. High retrieval success despite about48% WER does not show accurate transcription or unseen-poem attribution. No inferential interval is used for N=3.

Sources: [Tesseract language data](https://github.com/tesseract-ocr/tessdata_fast), [tesserocr distribution](https://pypi.org/project/tesserocr/2.12.0/), [official Vosk models](https://alphacephei.com/vosk/models), [Vosk example](https://github.com/alphacep/vosk-api/blob/master/python/example/test_simple.py), [Ganjoor API](https://api.ganjoor.net/index.html). Source URLs, sizes and SHA-256 hashes are recorded.

Normal pip installation failed on Windows temporary-file renames. Registry-hash-verified wheel extraction into media_runtime was used instead; global Python packages, PATH, registry, ACLs and security settings were not changed. The pure-Python srt module came from its registry-verified source archive without running setup code. Official-host model downloads used checked byte ranges and ZIP integrity checks. Raw images/audio/transcripts, native libraries and weights are local only.

Run from the complete local working folder:
- python -B run_media_cli.py --check
- python -B run_media_cli.py --image YOUR_IMAGE.png
- python -B run_media_cli.py --audio YOUR_SHORT_AUDIO.wav
- python -B serve_demo.py --port 8787

Then open http://127.0.0.1:8787. File cap5MiB; audio cap60seconds; all inference is local. Author classification was evaluated on full poems, so short-transcript guesses are exploratory. Preserve exclusive run markers. A larger real-image/speech dataset is future work beyond this completed bounded prototype.
