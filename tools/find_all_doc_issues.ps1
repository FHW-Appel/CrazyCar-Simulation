<#
.SYNOPSIS
    Comprehensive documentation checker per DOCUMENTATION_STATUS.md standards.

.DESCRIPTION
    Scans all Python files for documentation issues including:
    - Short/incomplete docstrings
    - Magic numbers without comments
    - German text in comments
    - Duplicate comments
    
    Generates a detailed report grouped by issue type and saves to CSV.

.EXAMPLE
    .\find_all_doc_issues.ps1

.OUTPUTS
    doc_issues.csv - Full report of all documentation issues found
#>

$allIssues = @()

Get-ChildItem "src\crazycar" -Filter "*.py" -Recurse -File | ForEach-Object {
    $file = $_.FullName
    $relPath = $file.Replace("$PWD\", "")
    $content = Get-Content $file -Raw
    $lines = Get-Content $file
    
    # === 1. CHECK: Short/incomplete docstrings ===
    $funcPattern = '(?ms)^(def (\w+)\([^)]*\):)\s*\n\s*"""([^"]*)"""'
    [regex]::Matches($content, $funcPattern) | ForEach-Object {
        $funcName = $_.Groups[2].Value
        $docstring = $_.Groups[3].Value
        $lineNum = ($content.Substring(0, $_.Index) -split "`n").Count
        
        # Skip private functions
        if ($funcName -match '^_[^_]') { return }
        
        $hasArgs = $docstring -match '(?m)^\s*Args:'
        $hasReturns = $docstring -match '(?m)^\s*Returns:'
        
        if ((-not $hasArgs -and $_.Groups[1].Value -match '\w+\s*:') -or 
            (-not $hasReturns -and $docstring.Length -lt 100)) {
            $allIssues += [PSCustomObject]@{
                File = $relPath
                Line = $lineNum
                Type = "SHORT_DOCSTRING"
                Function = $funcName
                Detail = "Missing Args/Returns or too short"
            }
        }
    }
    
    # === 2. CHECK: Magic numbers (numbers without comments) ===
    $magicPattern = '(?m)^\s+.*?=.*?\b(\d+\.?\d+)\b(?!\s*#).*$'
    [regex]::Matches($content, $magicPattern) | ForEach-Object {
        $number = $_.Groups[1].Value
        $lineNum = ($content.Substring(0, $_.Index) -split "`n").Count
        $lineContent = $lines[$lineNum - 1]
        
        # Skip if in constants.py or already has comment or is 0/1/simple
        if ($relPath -match 'constants\.py' -or 
            $number -in @('0', '1', '0.0', '1.0') -or
            $lineContent -match '#') { return }
        
        $allIssues += [PSCustomObject]@{
            File = $relPath
            Line = $lineNum
            Type = "MAGIC_NUMBER"
            Function = ""
            Detail = "Number $number needs comment with unit/meaning"
        }
    }
    
    # === 3. CHECK: German text (excluding legacy function names) ===
    # Match only actual German words with umlauts, not Unicode artifacts
    # Use common German word patterns to reduce false positives
    $germanPattern = '\b\w*(für|über|während|könnte|müssen|größer|schön|ähnlich)[a-zäöüß]*\b|' +
                     '\b[a-zäöüß]*(änderung|geschwindigkeit|größe|überprüfung)\b'
    if ($content -match $germanPattern) {
        $lines | Select-String -Pattern $germanPattern | ForEach-Object {
            $lineContent = $_.Line
            # Skip if it's a known legacy name
            if ($lineContent -notmatch 'Lenkeinschlagsänderung|Geschwindigkeit|servo2IstWinkel') {
                $allIssues += [PSCustomObject]@{
                    File = $relPath
                    Line = $_.LineNumber
                    Type = "GERMAN_TEXT"
                    Function = ""
                    Detail = $lineContent.Trim().Substring(0, [Math]::Min(60, $lineContent.Trim().Length))
                }
            }
        }
    }
    
    # === 4. CHECK: Duplicate comments ===
    $commentPattern = '(?m)^\s*#\s*(.+)$'
    $seenComments = @{}
    [regex]::Matches($content, $commentPattern) | ForEach-Object {
        $comment = $_.Groups[1].Value.Trim()
        $lineNum = ($content.Substring(0, $_.Index) -split "`n").Count
        
        if ($seenComments.ContainsKey($comment)) {
            $allIssues += [PSCustomObject]@{
                File = $relPath
                Line = $lineNum
                Type = "DUPLICATE_COMMENT"
                Function = ""
                Detail = "Duplicate: $comment"
            }
        } else {
            $seenComments[$comment] = $lineNum
        }
    }
}

# Output results
if ($allIssues.Count -eq 0) {
    Write-Host "ALL CHECKS PASSED!" -ForegroundColor Green
    exit 0
}

Write-Host "Found $($allIssues.Count) documentation issues:" -ForegroundColor Red
Write-Host ""

# Group by type
$allIssues | Group-Object Type | ForEach-Object {
    Write-Host "=== $($_.Name) ($($_.Count) issues) ===" -ForegroundColor Cyan
    $_.Group | Format-Table File, Line, Function, Detail -AutoSize | Out-String | Write-Host
}

# Save to file for processing
$allIssues | Export-Csv "doc_issues.csv" -NoTypeInformation -Encoding UTF8
Write-Host "Full report saved to: doc_issues.csv" -ForegroundColor Yellow
