import cv2
import numpy as np

FACE_HEIGHT_RATIO = 0.3
BLUR_KERNEL = (99, 99)


def blur_faces(frame: np.ndarray, boxes_xyxy) -> np.ndarray:
    h, w = frame.shape[:2]
    for x1, y1, x2, y2 in boxes_xyxy:
        bw = float(x2 - x1)
        bh = float(y2 - y1)
        face_h = max(int(bh * FACE_HEIGHT_RATIO), 1)
        face_w = max(int(bw * 0.7), 1)
        fx1 = max(int(x1) + (int(bw) - face_w) // 2, 0)
        fy1 = max(int(y1), 0)
        fx2 = min(fx1 + face_w, w)
        fy2 = min(fy1 + face_h, h)
        if fx2 <= fx1 or fy2 <= fy1:
            continue
        region = frame[fy1:fy2, fx1:fx2]
        frame[fy1:fy2, fx1:fx2] = cv2.GaussianBlur(region, BLUR_KERNEL, 30)
    return frame
