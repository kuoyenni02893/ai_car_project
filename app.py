from flask import Flask, render_template, Response, request, jsonify
import cv2, time, threading
from picamera2 import Picamera2
from ultralytics import YOLO
from motor_control import MotorControl
from lane_detector import LaneDetector
from pid_controller import PIDController

app = Flask(__name__)
robot = MotorControl()
lane_det = LaneDetector()
pid_ctrl = PIDController(kp=0.15, ki=0.0, kd=0.25)

# [修改 1] 載入你剛剛辛苦訓練出的專屬模型 best.pt
model = YOLO('models/weights.pt')

# [修改 2] 在狀態變數中新增 "traffic_light" 紀錄目前的燈號
status = {"mode": "manual", "base_speed": 35, "yolo_enabled": True, "traffic_light": "green"}

picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (640, 480)})
picam2.configure(config)

# 註解掉手動控制，讓相機自己決定曝光和白平衡（避免全紅/全藍）
# picam2.set_controls({"AeEnable": True, "AwbEnable": True, "AwbMode": 1}) 
# picam2.set_controls({"Brightness": -0.15, "ExposureValue": -0.8})
picam2.start()

frame_count = 0  # 確保這行放在 gen_frames 外面或作為全域變數
current_auto_speed = 0

def gen_frames():
    global frame_count, current_auto_speed
    while True:
        try:
            # 取得影像
            frame = picam2.capture_array()
            
            # --- [終極色彩修復] ---
            if len(frame.shape) == 3:
                channels = frame.shape[2]
                if channels == 4:
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
                elif channels == 3:
                    # 解決「陰間青色濾鏡」的關鍵，把 RGB 轉回正確的 BGR
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # 注意這裡的縮排！不管上面有沒有轉換色彩，畫面都一定要翻轉
            frame = cv2.rotate(frame, cv2.ROTATE_180)
            # ----------------------

            # 1. 每一幀都執行車道辨識，確保駕駛穩定
            error, debug_frame = lane_det.process_frame(frame)

            if status["mode"] == "auto":
            # [修改 3] 新增紅綠燈煞車邏輯：如果是紅燈，直接強制停車
               if status["traffic_light"] == "red":
                
                 # 【防當機神技：煞車只踩一次，不要連發！】
                 # 只有當車子還有速度時，才發送停止指令
                  if current_auto_speed != 0:
                      robot.stop()
                      current_auto_speed = 0  # 標記為已停止，下次迴圈就不會再發送指令了
                
                # 在畫面上印出超大的警告字樣方便監控
                  cv2.putText(frame, "RED LIGHT! STOP!", (120, 240),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 4)
                            
               else:
                # 如果不是紅燈，才執行原本的 PID 循線邏輯
                # (a) 容忍區間：稍微調回 10，過濾掉相機震動產生的微小誤差
                if abs(error) < 10:
                    error = 0

                # 1. 計算 PID 轉向力道
                steering = pid_ctrl.calculate(error)

                # 2. 轉向限幅：稍微降回 60，避免過度拉扯
                max_steer = 60  
                if steering > max_steer:
                    steering = max_steer
                elif steering < -max_steer:
                    steering = -max_steer

                # --- [修改] 極致平滑過彎降速 ---
                # 不要用 if 來急煞，直接讓「速度」隨著「轉向力道」等比例下降
                # 轉得越彎，速度自然扣得越多，完全不會有頓挫感
                target_speed = status["base_speed"] - (abs(steering) * 0.4)
                
                # 確保最低速度維持在 25，才推得動這台車
                target_speed = max(25, target_speed)

                # --- 軟體緩啟動與加減速邏輯 ---
                if current_auto_speed < target_speed:
                    current_auto_speed += 1       
                elif current_auto_speed > target_speed:
                    current_auto_speed -= 1  # 煞車也改回 1，不要急煞！

                try:
                    # 執行馬達控制 (記得轉成整數)
                    robot.steer(int(current_auto_speed), int(steering))
                except Exception as e:
                    print(f"⚠️ I2C 通訊安全略過: {e}")
                
            
            # 2. YOLO 紅綠燈辨識
            frame_count += 1
            if frame_count % 10 == 0:  # 每 10 幀看一次
                
                # 直接餵原圖給模型！(刪除調暗，刪除寫入 SD 卡的存檔動作)
                results = model(frame, imgsz=192, conf=0.15, verbose=False)

                detected_light = "green" # 預設綠燈
                for r in results:
                    for box in r.boxes:
                        label = model.names[int(box.cls[0])].lower()
                        conf_score = float(box.conf[0])
                        
                        # [除錯] 印出 AI 看到的所有東西
                        print(f"👁️ AI 偵測到: {label} (信心度: {conf_score:.2f})")
                        
                        if "red" in label:
                            detected_light = "red"
                            print("🔴 YOLO 看到紅燈啦！執行煞車！")
                            break
                
                status["traffic_light"] = detected_light

            # 3. 疊加 Error 文字資訊，方便你從網頁監控
            cv2.putText(frame, f"Error: {error:.1f}", (10, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # 4. 影像編碼與輸出給網頁
            ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 40])
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

        except Exception as e:
            print(f"影像串流錯誤: {e}")
            break

@app.route('/')
def index(): return render_template('index.html')

@app.route('/video_feed')
def video_feed(): return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/set_param')
def set_param():
    mode = request.args.get('mode')
    speed = request.args.get('speed')
    kp = request.args.get('kp')
    kd = request.args.get('kd')
    ki = request.args.get('ki')

    if mode: status["mode"] = mode
    if speed: status["base_speed"] = int(speed)
    if kp: pid_ctrl.kp = float(kp)
    if kd: pid_ctrl.kd = float(kd)
    if ki: pid_ctrl.ki = float(ki)

    # 切換回手動時立即停車，確保安全
    if status["mode"] == "manual":
        robot.stop()

    return jsonify(status)

@app.route('/move')
def car_move():
    action = request.args.get('action')
    # 如果在自動模式下，不接受手動指令
    if status["mode"] == "auto":
        return "In Auto Mode"

    if action == 'forward':
        target_speed = status["base_speed"]
        # 從 20 開始，每次加 5，直到達到目標速度 (避免瞬間大電流)
        for s in range(20, target_speed + 1, 5):
            robot.steer(s, 0)
            time.sleep(0.05)  # 每次微調停頓 0.05 秒讓電池適應
            
    elif action == 'reverse':
        target_speed = status["base_speed"]
        for s in range(20, target_speed + 1, 5):
            for i in range(4): robot.motor_run(i, 'backward', s)
            time.sleep(0.05)
    elif action == 'left':
        # 轉彎時動力稍微提高 20
        robot.motor_run(0, 'backward', status["base_speed"]+20)
        robot.motor_run(2, 'backward', status["base_speed"]+20)
        robot.motor_run(1, 'forward', status["base_speed"]+20)
        robot.motor_run(3, 'forward', status["base_speed"]+20)
    elif action == 'right':
        robot.motor_run(1, 'backward', status["base_speed"]+20)
        robot.motor_run(3, 'backward', status["base_speed"]+20)
        robot.motor_run(0, 'forward', status["base_speed"]+20)
        robot.motor_run(2, 'forward', status["base_speed"]+20)
    elif action == 'stop':
        robot.stop()
    return "OK"

@app.route('/servo')
def servo_control():
    # 舵機控制：9號上下，10號左右
    direction = request.args.get('direction')
    if direction == 'up': robot.set_servo_angle(9, 25)
    elif direction == 'down': robot.set_servo_angle(9, 50)
    elif direction == 'left': robot.set_servo_angle(10, 110)
    elif direction == 'right': robot.set_servo_angle(10, 70)
    elif direction == 'home':
        robot.set_servo_angle(9, 40); robot.set_servo_angle(10, 90)
    return "OK"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
