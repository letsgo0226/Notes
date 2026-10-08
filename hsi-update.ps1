param(
  [Parameter(Position=0,Mandatory=$true)]
  [string]$Artifact,
  [Parameter(ValueFromRemainingArguments=$true)]
  [string[]]$HSIArgs
)
$ErrorActionPreference="Stop"
$Base="https://raw.githubusercontent.com/letsgo0226/Notes/main"
$Dir=if($env:HSI_UPDATE_HOME){$env:HSI_UPDATE_HOME}else{Join-Path $HOME ".hsi-update"}
$App=Join-Path $Dir "hsi_update.py"
New-Item -ItemType Directory -Force -Path $Dir | Out-Null

$Py=$null
if(Get-Command py -ErrorAction SilentlyContinue){$Py=@{Cmd="py";Prefix=@("-3")}}
elseif(Get-Command python3 -ErrorAction SilentlyContinue){$Py=@{Cmd="python3";Prefix=@()}}
elseif(Get-Command python -ErrorAction SilentlyContinue){$Py=@{Cmd="python";Prefix=@()}}
if($null -eq $Py){throw "Python 3.9+ required."}

Invoke-WebRequest -UseBasicParsing "$Base/hsi_update.py" -OutFile $App
Write-Host "HSI UPDATE: artifact-driven finite update solver; no automatic source rewrite or git push."
$invoke=@();$invoke+=$Py.Prefix;$invoke+=$App;$invoke+=$Artifact;$invoke+=$HSIArgs
& $Py.Cmd @invoke
exit $LASTEXITCODE
