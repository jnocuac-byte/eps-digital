# Levanta la demo de EPS Digital (H-16) con un solo comando.
#   powershell -ExecutionPolicy Bypass -File .\levantar-demo.ps1
# Requiere GitHub CLI (gh) autenticado con scope codespace.
$ErrorActionPreference = "Continue"
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

$Repo   = "jnocuac-byte/eps-digital"
$Branch = "feat/h16-kubernetes"
$Name   = if ($env:CODESPACE_NAME) { $env:CODESPACE_NAME } else { "" }

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw "Falta GitHub CLI: winget install GitHub.cli" }

# 1) Buscar el Codespace del proyecto (por repo y nombre eps-h16); crearlo si no existe.
if (-not $Name) {
    $lista = gh codespace list --json name,displayName,repository,state | ConvertFrom-Json
    $cs = $lista | Where-Object { $_.repository -eq $Repo -and $_.displayName -eq "eps-h16" } | Select-Object -First 1
    if ($cs) { $Name = $cs.name } else {
        Write-Host "No hay Codespace: creandolo..."
        $Name = (gh codespace create -R $Repo -b $Branch -m standardLinux32gb --idle-timeout 240m --display-name eps-h16 2>$null | Select-Object -Last 1).Trim()
    }
}
Write-Host "Codespace: $Name"

# 2) Encenderlo si esta detenido (ssh lo arranca) y esperar a que este disponible.
for ($i = 0; $i -lt 60; $i++) {
    $estado = gh codespace view -c $Name --json state --jq .state
    if ($estado -eq "Available") { break }
    Write-Host "Estado: $estado ..."
    if ($estado -eq "Shutdown") { gh codespace ssh -c $Name -- "true" 2>$null | Out-Null }
    Start-Sleep 10
}

# 3) Desplegar (idempotente): arranca minikube, construye imagenes y espera los pods.
gh codespace ssh -c $Name -- "cd /workspaces/eps-digital && git pull -q --ff-only; bash k8s/deploy.sh"
if ($LASTEXITCODE -ne 0) { throw "deploy.sh fallo (revisar salida)" }

# 4) Puerto 8080 publico e imprimir la URL.
gh codespace ports visibility 8080:public -c $Name
$url = "https://$Name-8080.app.github.dev"
Write-Host ""
Write-Host "=========================================="
Write-Host " DEMO LISTA: $url"
Write-Host "=========================================="
try { $r = Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 60; Write-Host "Comprobacion: HTTP $($r.StatusCode)" } catch { Write-Host "Aun no responde, reintenta en 30 s." }
Write-Host "Al terminar: gh codespace stop -c $Name"
