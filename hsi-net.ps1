param(
  [Parameter(ValueFromRemainingArguments=$true)]
  [string[]]$HSIArgs
)
$ErrorActionPreference="Stop"
$Pin="71be7f28917ec94abcb247db8b4150971c79e532"
$Base="https://raw.githubusercontent.com/letsgo0226/Notes/$Pin"
$Dir=if($env:HSI_NET_HOME){$env:HSI_NET_HOME}else{Join-Path $HOME ".hsi-net"}
$App=Join-Path $Dir "hsi_net.py"
New-Item -ItemType Directory -Force -Path $Dir | Out-Null

$Py=$null
if(Get-Command py -ErrorAction SilentlyContinue){$Py=@{Cmd="py";Prefix=@("-3")}}
elseif(Get-Command python3 -ErrorAction SilentlyContinue){$Py=@{Cmd="python3";Prefix=@()}}
elseif(Get-Command python -ErrorAction SilentlyContinue){$Py=@{Cmd="python";Prefix=@()}}
if($null -eq $Py){throw "Python 3 required. Install with: winget install Python.Python.3.13"}

$Tmp="$App.tmp.$PID"
try{
  Invoke-WebRequest -UseBasicParsing "$Base/hsi_net.py" -OutFile $Tmp
  if((Get-Item $Tmp).Length -le 0){throw "Downloaded HSI NET program is empty."}
  Move-Item -Force $Tmp $App
}finally{Remove-Item -Force -ErrorAction SilentlyContinue $Tmp}

Write-Host "HSI NET: formal global-information-field projection model; not a physical-singularity claim."
Write-Host "bundle_commit> $Pin"
$invoke=@();$invoke+=$Py.Prefix;$invoke+=$App;$invoke+=$HSIArgs
& $Py.Cmd @invoke
exit $LASTEXITCODE
