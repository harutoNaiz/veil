# Verify sub-phase 7.1.3 "App side: Kotlin port and the Also hide? Console flow".
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$script:failed = $false

function Check([string]$name, [scriptblock]$body) {
  $out = @(& $body 2>&1 | ForEach-Object { "$_" })
  $ok = ($LASTEXITCODE -eq 0)
  if (-not $ok) { $out | Select-Object -Last 25 | ForEach-Object { Write-Host "    $_" } }
  Write-Host ('{0}  {1}' -f $(if ($ok) { 'ok  ' } else { 'FAIL' }), $name)
  if (-not $ok) { $script:failed = $true }
}

function Gradle([string]$a) {
  $log = Join-Path $env:TEMP ("veil-7.1.3-gradle-{0}.txt" -f (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
  cmd /c "powershell -NoProfile -ExecutionPolicy Bypass -File `"$PSScriptRoot\..\gradle-locked.ps1`" $a > `"$log`" 2>&1"
  $code = $LASTEXITCODE
  Get-Content $log | Select-Object -Last 12
  cmd /c "exit $code"
}

$kt = @(
  'guard/brain/src/main/kotlin/com/veil/brain/contract/Types.kt',
  'guard/brain/src/main/kotlin/com/veil/brain/judge/Judge.kt',
  'guard/teacher/src/main/kotlin/com/veil/teacher/autocal/BankFile.kt',
  'guard/teacher/src/main/kotlin/com/veil/teacher/autocal/VocabFile.kt',
  'guard/teacher/src/main/kotlin/com/veil/teacher/autocal/AutoCal.kt',
  'guard/teacher/src/test/kotlin/com/veil/teacher/AutoCalParityTest.kt',
  'guard/app/src/main/java/com/veil/guard/wire/ml/ConceptPack.kt',
  'guard/app/src/test/java/com/veil/guard/wire/ml/ConceptPackTest.kt',
  'guard/app/src/main/java/com/veil/guard/teacher/TeacherDebugActivity.kt'
)

Check '(0) ktlint' { & "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" --relative @kt }
Check '(1) gradle brain+teacher+app tests' { Gradle ':brain:test :teacher:test :app:testDebugUnitTest --tests *ConceptPackTest*' }
Check '(2) dart format' { Push-Location console; dart format --set-exit-if-changed lib/guard lib/screens/concept_studio_screen.dart test/screens/also_hide_test.dart; $c = $LASTEXITCODE; Pop-Location; cmd /c "exit $c" }
Check '(3) flutter test' { Push-Location console; flutter test; $c = $LASTEXITCODE; Pop-Location; cmd /c "exit $c" }

if ($script:failed) { Write-Host 'VERIFY 7.1.3: FAIL'; exit 1 }
Write-Host 'VERIFY 7.1.3: PASS'
