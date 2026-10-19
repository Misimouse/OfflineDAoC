param(
    [Parameter(Mandatory=$true)][string]$InstallRoot,
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)
$ErrorActionPreference = 'Stop'
$sourceProject = Join-Path $InstallRoot 'new-client\godot'
$sourceProject = (Resolve-Path -LiteralPath $sourceProject).Path
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
if ($sourceProject -eq $ProjectRoot) { throw 'La copia de desarrollo debe estar separada del juego.' }
$content = Join-Path $ProjectRoot 'content'
if (Test-Path -LiteralPath $content) {
    throw 'Ya existe content. No se sobrescriben recursos de desarrollo. Revisa o prepara otra copia.'
}
if (!(Test-Path -LiteralPath "$sourceProject\content\zones\zone207\zone.json")) { throw 'Falta Ardee en la instalacion indicada.' }
New-Item -ItemType Directory -Path "$content\zones", "$ProjectRoot\.godot\mono\temp\bin\Debug" -Force | Out-Null
Copy-Item -LiteralPath "$sourceProject\content\.gdignore" -Destination "$content\.gdignore"
Copy-Item -LiteralPath "$sourceProject\content\zones\zone207" -Destination "$content\zones\zone207" -Recurse
foreach ($name in @('sky','ui','rules','classes','companions','quests','world','sounds')) {
    Copy-Item -LiteralPath "$sourceProject\content\$name" -Destination "$content\$name" -Recurse
}
Get-ChildItem -LiteralPath "$sourceProject\content\zones" -File | Copy-Item -Destination "$content\zones"
Get-ChildItem -LiteralPath "$sourceProject\.godot\mono\temp\bin\Debug" -File | Copy-Item -Destination "$ProjectRoot\.godot\mono\temp\bin\Debug"
foreach ($name in @('global_script_class_cache.cfg','uid_cache.bin','.gdignore')) {
    Copy-Item -LiteralPath "$sourceProject\.godot\$name" -Destination "$ProjectRoot\.godot\$name"
}
$rows = foreach ($file in (Get-ChildItem -LiteralPath $content -Recurse -File)) {
    $relative = [IO.Path]::GetRelativePath($content, $file.FullName)
    $source = Join-Path "$sourceProject\content" $relative
    $hash = (Get-FileHash -LiteralPath $file.FullName).Hash
    if ($hash -ne (Get-FileHash -LiteralPath $source).Hash) { throw "Copia incorrecta: $relative" }
    [pscustomobject]@{path=$relative;sha256=$hash;bytes=$file.Length}
}
$session = Join-Path $ProjectRoot '.enhanced-session'
New-Item -ItemType Directory -Path $session -Force | Out-Null
$rows | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath "$session\copied-content.json" -Encoding utf8
Write-Output "Preparados y verificados $($rows.Count) archivos. Sin cuentas, DB ni guardados."
