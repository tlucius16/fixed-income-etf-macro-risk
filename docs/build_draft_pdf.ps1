$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$source = Join-Path $root "docs\draft.md"
$output = Join-Path $root "docs\draft.pdf"
$stylesheet = Join-Path $root "docs\paper_print.css"
$requiredFigure = Join-Path $root "docs\figures\fragility_deciles.png"
$temporary = Join-Path $env:TEMP "draft_formatted.md"
$temporaryHtml = Join-Path $env:TEMP "draft_formatted.html"
$edgeProfile = Join-Path $env:TEMP ("bond-etf-paper-edge-" + [Guid]::NewGuid())
$buildStarted = Get-Date

if (-not (Test-Path -LiteralPath $requiredFigure)) {
    throw "Missing generated paper figure. Run: python scripts/08_paper_artifacts.py"
}

$lines = Get-Content -Encoding utf8 $source
$title = $lines[0] -replace '^#\s+', ''
$author = $lines[2] -replace '^\*\*|\*\*.*$', ''
$email = $lines[3] -replace '<br>', ''
$date = $lines[4]

$abstractStart = [Array]::IndexOf($lines, "## Abstract") + 1
$abstractEnd = $abstractStart
while ($abstractEnd -lt $lines.Count -and $lines[$abstractEnd] -ne "---") {
    $abstractEnd++
}
$introduction = [Array]::IndexOf($lines, "## 1. Introduction")

$formatted = @(
    "---"
    "title: `"$title`""
    "author:"
    "  - `"$author | $email`""
    "date: `"$date`""
    "abstract: |"
)
$formatted += $lines[$abstractStart..($abstractEnd - 1)] | ForEach-Object { "  $_" }
$formatted += @("---", "")
$formatted += $lines[$introduction..($lines.Count - 1)]

[IO.File]::WriteAllLines(
    $temporary,
    $formatted,
    [Text.UTF8Encoding]::new($false)
)

Push-Location $root
try {
    & pandoc $temporary `
        -o $temporaryHtml `
        --standalone `
        --embed-resources `
        --mathml `
        --css $stylesheet `
        --resource-path $root `
        --shift-heading-level-by=-1
    if ($LASTEXITCODE -ne 0) {
        throw "Pandoc failed with exit code $LASTEXITCODE"
    }

    $edgeCandidates = @(
        (Join-Path ${env:ProgramFiles(x86)} "Microsoft\Edge\Application\msedge.exe"),
        (Join-Path $env:ProgramFiles "Microsoft\Edge\Application\msedge.exe")
    )
    $edge = $edgeCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if (-not $edge) {
        throw "Microsoft Edge was not found. Use docs/build_draft_pdf.sh with a TeX installation instead."
    }

    $htmlUri = [Uri]::new($temporaryHtml).AbsoluteUri
    & $edge `
        --headless=new `
        --disable-gpu `
        --no-pdf-header-footer `
        "--user-data-dir=$edgeProfile" `
        "--print-to-pdf=$output" `
        $htmlUri
    if ($LASTEXITCODE -ne 0) {
        throw "Edge PDF export failed with exit code $LASTEXITCODE"
    }
    $deadline = (Get-Date).AddSeconds(15)
    do {
        $generated = Get-Item -LiteralPath $output -ErrorAction SilentlyContinue
        if ($generated -and $generated.LastWriteTime -ge $buildStarted -and $generated.Length -gt 0) {
            break
        }
        Start-Sleep -Milliseconds 200
    } while ((Get-Date) -lt $deadline)
    if (-not $generated -or $generated.LastWriteTime -lt $buildStarted) {
        throw "Edge returned without writing a fresh PDF"
    }
}
finally {
    Pop-Location
    if (Test-Path -LiteralPath $edgeProfile) {
        $resolvedProfile = (Resolve-Path -LiteralPath $edgeProfile).Path
        $resolvedTemp = (Resolve-Path -LiteralPath $env:TEMP).Path
        if ($resolvedProfile.StartsWith($resolvedTemp, [StringComparison]::OrdinalIgnoreCase)) {
            Remove-Item -LiteralPath $resolvedProfile -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

Write-Output "OK -> $output"
