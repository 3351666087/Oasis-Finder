param(
    [string]$BaseDir = "C:\Program Files\MySQL\MySQL Server 8.4",
    [string]$ServiceName = "MeshSupplyChainMySQL",
    [int]$Port = 3307,
    [string]$DatabaseName = "mesh_supply_chain",
    [string]$AppUser = "mesh_user",
    [string]$AppPassword = "MeshUser#2026",
    [string]$RootPassword = "MeshRoot#2026",
    [string]$ProjectRoot = ""
)

$ErrorActionPreference = "Stop"

function Wait-ForPort {
    param(
        [string]$HostName,
        [int]$PortNumber,
        [int]$TimeoutSeconds = 60
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $client = [System.Net.Sockets.TcpClient]::new()
            $async = $client.BeginConnect($HostName, $PortNumber, $null, $null)
            if ($async.AsyncWaitHandle.WaitOne(1000, $false) -and $client.Connected) {
                $client.EndConnect($async) | Out-Null
                $client.Close()
                return
            }
            $client.Close()
        } catch {
        }
        Start-Sleep -Milliseconds 800
    }

    throw "MySQL did not open port $PortNumber within $TimeoutSeconds seconds."
}

function Convert-ToMySqlPath {
    param([string]$RawPath)
    return ($RawPath -replace "\\", "/")
}

if ($ProjectRoot) {
    $projectRoot = Resolve-Path $ProjectRoot
} else {
    $projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
}
$runtimeRoot = Join-Path $projectRoot ".runtime\mysql"
$dataDir = Join-Path $runtimeRoot "data"
$tmpDir = Join-Path $runtimeRoot "tmp"
$logDir = Join-Path $runtimeRoot "logs"
$configPath = Join-Path $runtimeRoot "my.ini"
$logFile = Join-Path $logDir "mysql-error.log"
$bootstrapSqlPath = Join-Path $runtimeRoot "bootstrap-init.sql"

$baseDirForIni = Convert-ToMySqlPath $BaseDir
$dataDirForIni = Convert-ToMySqlPath $dataDir
$tmpDirForIni = Convert-ToMySqlPath $tmpDir
$logFileForIni = Convert-ToMySqlPath $logFile
$configPathForIni = Convert-ToMySqlPath $configPath
$bootstrapSqlPathForIni = Convert-ToMySqlPath $bootstrapSqlPath

New-Item -ItemType Directory -Force -Path $runtimeRoot, $dataDir, $tmpDir, $logDir | Out-Null

$mysqld = Join-Path $BaseDir "bin\mysqld.exe"
$mysql = Join-Path $BaseDir "bin\mysql.exe"

if (!(Test-Path $mysqld)) {
    throw "mysqld.exe was not found at $mysqld"
}

@"
[mysqld]
basedir=$baseDirForIni
datadir=$dataDirForIni
port=$Port
mysqlx_port=33070
tmpdir=$tmpDirForIni
log-error=$logFileForIni
character-set-server=utf8mb4
collation-server=utf8mb4_0900_ai_ci
default-time-zone='+08:00'
sql-mode=STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION
max_connections=300
innodb_buffer_pool_size=256M
skip-name-resolve=0
"@ | Set-Content -Path $configPath -Encoding ASCII

@"
CREATE DATABASE IF NOT EXISTS ${DatabaseName} CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER IF NOT EXISTS '$AppUser'@'%' IDENTIFIED WITH mysql_native_password BY '$AppPassword';
CREATE USER IF NOT EXISTS '$AppUser'@'localhost' IDENTIFIED WITH mysql_native_password BY '$AppPassword';
ALTER USER '$AppUser'@'%' IDENTIFIED WITH mysql_native_password BY '$AppPassword';
ALTER USER '$AppUser'@'localhost' IDENTIFIED WITH mysql_native_password BY '$AppPassword';
GRANT ALL PRIVILEGES ON ${DatabaseName}.* TO '$AppUser'@'%';
GRANT ALL PRIVILEGES ON ${DatabaseName}.* TO '$AppUser'@'localhost';
FLUSH PRIVILEGES;
"@ | Set-Content -Path $bootstrapSqlPath -Encoding ASCII

if (!(Test-Path (Join-Path $dataDir "mysql"))) {
    & $mysqld --defaults-file=$configPath --initialize-insecure
}

$existingProcesses = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq "mysqld.exe" -and $_.CommandLine -like "*my.ini*"
}
foreach ($proc in $existingProcesses) {
    Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2

Start-Process -FilePath $mysqld -ArgumentList "--defaults-file=$configPathForIni", "--init-file=$bootstrapSqlPathForIni" -WindowStyle Hidden | Out-Null

Wait-ForPort -HostName "127.0.0.1" -PortNumber $Port -TimeoutSeconds 90
& $mysql --protocol=tcp -h 127.0.0.1 -P $Port -u $AppUser "-p$AppPassword" $DatabaseName -e "SELECT CURRENT_USER(), DATABASE();" | Out-Null

$envContent = @"
MESH_DB_HOST=127.0.0.1
MESH_DB_PORT=$Port
MESH_DB_NAME=$DatabaseName
MESH_DB_USER=$AppUser
MESH_DB_PASSWORD=$AppPassword
MESH_DB_ADMIN_USER=root
MESH_DB_ADMIN_PASSWORD=$RootPassword
MESH_TIMEZONE=Asia/Shanghai
"@

$envPath = Join-Path $projectRoot ".env"
$envContent | Set-Content -Path $envPath -Encoding ASCII

Write-Host "MySQL runtime prepared at $runtimeRoot"
Write-Host "Connection: mysql://$AppUser@127.0.0.1:$Port/$DatabaseName"
