# ATCC Dataset Combiner Script
# Combines all your datasets into one unified dataset

Write-Host "=== ATCC DATASET COMBINER ===" -ForegroundColor Cyan
Write-Host "Combining 8 datasets into one unified dataset" -ForegroundColor Green

$sourcePath = "F:\ATCC\data\ANNOTATED"
$destPath = "F:\ATCC\ATCC-PROJECT\datasets"

# Create destination directories
@("train\images", "train\labels", "val\images", "val\labels", "test\images", "test\labels") | ForEach-Object {
    New-Item -ItemType Directory -Path "$destPath\$_" -Force | Out-Null
}

# Find all YOLO datasets
$datasets = Get-ChildItem -Path $sourcePath -Directory | Where-Object {
    $_.Name -match '\.(yolov8|yolo)'
}

Write-Host "Found $($datasets.Count) YOLO datasets to combine:" -ForegroundColor Yellow
$datasets | ForEach-Object { Write-Host "  - $($_.Name)" -ForegroundColor Gray }

# Master class mapping for 11 classes
$masterClasses = @{
    0 = "2-wheeler"
    1 = "3-wheeler" 
    2 = "bus"
    3 = "lcv"
    4 = "car"
    5 = "2-axle-truck"
    6 = "3-axle-truck"
    7 = "multi-axle-truck"
    8 = "bicycle"
    9 = "handcart"
    10 = "person"
}

# Map dataset classes to our master classes
$classMapping = @{
    # From your datasets
    "2 axle truck" = 5      # -> 2-axle-truck
    "3 axle truck" = 6      # -> 3-axle-truck
    "LCV" = 3               # -> lcv
    "auto" = 1              # -> 3-wheeler
    "bus" = 2               # -> bus
    "car" = 4               # -> car
    "cycle" = 8             # -> bicycle
    "multi axle truck" = 7  # -> multi-axle-truck
    "person" = 10           # -> person
    "two wheeler" = 0       # -> 2-wheeler
    "tractor" = $null       # Skip (not in our 11 classes)
}

$totalImages = 0
$classStats = @{}

foreach ($dataset in $datasets) {
    Write-Host "`n📦 Processing: $($dataset.Name)" -ForegroundColor Cyan
    
    # Read dataset config
    $dataYaml = Join-Path $dataset.FullName "data.yaml"
    if (-not (Test-Path $dataYaml)) {
        Write-Host "  ⚠️ Skipping: No data.yaml" -ForegroundColor Yellow
        continue
    }
    
    # Parse YAML to get dataset classes
    $yamlContent = Get-Content $dataYaml -Raw
    $datasetClasses = @()
    
    if ($yamlContent -match 'names:\s*\r?\n((\s*\d+:\s*.+\r?\n)+)') {
        $namesSection = $matches[1]
        $namesSection -split "`r?`n" | ForEach-Object {
            if ($_ -match '\s*(\d+):\s*(.+)') {
                $datasetClasses += $matches[2].Trim()
            }
        }
    }
    
    Write-Host "  Classes found: $($datasetClasses.Count)" -ForegroundColor Gray
    for ($i=0; $i -lt $datasetClasses.Count; $i++) {
        $mappedId = $classMapping[$datasetClasses[$i]]
        $mappedName = if ($mappedId -ne $null) { $masterClasses[$mappedId] } else { "SKIP" }
        Write-Host "    $i: $($datasetClasses[$i]) -> $mappedId ($mappedName)" -ForegroundColor DarkGray
    }
    
    # Process each split
    $copiedThisDataset = 0
    
    foreach ($split in @("train", "valid", "test")) {
        $sourceImages = Join-Path $dataset.FullName "$split\images"
        $sourceLabels = Join-Path $dataset.FullName "$split\labels"
        
        $destSplit = if ($split -eq "valid") { "val" } else { $split }
        
        if (Test-Path $sourceImages) {
            $images = Get-ChildItem -Path $sourceImages -File -Include *.jpg, *.jpeg, *.png
            
            foreach ($img in $images) {
                # Generate unique filename
                $uniqueId = [System.Guid]::NewGuid().ToString("N").Substring(0, 8)
                $newImageName = "${uniqueId}_$($img.Name)"
                $destImagePath = "$destPath\$destSplit\images\$newImageName"
                
                # Copy image
                Copy-Item -Path $img.FullName -Destination $destImagePath -Force
                
                # Process corresponding label
                $labelFile = $img.Name -replace '\.[^.]*$', '.txt'
                $sourceLabelPath = Join-Path $sourceLabels $labelFile
                
                if (Test-Path $sourceLabelPath) {
                    $newLabelName = "${uniqueId}_$($img.BaseName).txt"
                    $destLabelPath = "$destPath\$destSplit\labels\$newLabelName"
                    
                    # Read and convert labels
                    $labelContent = Get-Content $sourceLabelPath
                    $newLabelLines = @()
                    
                    foreach ($line in $labelContent) {
                        if ($line.Trim()) {
                            $parts = $line.Trim() -split '\s+'
                            if ($parts.Count -ge 5) {
                                $oldClassId = [int]$parts[0]
                                if ($oldClassId -lt $datasetClasses.Count) {
                                    $className = $datasetClasses[$oldClassId]
                                    $newClassId = $classMapping[$className]
                                    
                                    if ($newClassId -ne $null) {
                                        # Update class ID
                                        $parts[0] = $newClassId.ToString()
                                        $newLabelLines += $parts -join ' '
                                        
                                        # Update statistics
                                        if (-not $classStats.ContainsKey($newClassId)) {
                                            $classStats[$newClassId] = 0
                                        }
                                        $classStats[$newClassId]++
                                    }
                                }
                            }
                        }
                    }
                    
                    if ($newLabelLines.Count -gt 0) {
                        $newLabelLines | Out-File -FilePath $destLabelPath -Encoding UTF8
                        $copiedThisDataset++
                        $totalImages++
                    }
                }
            }
            
            Write-Host "  $split`: $($images.Count) images" -ForegroundColor DarkGray
        }
    }
    
    Write-Host "  ✅ Copied: $copiedThisDataset images from this dataset" -ForegroundColor Green
}

# Create final data.yaml
$finalYaml = @"
# ATCC Combined Vehicle Dataset - 11 Classes
path: ./datasets
train: train/images
val: val/images
test: test/images

nc: 11
names:
  0: '2-wheeler'
  1: '3-wheeler'
  2: 'bus'
  3: 'lcv'
  4: 'car'
  5: '2-axle-truck'
  6: '3-axle-truck'
  7: 'multi-axle-truck'
  8: 'bicycle'
  9: 'handcart'
  10: 'person'
"@

$finalYaml | Out-File -FilePath "$destPath\data.yaml" -Encoding UTF8

Write-Host "`n🎉 DATASET COMBINATION COMPLETE!" -ForegroundColor Green -BackgroundColor DarkBlue
Write-Host "Total images combined: $totalImages" -ForegroundColor Yellow
Write-Host "Output folder: $destPath" -ForegroundColor Cyan

# Show class distribution
Write-Host "`n📊 CLASS DISTRIBUTION:" -ForegroundColor Cyan
foreach ($classId in (0..10)) {
    $count = if ($classStats.ContainsKey($classId)) { $classStats[$classId] } else { 0 }
    $name = $masterClasses[$classId]
    $percentage = if ($totalImages -gt 0) { [math]::Round(($count / $totalImages) * 100, 1) } else { 0 }
    Write-Host "  $classId: $name = $count instances ($percentage%)" -ForegroundColor Gray
}

Write-Host "`n=== NEXT STEPS ===" -ForegroundColor Yellow
Write-Host "1. Create zip for Colab: .\scripts\create_colab_zip.ps1" -ForegroundColor White
Write-Host "2. Upload to Colab and train!" -ForegroundColor White
