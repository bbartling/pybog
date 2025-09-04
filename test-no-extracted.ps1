$body = @{
    message = 'Test without extracted text'
    sessionId = 'test_no_extracted_789'
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri 'http://localhost:5678/webhook/ingest-doc' -Method POST -ContentType 'application/json' -Body $body
$response | ConvertTo-Json -Depth 10
