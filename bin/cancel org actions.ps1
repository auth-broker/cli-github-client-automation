# gh auth login first (token must see private repos if you want to cancel them)
$Org = "auth-broker"

$repos = ""
try {
  $repos = gh repo list $Org --limit 200 --json name --jq '.[].name' 2>$null
} catch { }

foreach ($r in ($repos -split "`n")) {
  if (-not $r) { continue }
  Write-Host "Cancelling in $r..."

  foreach ($Status in @("in_progress","queued")) {
    $runIds = gh api "repos/$Org/$r/actions/runs" -f status=$Status --jq '.workflow_runs[].id' 2>$null

    if (-not $runIds) { continue }

    foreach ($id in ($runIds -split "`n")) {
      if ($id -match '^\d+$') {
        gh api --method POST "repos/$Org/$r/actions/runs/$id/cancel"
      }
    }
  }
}
