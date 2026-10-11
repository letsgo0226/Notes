param([Parameter(ValueFromRemainingArguments=$true)][string[]]$HSIArgs)
$ErrorActionPreference="Stop"
$Ref=if($env:HSI_BUNDLE_REF){$env:HSI_BUNDLE_REF}else{"main"}
$Dir=if($env:HSI_BOOTSTRAP_HOME){$env:HSI_BOOTSTRAP_HOME}else{Join-Path $HOME ".hsi-bootstrap"}
New-Item -ItemType Directory -Force -Path $Dir | Out-Null
$Py=$null
if(Get-Command py -ErrorAction SilentlyContinue){$Py=@{Cmd="py";Prefix=@("-3")}}
elseif(Get-Command python3 -ErrorAction SilentlyContinue){$Py=@{Cmd="python3";Prefix=@()}}
elseif(Get-Command python -ErrorAction SilentlyContinue){$Py=@{Cmd="python";Prefix=@()}}
if($null -eq $Py){throw "Python 3.9+ required. Install Python 3 and rerun."}
$App=Join-Path $Dir "hsi_bootstrap.py"
$Tmp="$App.tmp.$PID"
try {
  Invoke-WebRequest -UseBasicParsing "https://raw.githubusercontent.com/letsgo0226/Notes/$Ref/hsi_bootstrap.py" -OutFile $Tmp
  if((Get-Item $Tmp).Length -le 0){throw "Downloaded bootstrap is empty."}
  Move-Item -Force $Tmp $App
} finally {Remove-Item -Force -ErrorAction SilentlyContinue $Tmp}
$invoke=@();$invoke+=$Py.Prefix;$invoke+=$App;$invoke+="native";$invoke+=$HSIArgs
& $Py.Cmd @invoke
exit $LASTEXITCODE
