param(
  [Parameter(ValueFromRemainingArguments=$true)]
  [string[]]$HSIArgs
)
$ErrorActionPreference="Stop"
$Base="https://raw.githubusercontent.com/letsgo0226/Notes/main"
$Dir=if($env:HSI_DEPLOY_BOOTSTRAP_HOME){$env:HSI_DEPLOY_BOOTSTRAP_HOME}else{Join-Path $HOME ".hsi-bootstrap"}
$App=Join-Path $Dir "hsi_deploy.py"
$Net=Join-Path $Dir "hsi_net.py"
New-Item -ItemType Directory -Force -Path $Dir | Out-Null

$Py=$null
if(Get-Command py -ErrorAction SilentlyContinue){$Py=@{Cmd="py";Prefix=@("-3")}}
elseif(Get-Command python3 -ErrorAction SilentlyContinue){$Py=@{Cmd="python3";Prefix=@()}}
elseif(Get-Command python -ErrorAction SilentlyContinue){$Py=@{Cmd="python";Prefix=@()}}
if($null -eq $Py){throw "Python 3.9+ required; bootstrap does not install packages automatically."}

Invoke-WebRequest -UseBasicParsing "$Base/hsi_net.py" -OutFile $Net
Invoke-WebRequest -UseBasicParsing "$Base/hsi_deploy.py" -OutFile $App

if(-not $env:GITHUB_TOKEN -and -not $env:GH_TOKEN -and (Get-Command gh -ErrorAction SilentlyContinue)){
  try {
    $token = (& gh auth token 2>$null).Trim()
    if($token){$env:GITHUB_TOKEN=$token}
  } catch {}
  Remove-Variable token -ErrorAction SilentlyContinue
}

Write-Host "HSI Deploy Solver: self + UTM + Trader_42 + Omega"
Write-Host "policy> solve first; immutable commit resolution; no domain execution during deployment"
$invoke=@();$invoke+=$Py.Prefix;$invoke+=$App;$invoke+=$HSIArgs
& $Py.Cmd @invoke
exit $LASTEXITCODE
