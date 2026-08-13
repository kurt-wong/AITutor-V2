#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'

$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
$codexConfig = Join-Path $codexHome 'config.toml'

if (-not (Test-Path -LiteralPath $codexConfig)) {
    throw "Codex config not found: $codexConfig"
}

$backup = "$codexConfig.bak-$(Get-Date -Format 'yyyyMMddHHmmss')"
Copy-Item -LiteralPath $codexConfig -Destination $backup -Force

$dockerConfigPath = (Join-Path $env:USERPROFILE '.docker\config.json').Replace('\', '/')
$permissionsBlock = @"

[permissions]
default_permissions = { extends = ":workspace", network = { enabled = true, allow_local_binding = true, domains = { "localhost" = "allow", "127.0.0.1" = "allow", "::1" = "allow" } }, filesystem = { "$dockerConfigPath" = "read", "\\\\.\\pipe\\docker_engine" = "write" } }
"@

if (-not (Select-String -LiteralPath $codexConfig -Pattern '^\[permissions\]' -Quiet)) {
    Add-Content -LiteralPath $codexConfig -Value $permissionsBlock -Encoding UTF8
} else {
    Write-Warning "[permissions] already exists in $codexConfig; add the default_permissions block manually."
}

& net localgroup docker-users CodexSandboxOffline /add

Write-Host 'Done. Restart Docker Desktop and Codex before testing.'
