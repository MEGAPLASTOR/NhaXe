# Tim camera IP (Imou / Dahua) trong mang noi bo.
# Chay bang file tim_camera.bat o thu muc goc.

$ErrorActionPreference = "SilentlyContinue"
$OutputEncoding = [Text.Encoding]::UTF8

function Test-Port([string]$dich, [int]$cong, [int]$cho = 700) {
    $tcp = New-Object Net.Sockets.TcpClient
    try {
        $kq = $tcp.BeginConnect($dich, $cong, $null, $null)
        if ($kq.AsyncWaitHandle.WaitOne($cho, $false) -and $tcp.Connected) { return $true }
        return $false
    } catch { return $false } finally { $tcp.Close() }
}

Write-Host ""
Write-Host "==================================================="
Write-Host "        TIM CAMERA TRONG MANG - VIDATEX"
Write-Host "==================================================="

$cfg = Get-NetIPConfiguration | Where-Object { $_.NetAdapter.Status -eq "Up" -and $_.IPv4Address } | Select-Object -First 1
if (-not $cfg) {
    Write-Host ""
    Write-Host "Khong tim thay ket noi mang. Hay cam day mang hoac bat Wi-Fi roi chay lai."
    Read-Host "Nhan Enter de dong"
    exit 1
}
$ipMay = $cfg.IPv4Address.IPAddress
$dai = ($ipMay -split "\.")[0..2] -join "."

Write-Host ""
Write-Host "May nay   : $ipMay   ($($cfg.InterfaceAlias))"
Write-Host "Router    : $($cfg.IPv4DefaultGateway.NextHop)"
Write-Host "Dang quet : $dai.1  ->  $dai.254"
Write-Host ""
Write-Host "Vui long doi khoang 1 phut..."

# ---- Buoc 1: ping ca dai mang cung luc ----
$ping = 1..254 | ForEach-Object { (New-Object Net.NetworkInformation.Ping).SendPingAsync("$dai.$_", 900) }
[Threading.Tasks.Task]::WaitAll($ping)
$song = @()
foreach ($p in $ping) {
    if ($p.Result -and $p.Result.Status -eq "Success") { $song += $p.Result.Address.ToString() }
}
Write-Host "Co $($song.Count) thiet bi dang bat."
Write-Host ""

# ---- Buoc 2: thiet bi nao mo cong 554 (RTSP) thi gan nhu chac chan la camera ----
$oui = @{
    "3CEF8C" = "Dahua/Imou"; "4C11BF" = "Dahua/Imou"; "9C1463" = "Dahua/Imou"
    "14A78B" = "Dahua/Imou"; "38AF29" = "Dahua/Imou"; "E0508B" = "Dahua/Imou"
    "08EDED" = "Dahua/Imou"; "24526A" = "Dahua/Imou"; "6C1C71" = "Dahua/Imou"
    "BC325F" = "Dahua/Imou"; "44D244" = "Dahua/Imou"; "F4B1C2" = "Dahua/Imou"
    "C0393D" = "Dahua/Imou"; "A0BDCD" = "Dahua/Imou"; "90021B" = "Dahua/Imou"
}
$camera = @()
foreach ($ip in $song) {
    if (-not (Test-Port $ip 554)) { continue }
    $mac = (Get-NetNeighbor -IPAddress $ip -ErrorAction SilentlyContinue | Select-Object -First 1).LinkLayerAddress
    $hang = "khong ro"
    if ($mac) {
        $ma = ($mac -replace "[-:]", "").Substring(0, 6).ToUpper()
        if ($oui.ContainsKey($ma)) { $hang = $oui[$ma] }
    }
    $camera += [pscustomobject]@{ IP = $ip; MAC = $mac; Hang = $hang; Web = (Test-Port $ip 80 400) }
}

Write-Host "==================================================="
if ($camera.Count -eq 0) {
    Write-Host "KHONG TIM THAY CAMERA NAO (khong co thiet bi mo cong 554)."
    Write-Host ""
    Write-Host "Kiem tra lai:"
    Write-Host "  - Camera da cam dien va den bao da sang chua"
    Write-Host "  - Camera va may tinh co cung mot mang Wi-Fi / day mang khong"
    Write-Host "  - Trong app Imou Life: ... -> Cai dat -> bat RTSP"
} else {
    Write-Host "TIM THAY $($camera.Count) CAMERA:"
    Write-Host ""
    foreach ($c in $camera) {
        Write-Host "   IP      : $($c.IP)"
        Write-Host "   MAC     : $($c.MAC)   ($($c.Hang))"
        Write-Host "   Trang web: $(if ($c.Web) { "http://$($c.IP)" } else { "khong mo" })"
        Write-Host "   ---"
    }
    Write-Host "Chep cac dia chi IP nay vao phan mem:"
    Write-Host "   Cai dat -> Camera -> o 'Dia chi IP'"
    Write-Host "   O 'Mat khau' nhap Safety Code in tren tem day camera."
}
Write-Host "==================================================="
Write-Host ""
Read-Host "Nhan Enter de dong"
