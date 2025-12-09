<#
.SYNOPSIS
    Find all functions missing Args/Returns/Raises sections per DOCUMENTATION_STATUS.md

.DESCRIPTION
    Scans Python source files for function docstrings and checks if they follow
    Google-style format with proper Args/Returns/Raises sections. Reports functions
    with incomplete documentation.

.PARAMETER Path
    Path to scan for Python files (default: src/crazycar)

.PARAMETER Fix
    Not yet implemented - reserved for future auto-fix functionality

.EXAMPLE
    .\check_docstring_completeness.ps1
    .\check_docstring_completeness.ps1 -Path src
#>
param(
    [string]$Path = "src/crazycar",
    [switch]$Fix
)

$issues = @()
$files = Get-ChildItem -Path $Path -Filter "*.py" -Recurse -File

foreach ($file in $files) {
    $content = Get-Content $file.FullName -Raw
    $lines = Get-Content $file.FullName
    
    # Find all function definitions with their docstrings
    $pattern = '(?ms)^(def (\w+)\([^)]*\):)\s*\n\s*"""(.*?)"""'
    $matches = [regex]::Matches($content, $pattern)
    
    foreach ($match in $matches) {
        $funcName = $match.Groups[2].Value
        $funcDef = $match.Groups[1].Value
        $docstring = $match.Groups[3].Value
        $lineNum = ($content.Substring(0, $match.Index) -split "`n").Count
        
        # Skip private functions (starting with _) unless they're magic methods
        if ($funcName -match '^_[^_]') {
            continue
        }
        
        # Check if function has parameters (excluding self, cls)
        $hasParams = $funcDef -match '\((?!self\s*\)|cls\s*\))[^)]*\w'
        
        # Check docstring completeness
        $hasArgs = $docstring -match '(?m)^\s*Args:'
        $hasReturns = $docstring -match '(?m)^\s*Returns:'
        $hasRaises = $docstring -match '(?m)^\s*Raises:'
        
        # Check for old-style sections
        $hasSideEffects = $docstring -match '(?m)^\s*Side Effects:'
        $hasWorkflow = $docstring -match '(?m)^\s*Workflow:'
        $hasConfiguration = $docstring -match '(?m)^\s*Configuration:'
        
        # Build issue list
        $problems = @()
        
        if ($hasParams -and -not $hasArgs) {
            $problems += "Missing Args:"
        }
        
        # Check if function returns something (not just None or pass)
        $funcBody = $content.Substring($match.Index + $match.Length, 
            [Math]::Min(500, $content.Length - $match.Index - $match.Length))
        $hasReturn = $funcBody -match '\n\s+return\s+(?!None\s*$)'
        
        if ($hasReturn -and -not $hasReturns) {
            $problems += "Missing Returns:"
        }
        
        if ($hasSideEffects) {
            $problems += 'Replace "Side Effects:" with "Note:"'
        }
        if ($hasWorkflow) {
            $problems += 'Replace "Workflow:" with description or "Note:"'
        }
        if ($hasConfiguration) {
            $problems += 'Move "Configuration:" to "Args:" or "Note:"'
        }
        
        # Check if docstring is too short (< 50 chars suggests incomplete)
        if ($docstring.Trim().Length -lt 50 -and $hasParams) {
            $problems += "Docstring too short ($(($docstring.Trim().Length)) chars)"
        }
        
        if ($problems.Count -gt 0) {
            $issues += [PSCustomObject]@{
                File = $file.FullName.Replace("$PWD\", "")
                Line = $lineNum
                Function = $funcName
                Issues = $problems -join "; "
            }
        }
    }
}

if ($issues.Count -eq 0) {
    Write-Host "✅ All functions have complete Google-style docstrings!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "❌ Found $($issues.Count) function(s) with incomplete docstrings:" -ForegroundColor Red
    Write-Host ""
    $issues | Format-Table -AutoSize -Wrap
    
    # Group by file for easier fixing
    Write-Host ""
    Write-Host "Summary by file:" -ForegroundColor Cyan
    $issues | Group-Object File | ForEach-Object {
        $fileName = $_.Name
        $count = $_.Count
        Write-Host "  $fileName : $count functions" -ForegroundColor Yellow
    }
    
    exit 1
}
