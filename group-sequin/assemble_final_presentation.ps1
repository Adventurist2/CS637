param(
 [Parameter(Mandatory=$true)][string]$SourcePptx,
 [Parameter(Mandatory=$true)][string]$SectionPptx,
 [Parameter(Mandatory=$true)][string]$OutputPptx
)
$ErrorActionPreference='Stop'
$existing=@(Get-Process POWERPNT -ErrorAction SilentlyContinue)
$app=$null;$deck=$null
try {
 $app=New-Object -ComObject PowerPoint.Application
 $app.DisplayAlerts=1;$app.AutomationSecurity=3
 $deck=$app.Presentations.Open($SourcePptx,-1,-1,0)
 if($deck.Slides.Count -ne 15){throw 'The supplied project template must contain 15 original slides.'}
 $inserted=$deck.Slides.InsertFromFile($SectionPptx,14)
 if($inserted -ne 16){throw 'The extension section must contain 16 slides.'}
 # The source template contains tutorial artwork on its default master.
 # Added slides carry their own explicit header and must hide that artwork.
 for($i=15;$i -le 30;$i++){$deck.Slides.Item($i).DisplayMasterShapes=0}
 $deck.SaveCopyAs($OutputPptx,24)
 [pscustomobject]@{slides=$deck.Slides.Count;inserted=$inserted}|ConvertTo-Json -Compress
} finally {
 if($null -ne $deck){$deck.Close();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($deck)}
 if($null -ne $app){if($existing.Count -eq 0){$app.Quit()};[void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)}
}
