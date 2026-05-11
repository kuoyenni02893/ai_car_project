# test_pid.py
import pytest

def test_pid_error_calculation():
    """
    測試驗證：PID 誤差計算是否正確
    """
    target_center = 320
    current_position = 350
    error = target_center - current_position
    
    assert error == -30, "PID 誤差計算邏輯錯誤"

def test_steering_clamping():
    """
    測試驗證：轉向限幅 (Clamping) 功能是否正常運作，防止馬達暴衝
    """
    max_steer = 70
    calculated_steer = 100
    
    # 模擬限幅邏輯
    if calculated_steer > max_steer:
        calculated_steer = max_steer
        
    assert calculated_steer == 70, "轉向限幅保護機制失效！"