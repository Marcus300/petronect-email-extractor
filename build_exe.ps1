$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$workPath = Join-Path ([System.IO.Path]::GetTempPath()) "PetronectEmailExtractor-build"

if (-not (Test-Path $python)) {
	$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
	if (-not $pythonCommand) {
		Write-Error "Python não encontrado. Crie .venv ou disponibilize python no PATH."
		exit 1
	}
	$python = $pythonCommand.Source
}

$version = (& $python -c "from email_extractor.version import __version__; print(__version__)").Trim()
if ($LASTEXITCODE -ne 0 -or -not $version) { exit 1 }
$applicationName = "Petronect Email Extractor v$version"

& $python -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $python -m pip install pyinstaller
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $python -m PyInstaller --noconfirm --clean --onefile --windowed `
	--name $applicationName `
	--workpath $workPath `
	--distpath (Join-Path $PSScriptRoot "dist") `
	--icon (Join-Path $PSScriptRoot "docs\logo\logo.ico") `
	--version-file (Join-Path $PSScriptRoot "version_info.txt") `
	--add-data ((Join-Path $PSScriptRoot "docs\logo\logo.ico") + ";.") `
	--add-data ((Join-Path $PSScriptRoot "docs\logo\logo.png") + ";.") `
	--hidden-import win32com.client `
	--hidden-import pythoncom `
	--hidden-import pywintypes `
	--hidden-import win32timezone `
	(Join-Path $PSScriptRoot "main.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# The CLI build is fully described above; keep its generated .spec out of the source tree.
$generatedSpec = Join-Path $PSScriptRoot "$applicationName.spec"
if (Test-Path -LiteralPath $generatedSpec) {
	[System.IO.File]::Delete($generatedSpec)
}
