from src.actions.base_action import Advance,SpinAntiClockwise,Sleep,SpinClockwise,Stop
from src.utils import Controller

class Rotate():
    def __init__(self):
        self.force = True  # 强制执行动作序列
        self.update_controller_speed = True  # 不更新控制器速度记录
        self.action_seq = [
            Advance(speed=30),          # 前进，速度30
            Sleep(sleep_time=3),             # 持续1秒
            
            SpinAntiClockwise(speed=30), # 逆时针旋转，速度30
            Sleep(sleep_time=3),           # 持续0.8秒
            
            Advance(speed=30),          # 再次前进
            Sleep(sleep_time=3),           # 持续0.5秒
            
            SpinClockwise(speed=30),    # 顺时针旋转，速度30
            Sleep(sleep_time=3),            # 持续0.8秒
            Stop()
        ]

ctrl = Controller()
ctrl.execute(Rotate())