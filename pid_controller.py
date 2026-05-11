import time

class PIDController:
    def __init__(self, kp=0.35, ki=0.0, kd=0.18):
        # 初始參數建議：Kp=0.35, Ki=0, Kd=0.18 [cite: 28, 41]
        self.kp = kp
        self.ki = ki
        self.kd = kd
        
        self.prev_error = 0
        self.integral = 0
        self.last_time = time.time()
        
        # 輸出限制範圍：-100 到 +100 [cite: 19]
        self.output_limits = (-100, 100)

    def calculate(self, error):
        current_time = time.time()
        dt = current_time - self.last_time
        if dt <= 0: dt = 1e-3 # 防止除以零

        # 1. P (Proportional): 比例控制，針對當前誤差立即修正 [cite: 18, 46]
        p_out = self.kp * error

        # 2. I (Integral): 積分控制，消除累積誤差 (本專案通常設為 0) [cite: 18, 46]
        self.integral += error * dt
        i_out = self.ki * self.integral

        # 3. D (Derivative): 微分控制，預測未來趨勢並抑制震盪 [cite: 18, 46]
        derivative = (error - self.prev_error) / dt
        d_out = self.kd * derivative

        # 總輸出公式：Kp*e + Ki*∫e + Kd*de/dt [cite: 18, 108]
        output = p_out + i_out + d_out

        # 限制輸出範圍在 -100 ~ +100 [cite: 19]
        output = max(min(output, self.output_limits[1]), self.output_limits[0])

        # 更新紀錄
        self.prev_error = error
        self.last_time = current_time

        return output

    def reset(self):
        """重置控制器，防止累積誤差影響下次啟動"""
        self.prev_error = 0
        self.integral = 0
        self.last_time = time.time()
