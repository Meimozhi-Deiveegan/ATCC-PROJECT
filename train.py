"""
ATCC Vehicle Detection - Training Script
"""

from ultralytics import YOLO
import argparse
import yaml

def train_model(data_yaml='configs/data.yaml', model_size='s', epochs=100):
    """Train YOLOv8 model for vehicle detection"""
    
    print("=" * 60)
    print("ATCC VEHICLE DETECTION TRAINING")
    print("=" * 60)
    print(f"Model: yolov8{model_size}.pt")
    print(f"Classes: 11 vehicle types")
    print(f"Epochs: {epochs}")
    print("=" * 60)
    
    # Load model
    model = YOLO(f'yolov8{model_size}.pt')
    
    # Train
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=640,
        batch=16,
        workers=4,
        device='cpu',  # Change to 'cuda' if you have GPU
        name=f'atcc_yolov8{model_size}',
        save=True,
        save_period=10,
        verbose=True
    )
    
    print("=" * 60)
    print("TRAINING COMPLETE!")
    print(f"Results saved in: runs/detect/atcc_yolov8{model_size}")
    print("=" * 60)
    
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', default='configs/data.yaml', help='Data config')
    parser.add_argument('--model', choices=['n','s','m','l','x'], default='s', help='Model size')
    parser.add_argument('--epochs', type=int, default=100, help='Training epochs')
    
    args = parser.parse_args()
    train_model(args.data, args.model, args.epochs)
