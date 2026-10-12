param(
    [int]$MaxAttempts = 60,
    [int]$DelaySeconds = 180
)

# Restart the resumable WS-27 confirmation controller after transient SSH or
# host errors. The controller reuses built sources, skips verified cells and
# refuses to overwrite any existing experiment ID or raw result.
$repo = "E:\研\毕业论文\workspace\ws27-guardhash-compare"
$log = Join-Path $repo "results\ws27-confirm-supervisor.log"
$out = Join-Path $repo "results\ws27-confirm.log"
$err = Join-Path $repo "results\ws27-confirm.err.log"

Set-Location $repo

for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
    "[$(Get-Date -Format o)] attempt $attempt start" | Add-Content -Path $log
    python scripts\run_ws27_matrix.py confirm run 1>> $out 2>> $err
    $code = $LASTEXITCODE
    "[$(Get-Date -Format o)] attempt $attempt exit=$code" | Add-Content -Path $log
    if ($code -eq 0) {
        "[$(Get-Date -Format o)] completed" | Add-Content -Path $log
        break
    }
    Start-Sleep -Seconds $DelaySeconds
}
