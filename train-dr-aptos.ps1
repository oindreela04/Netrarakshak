# Download APTOS 2019 from Kaggle with YOUR Kaggle account and train the NetraRakshak DR model on this PC.
#   powershell -ExecutionPolicy Bypass -File .\train-dr-aptos.ps1
#
# Before running (one time, in your browser):
#   1. Sign in at https://www.kaggle.com and open
#      https://www.kaggle.com/competitions/aptos2019-blindness-detection/rules  -> "I Understand and Accept".
#   2. Kaggle -> Settings -> API -> "Create New Token". Save the downloaded kaggle.json to
#      %USERPROFILE%\.kaggle\kaggle.json  (keep it private; never commit or share it).
# Needs ~20 GB free disk. An NVIDIA GPU is strongly recommended (CPU training takes many hours).
param([int]$Epochs = 0, [int]$Size = 0, [int]$BatchSize = 16)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = "$root\backend\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Run setup.ps1 first." }
$token = Join-Path $env:USERPROFILE ".kaggle\kaggle.json"
if (-not (Test-Path $token) -and -not $env:KAGGLE_API_TOKEN) { throw "Kaggle token not found at $token. See the instructions at the top of this script." }

& $py -m pip install --quiet kaggle
$data = "$root\backend\data\datasets\aptos2019"
New-Item -ItemType Directory -Force $data | Out-Null
if (-not (Test-Path "$data\train.csv")) {
  if (-not (Test-Path "$data\aptos2019-blindness-detection.zip")) {
    Write-Host "Downloading APTOS 2019 (about 10 GB)..." -ForegroundColor Cyan
    & $py -m kaggle competitions download -c aptos2019-blindness-detection -p $data
    if ($LASTEXITCODE -ne 0) { throw "Download failed. Did you accept the competition rules on kaggle.com with this account?" }
  }
  Write-Host "Extracting training images..." -ForegroundColor Cyan
  & $py -c "import zipfile,sys; z=zipfile.ZipFile(sys.argv[1]); [z.extract(m, sys.argv[2]) for m in z.namelist() if m=='train.csv' or m.startswith('train_images/')]" "$data\aptos2019-blindness-detection.zip" $data
}

$gpu = (& $py -c "import torch;print(torch.cuda.is_available())").Trim()
if ($gpu -eq "True") { if (-not $Size) { $Size = 384 }; if (-not $Epochs) { $Epochs = 25 } ; Write-Host "GPU detected." -ForegroundColor Green }
else { if (-not $Size) { $Size = 256 }; if (-not $Epochs) { $Epochs = 12 }; Write-Host "No CUDA GPU detected: training on CPU at ${Size}px for $Epochs epochs. Expect many hours." -ForegroundColor Yellow }

Set-Location "$root\backend"
& $py -m ai.modules.diabetic_retinopathy.train `
  --labels "$data\train.csv" --images "$data\train_images" --format aptos `
  --dataset-name "APTOS 2019 Blindness Detection (Kaggle)" `
  --dataset-licence "Kaggle competition rules accepted by the account holder; commercial use NOT confirmed" `
  --arch efficientnet_b0 --size $Size --epochs $Epochs --batch-size $BatchSize --workers 4 `
  --cache-dir "$root\backend\data\cache"
if ($LASTEXITCODE -ne 0) { throw "Training failed." }
Write-Host "`nModel registered and activated. Restart the API (start-backend.ps1), then open 'AI modules' in the app to see the test metrics." -ForegroundColor Green
