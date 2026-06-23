# 注释说明：该 PowerShell 脚本用于本地项目完整性检查，注释帮助理解检查项来源。
$ErrorActionPreference = "Stop"
$root = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
$dataset = Join-Path $root "data\dataset"
$files = Get-ChildItem -LiteralPath $root -Recurse -File -Force -ErrorAction SilentlyContinue |
    Where-Object {
        $_.FullName -notlike "*\.git\*" -and
        $_.FullName -notlike "*\node_modules\*" -and
        $_.FullName -notlike "*\backend\pytest-cache-files-*"
    }
$pdfs = Get-ChildItem -LiteralPath $dataset -File -Filter *.pdf
[pscustomobject]@{
    Root = $root.Path
    Files = $files.Count
    Bytes = ($files | Measure-Object Length -Sum).Sum
    DatasetFiles = $pdfs.Count
    DatasetBytes = ($pdfs | Measure-Object Length -Sum).Sum
}
