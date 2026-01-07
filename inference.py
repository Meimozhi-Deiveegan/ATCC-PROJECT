"""
ATCC Vehicle Detection - Inference Script
"""

from ultralytics import YOLO
import cv2
import matplotlib.pyplot as plt
from pathlib import Path

class VehicleDetector:
    def __init__(self, model_path):
        self.model = YOLO(model_path)
        self.class_names = {
            0: '2-wheeler',
            1: '3-wheeler',
            2: 'bus',
            3: 'lcv',
            4: 'car',
            5: '2-axle-truck',
            6: '3-axle-truck',
            7: 'multi-axle-truck',
            8: 'bicycle',
            9: 'handcart',
            10: 'person'
        }
    
    def detect_image(self, image_path, save=True):
        """Detect vehicles in image"""
        print(f"Processing: {Path(image_path).name}")
        
        results = self.model.predict(
            source=image_path,
            conf=0.25,
            save=save,
            save_txt=save
        )
        
        # Display results
        for r in results:
            if r.boxes is not None:
                print(f"\nDetected {len(r.boxes)} vehicles:")
                for box in r.boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    name = self.class_names.get(cls, f'class_{cls}')
                    print(f"  - {name}: {conf:.2%}")
            
            # Show image
            im_array = r.plot()
            im_rgb = cv2.cvtColor(im_array, cv2.COLOR_BGR2RGB)
            
            plt.figure(figsize=(12, 8))
            plt.imshow(im_rgb)
            plt.title(f"Vehicle Detection: {Path(image_path).name}")
            plt.axis('off')
            plt.show()
        
        return results

if __name__ == "__main__":
    # Example usage
    detector = VehicleDetector('yolov8n.pt')  # Use your trained model
    
    # Test with sample (create a test image first)
    import numpy as np
    test_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
    cv2.imwrite('test_sample.jpg', test_image)
    
    detector.detect_image('test_sample.jpg')
