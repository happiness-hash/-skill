$ErrorActionPreference = "Stop"

Write-Host "配置 OpenAI 兼容接口用户级环境变量" -ForegroundColor Cyan
Write-Host "API Key 输入时不会显示在屏幕上。" -ForegroundColor DarkGray

$apiKeySecure = Read-Host "OPENAI_API_KEY" -AsSecureString
$apiKeyPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($apiKeySecure)
try {
    $apiKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($apiKeyPtr)
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($apiKeyPtr)
}

if ([string]::IsNullOrWhiteSpace($apiKey)) {
    throw "OPENAI_API_KEY 不能为空"
}

$baseUrl = Read-Host "OPENAI_BASE_URL [默认: https://api.openai.com/v1]"
if ([string]::IsNullOrWhiteSpace($baseUrl)) {
    $baseUrl = "https://api.openai.com/v1"
}

$model = Read-Host "OPENAI_MODEL [默认: gpt-4.1-mini]"
if ([string]::IsNullOrWhiteSpace($model)) {
    $model = "gpt-4.1-mini"
}

$visionModel = Read-Host "OPENAI_VISION_MODEL [默认同 OPENAI_MODEL]"
if ([string]::IsNullOrWhiteSpace($visionModel)) {
    $visionModel = $model
}

$timeout = Read-Host "OPENAI_TIMEOUT [默认: 12000]"
if ([string]::IsNullOrWhiteSpace($timeout)) {
    $timeout = "12000"
}

[Environment]::SetEnvironmentVariable("OPENAI_API_KEY", $apiKey, "User")
[Environment]::SetEnvironmentVariable("OPENAI_BASE_URL", $baseUrl, "User")
[Environment]::SetEnvironmentVariable("OPENAI_MODEL", $model, "User")
[Environment]::SetEnvironmentVariable("OPENAI_VISION_MODEL", $visionModel, "User")
[Environment]::SetEnvironmentVariable("OPENAI_TIMEOUT", $timeout, "User")

$env:OPENAI_API_KEY = $apiKey
$env:OPENAI_BASE_URL = $baseUrl
$env:OPENAI_MODEL = $model
$env:OPENAI_VISION_MODEL = $visionModel
$env:OPENAI_TIMEOUT = $timeout

Write-Host ""
Write-Host "已写入用户级环境变量。新打开的 PowerShell/程序会自动读取。" -ForegroundColor Green
Write-Host "当前 PowerShell 会话也已临时生效。" -ForegroundColor Green
Write-Host ""
Write-Host "当前配置："
Write-Host "OPENAI_API_KEY=已设置"
Write-Host "OPENAI_BASE_URL=$baseUrl"
Write-Host "OPENAI_MODEL=$model"
Write-Host "OPENAI_VISION_MODEL=$visionModel"
Write-Host "OPENAI_TIMEOUT=$timeout"
