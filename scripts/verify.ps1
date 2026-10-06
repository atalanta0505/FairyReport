<#
    FairyReport_lite - pipeline gate verifier (task V2-T50)

    Runs the five repository gates in order and emits one structured result set
    that both Maker and Checker paste into their reports, plus the git state
    observed before and after the run (Checker read-only self-evidence).

        powershell -NoProfile -File scripts\verify.ps1
        powershell -NoProfile -File scripts\verify.ps1 -Fast              # skip the frontend production build
        powershell -NoProfile -File scripts\verify.ps1 -Only unit-engine  # run selected gates only
        powershell -NoProfile -File scripts\verify.ps1 -Json report.json  # also write the JSON report to a file

    Exit code is 0 when every executed gate passed, 1 otherwise.
    pwsh 7 works too where it is installed; this host only ships Windows
    PowerShell 5.1, so the documented form uses `powershell`.

    This file is intentionally ASCII-only: Windows PowerShell 5.1 misreads
    BOM-less UTF-8 script files, and this script must run on both hosts.
#>
[CmdletBinding()]
param(
    [switch]$Fast,
    [string[]]$Only,
    [string]$Json,
    [switch]$KeepGoing,
    [int]$TailLines = 40
)

$ErrorActionPreference = 'Continue'
Set-StrictMode -Version 2.0
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    Set-Variable -Name PSNativeCommandUseErrorActionPreference -Value $false
}

$repoRoot = Split-Path -Parent $PSScriptRoot

function Get-GitState {
    param([string]$Root)
    $head = ''
    $status = ''
    try { $head = ((& git -C $Root rev-parse HEAD 2>&1) | Out-String).Trim() } catch { $head = 'ERROR ' + $_.Exception.Message }
    try { $status = ((& git -C $Root status --short 2>&1) | Out-String).Trim() } catch { $status = 'ERROR ' + $_.Exception.Message }
    return [pscustomobject]@{ head = $head; statusShort = $status }
}

# Gate table. 'cmd' is the command line reported to the reader; 'exe'/'argv' are
# what actually runs, so no command string is ever re-parsed as code.
$gateTable = @(
    [pscustomobject]@{
        id = 'unit-desktop'; label = 'Frontend unit tests (Vitest)'; dir = 'desktop'
        cmd = 'npx vitest run'; exe = 'npx'; argv = @('vitest', 'run')
        skipInFast = $false; pattern = 'Tests\s+.*'; passSummary = 'all tests passed'
    },
    [pscustomobject]@{
        id = 'typecheck'; label = 'Vue type check (vue-tsc)'; dir = 'desktop'
        cmd = 'npx vue-tsc --noEmit'; exe = 'npx'; argv = @('vue-tsc', '--noEmit')
        skipInFast = $false; pattern = 'error TS\d+.*'; passSummary = 'no type errors'
    },
    [pscustomobject]@{
        id = 'build'; label = 'Frontend production build (Vite)'; dir = 'desktop'
        cmd = 'npx vite build'; exe = 'npx'; argv = @('vite', 'build')
        skipInFast = $true; pattern = 'built in.*'; passSummary = 'build ok'
    },
    [pscustomobject]@{
        id = 'unit-engine'; label = 'Backend unit tests (Pytest)'; dir = '.'
        cmd = 'python -m pytest engine/tests -q'; exe = 'python'; argv = @('-m', 'pytest', 'engine/tests', '-q')
        skipInFast = $false; pattern = '\d+ (passed|failed).*'; passSummary = 'all tests passed'
    },
    [pscustomobject]@{
        id = 'rust-check'; label = 'Rust shell check (cargo check)'; dir = 'desktop/src-tauri'
        cmd = 'cargo check'; exe = 'cargo'; argv = @('check')
        skipInFast = $false; pattern = 'Finished.*'; passSummary = 'check ok'
    }
)

function Get-Summary {
    param([string]$Text, [string]$Pattern, [string]$Fallback)
    if ([string]::IsNullOrWhiteSpace($Text)) { if ($Fallback) { return $Fallback } else { return '(no output)' } }
    if ($Pattern) {
        $m = [regex]::Matches($Text, $Pattern)
        if ($m.Count -gt 0) {
            $value = $m[$m.Count - 1].Value.Trim()
            if ($value.Length -gt 200) { $value = $value.Substring(0, 200) }
            return $value
        }
    }
    if ($Fallback) { return $Fallback }
    $lines = @($Text -split "\r?\n" | Where-Object { $_.Trim() -ne '' })
    if ($lines.Count -eq 0) { return '(no output)' }
    $last = $lines[$lines.Count - 1].Trim()
    if ($last.Length -gt 200) { $last = $last.Substring(0, 200) }
    return $last
}

function Invoke-Gate {
    param([pscustomobject]$Gate)
    $workDir = Join-Path $repoRoot $Gate.dir
    $result = [ordered]@{
        gate = $Gate.id; label = $Gate.label; command = $Gate.cmd; workdir = $Gate.dir
        status = 'PASS'; exitCode = 0; seconds = 0; summary = ''; output = ''
    }
    if (-not (Test-Path -LiteralPath $workDir)) {
        $result.status = 'SKIP'
        $result.summary = 'workdir not found: ' + $workDir
        return [pscustomobject]$result
    }
    $text = ''
    $code = 1
    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    Push-Location -LiteralPath $workDir
    try {
        $text = (& $Gate.exe @($Gate.argv) 2>&1 | Out-String)
        if ($null -eq $LASTEXITCODE) { $code = 0 } else { $code = $LASTEXITCODE }
    } catch {
        $text = ($_ | Out-String)
        $code = 1
    } finally {
        $watch.Stop()
        Pop-Location
    }
    $result.exitCode = $code
    $result.seconds = [math]::Round($watch.Elapsed.TotalSeconds, 1)
    $result.summary = Get-Summary -Text $text -Pattern $Gate.pattern -Fallback $Gate.passSummary
    if ($code -ne 0) { $result.status = 'FAIL' }
    $result.output = $text
    return [pscustomobject]$result
}

$startedAt = (Get-Date).ToString('s')
$gitBefore = Get-GitState -Root $repoRoot
$mode = 'full'
if ($Fast) { $mode = 'fast' }

$selected = @($gateTable | Where-Object { -not ($Only -and ($Only -notcontains $_.id)) -and -not ($Fast -and $_.skipInFast) })

Write-Host ''
Write-Host ('FairyReport pipeline gates  |  mode: ' + $mode + '  |  repo: ' + $repoRoot)
Write-Host ('HEAD before: ' + $gitBefore.head)
Write-Host ''

$results = @()
$allPassed = $true
foreach ($gate in $selected) {
    Write-Host ('-> ' + $gate.id + ' : ' + $gate.cmd + '  (workdir: ' + $gate.dir + ')')
    $r = Invoke-Gate -Gate $gate
    $results += $r
    Write-Host ('   ' + $r.status + '  ' + $r.seconds + 's  ' + $r.summary)
    if ($r.status -ne 'PASS') {
        $allPassed = $false
        if (-not $KeepGoing) {
            Write-Host ''
            Write-Host ('--- last ' + $TailLines + ' lines of ' + $r.gate + ' output ---')
            $tail = @($r.output -split "\r?\n")
            $from = [math]::Max(0, $tail.Count - $TailLines)
            for ($i = $from; $i -lt $tail.Count; $i++) { Write-Host ('   ' + $tail[$i]) }
            Write-Host ''
            break
        }
    }
}

$gitAfter = Get-GitState -Root $repoRoot
$worktreeStable = (($gitBefore.head -eq $gitAfter.head) -and ($gitBefore.statusShort -eq $gitAfter.statusShort))

$report = [ordered]@{
    task = 'V2-T50'
    script = 'scripts/verify.ps1'
    mode = $mode
    selected = @($selected | ForEach-Object { $_.id })
    startedAt = $startedAt
    finishedAt = (Get-Date).ToString('s')
    git = [ordered]@{
        headBefore = $gitBefore.head
        headAfter = $gitAfter.head
        statusBefore = $gitBefore.statusShort
        statusAfter = $gitAfter.statusShort
        worktreeStable = $worktreeStable
    }
    passed = $allPassed
    gates = @($results | ForEach-Object {
        [ordered]@{
            gate = $_.gate; label = $_.label; command = $_.command; workdir = $_.workdir
            status = $_.status; exitCode = $_.exitCode; seconds = $_.seconds; summary = $_.summary
        }
    })
}

Write-Host ''
Write-Host ('{0,-14} {1,-6} {2,8}  {3}' -f 'GATE', 'STATUS', 'SECONDS', 'SUMMARY')
foreach ($g in $report.gates) {
    Write-Host ('{0,-14} {1,-6} {2,8}  {3}' -f $g.gate, $g.status, $g.seconds, $g.summary)
}
Write-Host ''
Write-Host ('worktreeStable: ' + $worktreeStable + '  (HEAD ' + $gitAfter.head + ')')
Write-Host ('RESULT: ' + $(if ($allPassed) { 'PASS' } else { 'FAIL' }))
Write-Host ''

$jsonText = ($report | ConvertTo-Json -Depth 6)
if ($Json) {
    $jsonPath = $Json
    if (-not [System.IO.Path]::IsPathRooted($jsonPath)) { $jsonPath = Join-Path $repoRoot $jsonPath }
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($jsonPath, $jsonText, $utf8NoBom)
    Write-Host ('JSON report written to: ' + $jsonPath)
    Write-Host ''
}
Write-Output $jsonText

if ($allPassed) { exit 0 } else { exit 1 }
