<#
.SYNOPSIS
    Run the complete Seller Trust Analytics validation sequence.

.DESCRIPTION
    Runs the test suite, the end-to-end ETL pipeline, and the data invariant
    checks. The script stops at the first failed command and returns its exit
    code to the caller.

.EXAMPLE
    .\scripts\validate_all.ps1

.EXAMPLE
    .\scripts\validate_all.ps1 -RawDir data\raw -OutputDir data\processed
#>

[CmdletBinding()]
param(
    [string]$RawDir = "data/raw",
    [string]$OutputDir = "data/processed",
    [string]$DbPath = "data/trust_analytics.db"
)

$ErrorActionPreference = "Stop"

function Invoke-ValidationStep {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Host "== $Name =="
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

try {
    Invoke-ValidationStep "Tests" { python -m pytest tests/ -q }
    Invoke-ValidationStep "ETL pipeline" {
        python scripts/etl_pipeline.py --raw-dir $RawDir --output-dir $OutputDir --db-path $DbPath
    }
    Invoke-ValidationStep "Data validation" {
        python scripts/validate_pipeline.py --raw-dir $RawDir --output-dir $OutputDir
    }
    Write-Host "VALIDATION ALL PASSED"
    exit 0
}
catch {
    Write-Error $_
    exit 1
}
