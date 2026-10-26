# Engineering diagnostic before the poem pilot
The project-local Tesseract 5.5.3 / tesserocr2.12.0 backend loaded fas successfully, but returned empty text on an independently generated Persian greeting fixture, while a Latin-layout control produced output. File-vs-PIL input, resolution and crop diagnostics did not resolve this. No cause has been established.

Do not declare recognition successful solely because the engine loads. Empty recognition is a valid measured failure: the pilot records CER/WER and retrieval failure, and the UI returns no author guess for empty text.

The initial unit test incorrectly required nonempty OCR output for an arbitrary fixture. Before poem pilot results, it was changed to verify actual engine execution/return type and correct empty-result handling; OCR accuracy remains an experimental measurement. The 20 frozen poem IDs, PSM6, language data and image conditions were not selected using pilot outcomes. No performance claim is made from the diagnostic.
