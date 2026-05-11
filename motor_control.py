import threading
import time
import busio
from board import SCL, SDA
from adafruit_pca9685 import PCA9685
from gpiozero import LED 

class MotorControl:
    def __init__(self):
        self.i2c = busio.I2C(SCL, SDA)
        self.pca = PCA9685(self.i2c)
        self.pca.frequency = 50
        self.lock = threading.Lock() # 保護 I2C 通訊 [cite: 77-78]
        # 右後輪 GPIO (25, 24) [cite: 197-199]
        self.din1 = LED(25); self.din2 = LED(24)

    def set_pwm(self, chan, duty):
        with self.lock: self.pca.channels[chan].duty_cycle = int(duty)

    def motor_run(self, idx, direction, speed):
        duty = int(speed * 655.35)
        # --- 左前輪 (idx 0)：已針對你的硬體進行方向補償 ---
        if idx == 0: 
            self.set_pwm(0, duty)
            if direction == 'forward': self.set_pwm(1, 65535); self.set_pwm(2, 0)
            else: self.set_pwm(1, 0); self.set_pwm(2, 65535)
        # --- 右前輪 (idx 1)：正常 ---
        elif idx == 1: 
            self.set_pwm(5, duty)
            if direction == 'forward': self.set_pwm(3, 65535); self.set_pwm(4, 0)
            else: self.set_pwm(3, 0); self.set_pwm(4, 65535)
        # --- 左後輪 (idx 2)：正常 ---
        elif idx == 2: 
            self.set_pwm(6, duty)
            if direction == 'forward': self.set_pwm(8, 65535); self.set_pwm(7, 0)
            else: self.set_pwm(8, 0); self.set_pwm(7, 65535)
        # --- 右後輪 (idx 3)：已針對你的硬體進行方向補償 ---
        elif idx == 3: 
            self.set_pwm(11, duty)
            if direction == 'forward': self.din1.off(); self.din2.on()
            else: self.din1.on(); self.din2.off()

    def steer(self, base_speed, steering):
        """差速控制：自動駕駛核心 [cite: 34-36]"""
        left_s = max(min(base_speed + steering, 100), 0)
        right_s = max(min(base_speed - steering, 100), 0)
        self.motor_run(0, 'forward', left_s); self.motor_run(2, 'forward', left_s)
        self.motor_run(1, 'forward', right_s); self.motor_run(3, 'forward', right_s)

    def set_servo_angle(self, chan, angle):
        """
        控制舵機角度 [cite: 200-204]
        chan: 9 (上下), 10 (左右) [cite: 215, 235-238]
        angle: 角度數值 (0-180) [cite: 208, 212]
        """
        # 將角度轉換為 PCA9685 的 duty cycle 數值 [cite: 208]
        duty = int((angle * 11 + 500) * 65535 / 20000)
        with self.lock: # 使用執行緒鎖保護 I2C 通訊 
            self.pca.channels[chan].duty_cycle = duty

    def stop(self):
        with self.lock:
            for i in [0, 5, 6, 11]: self.pca.channels[i].duty_cycle = 0
            self.din1.off(); self.din2.off()
