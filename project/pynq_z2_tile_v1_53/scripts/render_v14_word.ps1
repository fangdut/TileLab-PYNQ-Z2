param([string]$DocPath=(Join-Path (Split-Path $PSScriptRoot -Parent) 'docs/Tile_V1.4_连续采集最佳截图与真实数据评估报告.docx'))
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
$qaPath=Join-Path $projectRoot 'reports/v14/document_qa'
New-Item -ItemType Directory -Path $qaPath -Force | Out-Null
$pdfPath=Join-Path $qaPath 'report.pdf'
$word=$null;$document=$null
try {
 $word=New-Object -ComObject Word.Application
 $word.Visible=$false;$word.DisplayAlerts=0
 $document=$word.Documents.Open($DocPath,$false,$true,$false)
 $document.ExportAsFixedFormat($pdfPath,17)
 Write-Output $pdfPath
} finally {
 if($document){$document.Close(0);[void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($document)}
 if($word){$word.Quit();[void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($word)}
}
$poppler=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
& $poppler -r 120 -png $pdfPath (Join-Path $qaPath 'page')
if($LASTEXITCODE -ne 0){throw 'PDF rendering failed'}
