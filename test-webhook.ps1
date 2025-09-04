$body = @{
    message = 'Test with extracted text'
    extracted_text = 'Supply air temperature 72F with cooling valve control'
    sessionId = 'test_fix_456'
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri 'http://localhost:5678/webhook/ingest-doc' -Method POST -ContentType 'application/json' -Body $body
$response | ConvertTo-Json -Depth 10
