# Publie (ou remplace) l'APK d'une appli dans la Release GitHub de son id.
# Le lien de téléchargement ne change jamais :
#   https://github.com/Cocosdnc/neocode-apps/releases/download/<id>/<Nom>.apk
#
# Exemple :
#   .\scripts\publier-apk.ps1 -Id funnyalarm -Nom FunnyAlarm -Apk "..\Funny Alarm\FunnyAlarm\FunnyAlarm-1.6.22.apk" -Version 1.6.22
param(
  [Parameter(Mandatory)] [string] $Id,       # id de l'appli dans public/apps.json (= tag de la Release)
  [Parameter(Mandatory)] [string] $Nom,      # nom du fichier publié, sans .apk
  [Parameter(Mandatory)] [string] $Apk,      # APK release signé à publier
  [Parameter(Mandatory)] [string] $Version
)
$ErrorActionPreference = 'Stop'
$repo = 'Cocosdnc/neocode-apps'
if (-not (Test-Path $Apk)) { throw "APK introuvable : $Apk" }

# Copie sous le nom publié (le nom du fichier est celui de l'asset GitHub).
$tmp = Join-Path ([IO.Path]::GetTempPath()) "neocode-apk-$Id"
New-Item -ItemType Directory -Force $tmp | Out-Null
$fichier = Join-Path $tmp "$Nom.apk"
Copy-Item $Apk $fichier -Force
$sha = (Get-FileHash $fichier -Algorithm SHA256).Hash.ToLower()
$titre = "$Nom $Version"
$notes = @"
**$Nom $Version** pour Android.

Télécharger : [$Nom.apk](https://github.com/$repo/releases/download/$Id/$Nom.apk), puis l'ouvrir sur le téléphone et autoriser l'installation (« Sources inconnues »).

SHA-256 : ``$sha``
"@

# PowerShell 5.1 change la sortie d'erreur de gh en exception : on la laisse à cmd.
cmd /c "gh release view $Id -R $repo >nul 2>nul"
if ($LASTEXITCODE -eq 0) {
  gh release upload $Id $fichier -R $repo --clobber
  if ($LASTEXITCODE -ne 0) { throw 'Envoi de l''APK refusé.' }
  gh release edit $Id -R $repo --title $titre --notes $notes
} else {
  gh release create $Id $fichier -R $repo --title $titre --notes $notes --latest=false
}
if ($LASTEXITCODE -ne 0) { throw 'Création ou mise à jour de la Release refusée.' }
Remove-Item $tmp -Recurse -Force
"OK : https://github.com/$repo/releases/download/$Id/$Nom.apk ($titre)"
