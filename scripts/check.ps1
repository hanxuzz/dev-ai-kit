param([ValidateSet('core','recording','browser','figma')][string]$Capability='core')
& (Join-Path $PSScriptRoot 'kit.ps1') 'check' '--capability' $Capability
exit $LASTEXITCODE
