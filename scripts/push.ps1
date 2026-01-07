Write-Host "=== Pushing to GitHub ===" -ForegroundColor Cyan

# Check Git
if (-not (Test-Path ".git")) {
    git init
    git remote add origin https://github.com/Meimozhi-Deiveegan/ATCC-PROJECT.git
}

# Create README
echo "# ATCC Vehicle Detection" > README.md
echo "## 11 Vehicle Classes" >> README.md
echo "1. 2-wheeler" >> README.md
echo "2. 3-wheeler" >> README.md
echo "3. bus" >> README.md
echo "4. lcv" >> README.md
echo "5. car" >> README.md
echo "6. 2-axle truck" >> README.md
echo "7. 3-axle truck" >> README.md
echo "8. multi-axle truck" >> README.md
echo "9. bicycle" >> README.md
echo "10. handcart" >> README.md
echo "11. person" >> README.md

# Create configs
mkdir configs -Force
echo "path: ./datasets" > configs/data.yaml
echo "train: train/images" >> configs/data.yaml
echo "val: val/images" >> configs/data.yaml
echo "nc: 11" >> configs/data.yaml
echo "names: ['2-wheeler','3-wheeler','bus','lcv','car','2-axle-truck','3-axle-truck','multi-axle-truck','bicycle','handcart','person']" >> configs/data.yaml

# Create .gitignore
echo "venv/" > .gitignore
echo "*.pt" >> .gitignore
echo "datasets/" >> .gitignore
echo "data/" >> .gitignore
echo "runs/" >> .gitignore

# Add to Git
git add .
git commit -m "ATCC Vehicle Detection Project"
git branch -M main
git push -u origin main

Write-Host "✅ Done! Check: https://github.com/Meimozhi-Deiveegan/ATCC-PROJECT" -ForegroundColor Green
