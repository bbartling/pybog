# Test script for unified PyBOG workflow
# PowerShell script to test all workflow paths

$baseUrl = "http://localhost:8000"
$webhookUrl = "$baseUrl/api/n8n/webhook/pybog-main"
$sessionId = "test_session_$(Get-Date -Format 'yyyyMMdd_HHmmss')"

Write-Host "Testing Unified PyBOG Workflow" -ForegroundColor Cyan
Write-Host "Session ID: $sessionId" -ForegroundColor Yellow
Write-Host "================================" -ForegroundColor Gray

# Test 1: Greeting/Initial Message
Write-Host "`nTest 1: Initial greeting message" -ForegroundColor Green
$greetingPayload = @{
    sessionId = $sessionId
    message = "Hello"
    action = "chat"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri $webhookUrl -Method Post -Body $greetingPayload -ContentType "application/json"
    Write-Host "Response Status: $($response.status)" -ForegroundColor White
    Write-Host "Message: $($response.message)" -ForegroundColor Gray
    if ($response.capabilities) {
        Write-Host "Capabilities:" -ForegroundColor Gray
        $response.capabilities | ForEach-Object { Write-Host "  - $_" -ForegroundColor Gray }
    }
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
}

# Test 2: Send HVAC text for analysis
Write-Host "`nTest 2: Send HVAC text for analysis" -ForegroundColor Green
$hvacText = @"
VAV Box Control Sequence:
The VAV box shall modulate the damper position based on the following:
1. Space temperature sensor input (55-85°F range)
2. Supply air temperature sensor (50-65°F)
3. Damper actuator control (0-100% position)
4. When space temperature > cooling setpoint + 2°F, open damper to maximum
5. When space temperature < heating setpoint - 2°F, open damper to minimum ventilation
6. Modulate damper between min and max based on temperature deviation
"@

$analysisPayload = @{
    sessionId = $sessionId
    message = "Analyze this HVAC sequence"
    action = "analyze"
    extracted_text = $hvacText
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri $webhookUrl -Method Post -Body $analysisPayload -ContentType "application/json"
    Write-Host "Response Status: $($response.status)" -ForegroundColor White
    Write-Host "Message: $($response.message)" -ForegroundColor Gray
    
    if ($response.analysis) {
        Write-Host "Analysis Results:" -ForegroundColor Cyan
        Write-Host "  Inputs: $($response.analysis.inputs.Count) found" -ForegroundColor Gray
        $response.analysis.inputs | ForEach-Object { Write-Host "    - $_" -ForegroundColor DarkGray }
        Write-Host "  Outputs: $($response.analysis.outputs.Count) found" -ForegroundColor Gray
        $response.analysis.outputs | ForEach-Object { Write-Host "    - $_" -ForegroundColor DarkGray }
        Write-Host "  Control Blocks: $($response.analysis.controlBlocks.Count)" -ForegroundColor Gray
        Write-Host "  Ready for BOG: $($response.readyForBOG)" -ForegroundColor Yellow
    }
    
    # Store for next test
    $global:analysisData = $response.analysis
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
}

# Test 3: Generate BOG (if analysis was successful)
if ($global:analysisData) {
    Write-Host "`nTest 3: Generate BOG from analysis" -ForegroundColor Green
    
    $generatePayload = @{
        sessionId = $sessionId
        action = "generate"
        io_points = $global:analysisData.io_points
        control_blocks = $global:analysisData.controlBlocks
        pseudocode = $global:analysisData.pseudocode
    } | ConvertTo-Json -Depth 10
    
    try {
        $response = Invoke-RestMethod -Uri $webhookUrl -Method Post -Body $generatePayload -ContentType "application/json"
        Write-Host "Response Status: $($response.status)" -ForegroundColor White
        Write-Host "Message: $($response.message)" -ForegroundColor Gray
        
        if ($response.downloadUrl) {
            Write-Host "Download URL: $($response.downloadUrl)" -ForegroundColor Green
            Write-Host "BOG File Path: $($response.bogFilePath)" -ForegroundColor Gray
        }
    } catch {
        Write-Host "Error: $_" -ForegroundColor Red
    }
}

# Test 4: Test file upload (optional - requires a PDF file)
$testPdfPath = "C:\Users\tech\Projects\pybog\test_files\sample_hvac.pdf"
if (Test-Path $testPdfPath) {
    Write-Host "`nTest 4: File upload and processing" -ForegroundColor Green
    
    # Create multipart form data
    $boundary = [System.Guid]::NewGuid().ToString()
    $LF = "`r`n"
    
    $bodyLines = @(
        "--$boundary",
        "Content-Disposition: form-data; name=`"sessionId`"",
        "",
        $sessionId,
        "--$boundary",
        "Content-Disposition: form-data; name=`"action`"",
        "",
        "process",
        "--$boundary",
        "Content-Disposition: form-data; name=`"files`"; filename=`"sample_hvac.pdf`"",
        "Content-Type: application/pdf",
        "",
        [System.Text.Encoding]::Default.GetString([System.IO.File]::ReadAllBytes($testPdfPath)),
        "--$boundary--"
    )
    
    $body = $bodyLines -join $LF
    
    try {
        $headers = @{
            "Content-Type" = "multipart/form-data; boundary=$boundary"
        }
        
        # Note: This is simplified - actual file upload may need different handling
        Write-Host "File upload test requires manual testing with curl or Postman" -ForegroundColor Yellow
        Write-Host "Command: curl -X POST $webhookUrl -F 'files=@$testPdfPath' -F 'sessionId=$sessionId' -F 'action=process'" -ForegroundColor Gray
    } catch {
        Write-Host "Error: $_" -ForegroundColor Red
    }
} else {
    Write-Host "`nTest 4: Skipping file upload test (no test file found)" -ForegroundColor Yellow
}

# Test 5: Chat interaction
Write-Host "`nTest 5: Regular chat interaction" -ForegroundColor Green
$chatPayload = @{
    sessionId = $sessionId
    message = "What components are needed for a VAV system?"
    action = "chat"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri $webhookUrl -Method Post -Body $chatPayload -ContentType "application/json"
    Write-Host "Response Status: $($response.status)" -ForegroundColor White
    Write-Host "Chat Response: $($response.message)" -ForegroundColor Gray
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
}

Write-Host "`n================================" -ForegroundColor Gray
Write-Host "Workflow testing complete!" -ForegroundColor Cyan
Write-Host "Session ID: $sessionId" -ForegroundColor Yellow

# Summary
Write-Host "`nTest Summary:" -ForegroundColor Cyan
Write-Host "1. Greeting Test: " -NoNewline
Write-Host "Check console output above" -ForegroundColor Gray
Write-Host "2. Analysis Test: " -NoNewline
Write-Host "Check console output above" -ForegroundColor Gray
Write-Host "3. Generation Test: " -NoNewline
Write-Host "Check console output above" -ForegroundColor Gray
Write-Host "4. File Upload: " -NoNewline
Write-Host "Manual test required" -ForegroundColor Yellow
Write-Host "5. Chat Test: " -NoNewline
Write-Host "Check console output above" -ForegroundColor Gray
