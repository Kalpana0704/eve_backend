# Start Docker Desktop (if needed), wait for engine, then run compose.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Test-DockerEngine {
    docker version 2>$null | Select-String "Server:" -Quiet
}

if (-not (Test-DockerEngine)) {
    $dockerExe = "${env:ProgramFiles}\Docker\Docker\Docker Desktop.exe"
    if (-not (Test-Path $dockerExe)) {
        Write-Host "Docker Desktop is not installed. Install it from https://www.docker.com/products/docker-desktop/" -ForegroundColor Red
        exit 1
    }
    Write-Host "Starting Docker Desktop — wait until the engine is running (30–90 seconds)..." -ForegroundColor Yellow
    Start-Process $dockerExe
    $deadline = (Get-Date).AddMinutes(3)
    while (-not (Test-DockerEngine)) {
        if ((Get-Date) -gt $deadline) {
            Write-Host "Docker engine did not start in time. Open Docker Desktop manually and retry." -ForegroundColor Red
            exit 1
        }
        Start-Sleep -Seconds 3
    }
}

Write-Host "Docker engine is ready." -ForegroundColor Green
docker compose up --build
