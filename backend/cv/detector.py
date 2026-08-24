import logging

import numpy as np
from ultralytics import YOLO

logging.getLogger("ultralytics").setLevel(logging.WARNING)

# winner of the threshold-vs-MAE tuning in notebooks/detection.ipynb
BEST_CONF = 0.1

_model = None


def get_model(weights_path: str = "yolov8n.pt") -> YOLO:
    global _model
    if _model is None:
        _model = YOLO(weights_path)
    return _model


def detect_persons(frame: np.ndarray, conf: float = BEST_CONF) -> np.ndarray:
    results = get_model()(frame, classes=[0], conf=conf, verbose=False, device="cpu")
    boxes = results[0].boxes
    if boxes is None or len(boxes) == 0:
        return np.empty((0, 4))
    return boxes.xyxy.cpu().numpy()


def xyxy_to_xywh(box) -> list[float]:
    x1, y1, x2, y2 = box
    return [float(x1), float(y1), float(x2) - float(x1), float(y2) - float(y1)]
