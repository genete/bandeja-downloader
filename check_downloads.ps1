# Compara pending.csv con los ZIPs descargados en Downloads
# Uso: .\check_downloads.ps1

$csv     = Get-Content "D:\BANDEJADL\data\pending.csv" | Where-Object { $_.Trim() -ne "" }
$dlDir   = "C:\Users\LGC005\Downloads"

$ok = 0; $dup = 0; $missing = 0

foreach ($code in $csv) {
    $pattern = $code.Trim() -replace "/", "_"
    $files   = @(Get-ChildItem -Path $dlDir -Filter "documentos_${pattern}*.zip" -ErrorAction SilentlyContinue)
    $count   = $files.Count

    $label = switch ($count) {
        0       { "FALTA  "; $missing++ }
        1       { "ok     "; $ok++ }
        default { "DUP($count) "; $dup++ }
    }

    Write-Host "$label $code"
}

Write-Host ""
Write-Host "--- ok: $ok  |  duplicados: $dup  |  faltan: $missing  |  total: $($ok + $dup + $missing) ---"
