param(
  [Parameter(ValueFromRemainingArguments=$true)]
  [string[]]$HSIArgs
)
$ErrorActionPreference="Stop"
$Pin="09d87a9b6fc615f616afd8adb1813677298a8190"
$Base="https://raw.githubusercontent.com/letsgo0226/Notes/$Pin"
$Dir=if($env:HSI_SOLVE_HOME){$env:HSI_SOLVE_HOME}else{Join-Path $HOME ".hsi-solve"}
$App=Join-Path $Dir "hsi_solve.py"
$Net=Join-Path $Dir "hsi_net.py"
$Search=Join-Path $Dir "hsi_search.py"
New-Item -ItemType Directory -Force -Path $Dir | Out-Null

$Py=$null
if(Get-Command py -ErrorAction SilentlyContinue){$Py=@{Cmd="py";Prefix=@("-3")}}
elseif(Get-Command python3 -ErrorAction SilentlyContinue){$Py=@{Cmd="python3";Prefix=@()}}
elseif(Get-Command python -ErrorAction SilentlyContinue){$Py=@{Cmd="python";Prefix=@()}}
if($null -eq $Py){throw "Python 3 required. Install with: winget install Python.Python.3.13"}

$T1="$App.tmp.$PID";$T2="$Net.tmp.$PID";$T3="$Search.tmp.$PID"
try{
  Invoke-WebRequest -UseBasicParsing "$Base/hsi_solve.py" -OutFile $T1
  Invoke-WebRequest -UseBasicParsing "$Base/hsi_net.py" -OutFile $T2
  Invoke-WebRequest -UseBasicParsing "$Base/hsi_search.py" -OutFile $T3
  foreach($x in @($T1,$T2,$T3)){if((Get-Item $x).Length -le 0){throw "Downloaded HSI component is empty."}}
  Move-Item -Force $T1 $App;Move-Item -Force $T2 $Net;Move-Item -Force $T3 $Search
}finally{Remove-Item -Force -ErrorAction SilentlyContinue $T1,$T2,$T3}

Write-Host "HSI SOLVE: finite meta-solver + self-deployment verifier"
Write-Host "bundle_commit> $Pin"
Write-Host "note> verification closure is not universal problem totality."
$invoke=@();$invoke+=$Py.Prefix;$invoke+=$App;$invoke+=$HSIArgs
& $Py.Cmd @invoke
exit $LASTEXITCODE
