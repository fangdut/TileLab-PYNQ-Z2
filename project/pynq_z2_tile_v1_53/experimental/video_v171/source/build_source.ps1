param([Parameter(Mandatory=$true)][string]$Out)
$ErrorActionPreference='Stop'
$framework='C:/Windows/Microsoft.NET/Framework64/v4.0.30319'
if(Test-Path -LiteralPath $Out) { throw 'Choose a fresh output executable.' }
$sourceFile=[System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'RealPhotoSource.cs'))
if(-not (Test-Path -LiteralPath $sourceFile)) { throw "Source file missing: $sourceFile" }
$compilerArgs=@('/nologo','/target:exe','/platform:x64',("/out:"+[System.IO.Path]::GetFullPath($Out)))
foreach($reference in @('WPF/PresentationFramework.dll','WPF/PresentationCore.dll','WPF/WindowsBase.dll','System.Xaml.dll','System.Windows.Forms.dll','System.Web.Extensions.dll')) {
 $compilerArgs+=("/r:"+[System.IO.Path]::GetFullPath((Join-Path $framework $reference)))
}
$compilerArgs+=$sourceFile
& "$framework/csc.exe" @compilerArgs
if($LASTEXITCODE -ne 0) { throw 'Photo source compilation failed.' }
