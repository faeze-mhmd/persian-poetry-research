param([string]$Python = 'python',[int]$Port = 8787)
$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
if (-not (Test-Path -LiteralPath (Join-Path $taskRoot 'dataset_local.json'))) { $taskRoot = (Resolve-Path -LiteralPath (Join-Path $taskRoot '..')).Path }
if (-not (Test-Path -LiteralPath (Join-Path $taskRoot 'retrieval_index_local.joblib'))) { throw 'Use the complete local working project, not only the review ZIP.' }
& $Python -B (Join-Path $taskRoot 'serve_demo.py') --port $Port
