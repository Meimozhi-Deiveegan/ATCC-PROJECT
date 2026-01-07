# Dataset Preparation Script
Write-Host "=== Preparing ATCC Dataset ===" -ForegroundColor Cyan

$sourcePath = "F:\ATCC\data\ANNOTATED"
$destPath = "F:\ATCC\ATCC-PROJECT\datasets"

Write-Host "Source: $sourcePath"
Write-Host "Destination: $destPath"

# Check if source exists
if (-not (Test-Path $sourcePath)) {
    Write-Host "❌ ERROR: Source path not found!" -ForegroundColor Red
    Write-Host "Make sure your data is at: F:\ATCC\data\ANNOTATED" -ForegroundColor Yellow
    exit 1
}

# Count datasets
$datasets = Get-ChildItem -Path $sourcePath -Directory | Where-Object { $_.Name -match '\.yolov8' }
Write-Host "Found $($datasets.Count) YOLO datasets" -ForegroundColor Green

# Copy from first dataset for testing
if ($datasets.Count -gt 0) {
    $firstDataset = $datasets[0]
    Write-Host "`nUsing dataset: $($firstDataset.Name)" -ForegroundColor Yellow
    
    # Copy train images and labels
    Copy-Item -Path "$($firstDataset.FullName)\train\images\*" -Destination "$destPath\train\images\" -Force -ErrorAction SilentlyContinue
    Copy-Item -Path "$($firstDataset.FullName)\train\labels\*" -Destination "$destPath\train\labels\" -Force -ErrorAction SilentlyContinue
    
    # Copy validation images and labels
    Copy-Item -Path "$($firstDataset.FullName)\valid\images\*" -Destination "$destPath\val\images\" -Force -ErrorAction SilentlyContinue
    Copy-Item -Path "$($firstDataset.FullName)\valid\labels\*" -Destination "$destPath\val\labels\" -Force -ErrorAction SilentlyContinue
    
    # Count files
    $trainImages = (Get-ChildItem -Path "$destPath\train\images" -File -ErrorAction SilentlyContinue).Count
    $trainLabels = (Get-ChildItem -Path "$destPath\train\labels" -File -ErrorAction SilentlyContinue).Count
    $valImages = (Get-ChildItem -Path "$destPath\val\images" -File -ErrorAction SilentlyContinue).Count
    
    Write-Host "`n✅ Dataset prepared:" -ForegroundColor Green
    Write-Host "   Training images: $trainImages" -ForegroundColor Gray
    Write-Host "   Training labels: $trainLabels" -ForegroundColor Gray
    Write-Host "   Validation images: $valImages" -ForegroundColor Gray
    
    # Check label format
    if ($trainLabels -gt 0) {
        $sampleLabel = Get-ChildItem -Path "$destPath\train\labels" -File | Select-Object -First 1
        $content = Get-Content $sampleLabel.FullName -First 1
        Write-Host "   Sample label: $content" -ForegroundColor Cyan
    }
} else {
    Write-Host "No YOLO datasets found!" -ForegroundColor Red
}

Write-Host "`n=== NEXT ===" -ForegroundColor Yellow
Write-Host "Run: python train.py --epochs 5 (for test training)" -ForegroundColor White
