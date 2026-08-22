# Conectar-PowerBI.ps1
# Conecta directamente al motor local de Analysis Services que usa tu
# Power BI Desktop abierto, usando la libreria AMO/TOM (Tabular Object Model)
# en vez de la ruta que falla con "Acceso denegado" (enumeracion via WMI).
#
# Uso:
#   1. Abre PowerShell (no hace falta ser administrador).
#   2. cd a la carpeta donde guardaste este script.
#   3. .\Conectar-PowerBI.ps1
#
# El script:
#   - Encuentra el puerto local de msmdsrv.exe (el motor de tu PBIX abierto).
#   - Localiza la libreria Microsoft.AnalysisServices.Tabular.dll instalada
#     junto con Power BI Desktop.
#   - Se conecta y vuelca la estructura del modelo (tablas, columnas, medidas
#     con su expresion DAX, relaciones) a un archivo JSON.
#
# Ajusta $OutputPath si quieres guardar el volcado en otro lugar.

$ErrorActionPreference = "Stop"

$OutputPath = "D:\Obras\TostadoraCentral\AppTostadoraCentral\reportes\Indicadores\pbi_model_dump.json"

Write-Host "1) Buscando el puerto local de Power BI Desktop (msmdsrv.exe)..." -ForegroundColor Cyan
$proc = Get-Process msmdsrv -ErrorAction SilentlyContinue
if (-not $proc) {
    Write-Error "No se encontro el proceso msmdsrv.exe. Asegurate de tener un archivo .pbix abierto en Power BI Desktop."
    exit 1
}

# Puede haber mas de un msmdsrv.exe (p.ej. un servicio SSAS instalado ademas
# del workspace de Power BI Desktop). Nos quedamos solo con los que cuelgan
# de un proceso PBIDesktop.exe para no conectarnos al motor equivocado.
$pbiPids = (Get-CimInstance Win32_Process -Filter "Name='msmdsrv.exe'" -ErrorAction SilentlyContinue) |
    Where-Object {
        $parent = Get-Process -Id $_.ParentProcessId -ErrorAction SilentlyContinue
        $parent -and $parent.ProcessName -eq 'PBIDesktop'
    } |
    Select-Object -ExpandProperty ProcessId

if (-not $pbiPids -or $pbiPids.Count -eq 0) {
    Write-Warning "No se pudo confirmar que msmdsrv.exe pertenezca a Power BI Desktop; se usaran todas las instancias encontradas."
    $pbiPids = $proc.Id
}

$ports = @()
foreach ($msmdsrvPid in $pbiPids) {
    $conns = Get-NetTCPConnection -OwningProcess $msmdsrvPid -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conns) { $ports += $c.LocalPort }
}
$ports = $ports | Sort-Object -Unique
if ($ports.Count -eq 0) {
    Write-Error "No se pudo determinar el puerto de msmdsrv.exe."
    exit 1
}
if ($ports.Count -gt 1) {
    Write-Warning "Se encontraron varios workspaces de Power BI Desktop abiertos (puertos: $($ports -join ', ')). Se usara el primero; ajusta `$port manualmente si no es el correcto."
}
$port = $ports[0]
Write-Host "   Puerto detectado: $port" -ForegroundColor Green

Write-Host "2) Buscando Microsoft.AnalysisServices.Tabular.dll..." -ForegroundColor Cyan
$dllCandidates = @()
$searchRoots = @(
    "$env:LOCALAPPDATA\Microsoft\WindowsApps",
    "C:\Program Files\Microsoft Power BI Desktop",
    "D:\Program Files\Microsoft Power BI Desktop",
    "C:\Program Files (x86)\Microsoft Power BI Desktop",
    "C:\Windows\Microsoft.NET\assembly\GAC_MSIL\Microsoft.AnalysisServices.Tabular"
)
foreach ($root in $searchRoots) {
    if (Test-Path $root) {
        $found = Get-ChildItem -Path $root -Filter "Microsoft.AnalysisServices.Tabular.dll" -Recurse -ErrorAction SilentlyContinue
        if ($found) { $dllCandidates += $found }
    }
}
# La busqueda recursiva con -Force sobre C:\Program Files\WindowsApps falla con
# "Acceso denegado" (ACLs de paquetes de otros usuarios). Si no se encontro nada
# arriba, se intenta localizar el paquete de Power BI Desktop especificamente.
if ($dllCandidates.Count -eq 0 -and (Test-Path "C:\Program Files\WindowsApps")) {
    $pbiPkg = Get-ChildItem "C:\Program Files\WindowsApps" -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "Microsoft.MicrosoftPowerBIDesktop_*" } |
        Select-Object -First 1
    if ($pbiPkg) {
        $found = Get-ChildItem -Path $pbiPkg.FullName -Filter "Microsoft.AnalysisServices.Tabular.dll" -Recurse -ErrorAction SilentlyContinue
        if ($found) { $dllCandidates += $found }
    }
}
if ($dllCandidates.Count -eq 0) {
    Write-Error "No se encontro Microsoft.AnalysisServices.Tabular.dll. Indica la ruta manualmente editando el script."
    exit 1
}
$dllPath = $dllCandidates[0].FullName
Write-Host "   Encontrada en: $dllPath" -ForegroundColor Green

Write-Host "3) Cargando la libreria y conectando..." -ForegroundColor Cyan
Add-Type -Path $dllPath

$server = New-Object Microsoft.AnalysisServices.Tabular.Server
$server.Connect("Data Source=localhost:$port")

Write-Host "   Conectado. Bases de datos disponibles:" -ForegroundColor Green
foreach ($db in $server.Databases) {
    Write-Host "    - $($db.Name)"
}

$database = $server.Databases[0]
$model = $database.Model

$dump = [ordered]@{
    databaseName = $database.Name
    tables       = @()
}

foreach ($table in $model.Tables) {
    $tableInfo = [ordered]@{
        name        = $table.Name
        isHidden    = $table.IsHidden
        columns     = @()
        measures    = @()
    }
    foreach ($col in $table.Columns) {
        $tableInfo.columns += [ordered]@{
            name     = $col.Name
            dataType = $col.DataType.ToString()
            isHidden = $col.IsHidden
        }
    }
    foreach ($m in $table.Measures) {
        $tableInfo.measures += [ordered]@{
            name       = $m.Name
            expression = $m.Expression
            formatString = $m.FormatString
            isHidden   = $m.IsHidden
        }
    }
    $dump.tables += $tableInfo
}

$dump.relationships = @()
foreach ($rel in $model.Relationships) {
    $dump.relationships += [ordered]@{
        fromTable  = $rel.FromColumn.Table.Name
        fromColumn = $rel.FromColumn.Name
        toTable    = $rel.ToColumn.Table.Name
        toColumn   = $rel.ToColumn.Name
        isActive   = $rel.IsActive
    }
}

$dump | ConvertTo-Json -Depth 8 | Out-File -FilePath $OutputPath -Encoding utf8

Write-Host "4) Listo. Volcado del modelo guardado en:" -ForegroundColor Cyan
Write-Host "   $OutputPath" -ForegroundColor Green

$server.Disconnect()
