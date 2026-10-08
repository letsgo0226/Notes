param(
  [Parameter(ValueFromRemainingArguments=$true)]
  [string[]]$HSIArgs
)

$ErrorActionPreference = "Stop"
$Pin = "71be7f28917ec94abcb247db8b4150971c79e532"
$Base = "https://raw.githubusercontent.com/letsgo0226/Notes/$Pin"
$Dir = if ($env:HSI_CORPUS_HOME) { $env:HSI_CORPUS_HOME } else { Join-Path $HOME ".hsi-corpus" }
$App = Join-Path $Dir "hsi_open_corpus.py"
$Search = Join-Path $Dir "hsi_search.py"
$Net = Join-Path $Dir "hsi_net.py"
New-Item -ItemType Directory -Force -Path $Dir | Out-Null

function Resolve-HSIPython {
  $candidates = @(
    @{Cmd="py"; Prefix=@("-3")},
    @{Cmd="python3"; Prefix=@()},
    @{Cmd="python"; Prefix=@()}
  )
  foreach ($c in $candidates) {
    $cmd = Get-Command $c.Cmd -ErrorAction SilentlyContinue
    if ($null -ne $cmd) {
      try {
        & $c.Cmd @($c.Prefix) --version *> $null
        if ($LASTEXITCODE -eq 0) { return $c }
      } catch {}
    }
  }
  return $null
}

$Py = Resolve-HSIPython
if ($null -eq $Py) {
  throw "Python 3 is required. Install it from python.org or with: winget install Python.Python.3.13"
}

$TmpApp = "$App.tmp.$PID"
$TmpSearch = "$Search.tmp.$PID"
$TmpNet = "$Net.tmp.$PID"
try {
  Invoke-WebRequest -UseBasicParsing "$Base/hsi_open_corpus.py" -OutFile $TmpApp
  Invoke-WebRequest -UseBasicParsing "$Base/hsi_search.py" -OutFile $TmpSearch
  Invoke-WebRequest -UseBasicParsing "$Base/hsi_net.py" -OutFile $TmpNet
  if ((Get-Item $TmpApp).Length -le 0 -or (Get-Item $TmpSearch).Length -le 0 -or (Get-Item $TmpNet).Length -le 0) {
    throw "Downloaded HSI program is empty."
  }
  Move-Item -Force $TmpApp $App
  Move-Item -Force $TmpSearch $Search
  Move-Item -Force $TmpNet $Net
} finally {
  Remove-Item -Force -ErrorAction SilentlyContinue $TmpApp,$TmpSearch,$TmpNet
}

Write-Host "HSI Open-Corpus Renderer: no AI / HSI-SEARCH / Openverse CC0+PDM WAV / deterministic DSP"
Write-Host "bundle_commit> $Pin"
Write-Host "note> YouTube audio is not downloaded or sampled."
Write-Host "note> Openverse license metadata is indexed metadata; verify landing pages before publication/commercial reuse."

$invoke = @()
$invoke += $Py.Prefix
$invoke += $App
$invoke += $HSIArgs
& $Py.Cmd @invoke
exit $LASTEXITCODE
