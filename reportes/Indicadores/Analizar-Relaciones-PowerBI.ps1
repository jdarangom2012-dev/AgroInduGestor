# Analizar-Relaciones-PowerBI.ps1
# Amplia el volcado anterior: trae el detalle completo de cada relacion
# (cardinalidad, direccion de filtrado cruzado, si esta activa) y detecta
# columnas tipo "Id..." que no tienen ninguna relacion asociada (candidatas
# a relaciones faltantes).
#
# Uso: igual que el script anterior, ejecutar desde la carpeta Indicadores:
#   .\Analizar-Relaciones-PowerBI.ps1

$ErrorActionPreference = "Stop"

$OutputPath = "D:\Obras\TostadoraCentral\AppTostadoraCentral\reportes\Indicadores\pbi_relaciones_dump.json"

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
if ($ports.Count -eq 0) { Write-Error "No se pudo determinar el puerto de msmdsrv.exe."; exit 1 }
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
if ($dllCandidates.Count -eq 0) { Write-Error "No se encontro Microsoft.AnalysisServices.Tabular.dll."; exit 1 }
$dllPath = $dllCandidates[0].FullName
Write-Host "   Encontrada en: $dllPath" -ForegroundColor Green

Write-Host "3) Conectando..." -ForegroundColor Cyan
Add-Type -Path $dllPath
$server = New-Object Microsoft.AnalysisServices.Tabular.Server
$server.Connect("Data Source=localhost:$port")
$database = $server.Databases[0]
$model = $database.Model
Write-Host "   Conectado a la base: $($database.Name)" -ForegroundColor Green

# --- Relaciones con detalle completo ---
$relaciones = @()
foreach ($rel in $model.Relationships) {
    $relaciones += [ordered]@{
        name                     = $rel.Name
        fromTable                = $rel.FromColumn.Table.Name
        fromColumn               = $rel.FromColumn.Name
        fromCardinality          = $rel.FromCardinality.ToString()
        toTable                  = $rel.ToColumn.Table.Name
        toColumn                 = $rel.ToColumn.Name
        toCardinality            = $rel.ToCardinality.ToString()
        crossFilteringBehavior   = $rel.CrossFilteringBehavior.ToString()
        isActive                 = $rel.IsActive
        securityFilteringBehavior = $rel.SecurityFilteringBehavior.ToString()
    }
}

# --- Deteccion heuristica de columnas "Id..." sin relacion ---
$columnasEnRelaciones = New-Object System.Collections.Generic.HashSet[string]
foreach ($rel in $model.Relationships) {
    [void]$columnasEnRelaciones.Add("$($rel.FromColumn.Table.Name).$($rel.FromColumn.Name)")
    [void]$columnasEnRelaciones.Add("$($rel.ToColumn.Table.Name).$($rel.ToColumn.Name)")
}

$candidatas = @()
foreach ($table in $model.Tables) {
    foreach ($col in $table.Columns) {
        $esCandidata = ($col.Name -match '^(Id|id)[A-Z]' -or $col.Name -match 'Id$' -or $col.Name -eq 'Id' -or $col.Name -eq 'id')
        if ($esCandidata) {
            $clave = "$($table.Name).$($col.Name)"
            if (-not $columnasEnRelaciones.Contains($clave)) {
                $candidatas += [ordered]@{
                    tabla  = $table.Name
                    columna = $col.Name
                    tipo   = $col.DataType.ToString()
                }
            }
        }
    }
}

# --- Tablas totalmente aisladas (sin ninguna relacion) ---
$tablasConRelacion = New-Object System.Collections.Generic.HashSet[string]
foreach ($rel in $model.Relationships) {
    [void]$tablasConRelacion.Add($rel.FromColumn.Table.Name)
    [void]$tablasConRelacion.Add($rel.ToColumn.Table.Name)
}
$tablasAisladas = @()
foreach ($table in $model.Tables) {
    if (-not $table.IsHidden -and -not $tablasConRelacion.Contains($table.Name) -and $table.Columns.Count -gt 1) {
        $tablasAisladas += $table.Name
    }
}

$resultado = [ordered]@{
    databaseName            = $database.Name
    relaciones               = $relaciones
    tablasAisladas           = $tablasAisladas
    columnasIdSinRelacion    = $candidatas
}

$resultado | ConvertTo-Json -Depth 8 | Out-File -FilePath $OutputPath -Encoding utf8

Write-Host "4) Listo. Guardado en:" -ForegroundColor Cyan
Write-Host "   $OutputPath" -ForegroundColor Green

$server.Disconnect()
