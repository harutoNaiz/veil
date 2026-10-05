# Live progress bar with ETA for an orchestrator verify run.
# Usage (in a separate PowerShell window):
#   powershell -NoProfile -ExecutionPolicy Bypass -File "D:\iqoo finale\progress\watch.ps1"
# Optional: -Evidence <verify evidence file>  -Weights <relative cost per check, comma-separated>
param(
  [string] $Evidence = 'D:\iqoo finale\progress\ch1-see\phase-1.3-see-prototype\evidence\1.3.3-verify.txt',
  [string] $Weights  = '1,1,2,30,1,40,1,8',   # 1.3.3: (4) full run and (6) no-cache rerun dominate
  [int]    $Every    = 3
)
$w = $Weights.Split(',') | ForEach-Object { [double]$_ }
$total = ($w | Measure-Object -Sum).Sum
while ($true) {
  if (-not (Test-Path $Evidence)) { Write-Host "waiting for $Evidence ..."; Start-Sleep $Every; continue }
  $lines = Get-Content $Evidence -Encoding UTF8
  $startLine = $lines | Where-Object { $_ -match '^=== .* verify · (\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)' } | Select-Object -First 1
  $start = if ($startLine -match '(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)') { [datetime]$Matches[1] } else { (Get-Item $Evidence).CreationTime }
  $done  = @($lines | Where-Object { $_ -match '^(ok|FAIL|skip)\s+\((\d+)\)' }).Count
  $fail  = @($lines | Where-Object { $_ -match '^FAIL' }).Count
  $final = $lines | Where-Object { $_ -match '^VERIFY .*: (PASS|FAIL)' } | Select-Object -Last 1
  $doneW = ($w | Select-Object -First $done | Measure-Object -Sum).Sum
  $pct   = if ($final) { 100 } else { [math]::Min(99, [math]::Round(100 * $doneW / $total)) }
  $elapsed = (Get-Date) - $start
  $eta = if ($final) { 'done' } elseif ($doneW -gt 0) {
           $rem = [timespan]::FromSeconds($elapsed.TotalSeconds / $doneW * ($total - $doneW)); '{0:mm\:ss} left (~{1:HH:mm})' -f $rem, ((Get-Date) + $rem)
         } else { 'estimating...' }
  $n = 40; $fill = [int]($n * $pct / 100)
  $bar = ('#' * $fill) + ('-' * ($n - $fill))
  $step = if ($final) { $final } else { "check $($done + 1) of $($w.Count) running" }
  Write-Host -NoNewline ("`r[{0}] {1,3}%  {2}  elapsed {3:mm\:ss}  ETA {4}  fails:{5}      " -f $bar, $pct, $step, $elapsed, $eta, $fail)
  if ($final) { Write-Host ""; break }
  Start-Sleep $Every
}
