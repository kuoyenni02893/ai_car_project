import cv2
import numpy as np

class LaneDetector:
    def __init__(self):
        # 根據講義，二值化閾值建議設
        self.threshold = 80
        self.last_error = 0
        self.lane_width = 300  # 預存車道平均寬度，用於單線分析 [cite: 27]

    def process_frame(self, frame):
        # 1. 取得影像大小 (預期為 640x480) [cite: 25]
        height, width = frame.shape[:2]
        center_x = width // 2

        # 2. 灰階轉換與高斯模糊 
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # 3. 二值化處理 (找出白色車道線)
        # 根據簡報 Slide 9 的設計，將亮度閾值拉高到 200，嚴格過濾暗部
        _, binary = cv2.threshold(blurred, 200, 255, cv2.THRESH_BINARY)

        # --- [新增] 簡報核心技術：形態學過濾 (Morphological Filtering) ---
        # 建立一個 5x5 的方塊矩陣作為核心
        kernel = np.ones((5, 5), np.uint8)
        
        # 使用「開運算 (MORPH_OPEN)」：先侵蝕 (Erosion) 掉細碎的地板反光雜訊，
        # 再膨脹 (Dilation) 回復原本真正白線的粗度。這能完美消除燈光倒影！
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        # 4. ROI 遮罩：僅分析畫面下半部以減少雜訊干擾 [cite: 10, 25, 100]
        mask = np.zeros_like(binary)
        # 把 0.65 改成 0.4！讓車子看畫面的下半部 60%，提早計算轉向誤差
        mask[int(height*0.4):height, :] = 255
        masked_binary = cv2.bitwise_and(binary, mask)

        # 5. 分左右半區計算白色像素質心 [cite: 11, 12]
        left_mask = np.zeros_like(masked_binary)
        left_mask[:, :center_x] = 255
        right_mask = np.zeros_like(masked_binary)
        right_mask[:, center_x:] = 255

        left_part = cv2.bitwise_and(masked_binary, left_mask)
        right_part = cv2.bitwise_and(masked_binary, right_mask)

        left_m = cv2.moments(left_part)
        right_m = cv2.moments(right_part)

        # 6. 計算左、右線質心 x 座標 [cite: 11, 12]
        lx = int(left_m['m10'] / left_m['m00']) if left_m['m00'] > 0 else None
        rx = int(right_m['m10'] / right_m['m00']) if right_m['m00'] > 0 else None

        # # 7. 中線估計邏輯
        if lx is not None and rx is not None:
            lane_center = (lx + rx) / 2
        elif lx is not None:
            lane_center = lx + (self.lane_width / 2)
        elif rx is not None:
            lane_center = rx - (self.lane_width / 2)
        else:
            # 關鍵修改處
            lane_center = center_x + self.last_error

        # # 8. 計算偏差量 Error
        error = lane_center - center_x
        self.last_error = error
        
        return error, masked_binary
