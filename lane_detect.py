import cv2
import numpy as np
import os

# 1. 讀取影像
input_image_path = 'road.jpg'
img = cv2.imread(input_image_path)

if img is None:
    print(f"❌ 錯誤：無法開啟影像 {input_image_path}")
    print(f"請檢查檔案是否存在於：{os.getcwd()}")
    exit()

# 2. 影像預處理
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
blur = cv2.GaussianBlur(gray, (5, 5), 0)

# 3. Canny 邊緣偵測
edges = cv2.Canny(blur, 50, 150)

# 4. 定義感興趣區域 (ROI)
height, width = edges.shape
mask = np.zeros_like(edges)

# 這裡定義一個三角形/梯形區域，只保留畫面下半部的資訊
roi_vertices = np.array([[
    (0, height), 
    (width * 0.45, height * 0.6), 
    (width * 0.55, height * 0.6), 
    (width, height)
]], dtype=np.int32)

cv2.fillPoly(mask, roi_vertices, 255)
masked_edges = cv2.bitwise_and(edges, mask)

# 5. 執行 霍夫變換 (Hough Transform) 尋找直線
lines = cv2.HoughLinesP(masked_edges, 1, np.pi/180, 50, minLineLength=50, maxLineGap=150)

# 6. 繪製偵測結果
result_img = img.copy()
if lines is not None:
    print(f"✅ 成功偵測到 {len(lines)} 條線段")
    for line in lines:
        x1, y1, x2, y2 = line[0]
        cv2.line(result_img, (x1, y1), (x2, y2), (0, 255, 0), 3)
else:
    print("⚠ 未偵測到明顯車道線")

# 7. 儲存結果
output_image_path = 'lane_detection_result.jpg'
cv2.imwrite(output_image_path, result_img)
print(f"💾 結果已儲存至：{output_image_path}")
