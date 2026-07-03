from src.actions.base_action import Advance,Sleep,ShiftLeft,ShiftRight,LeftOblique,RightOblique,BackUp,Stop
from src.utils import Controller

class Shift():
    def __init__(self):
        self.force = True  # 强制执行动作序列
        self.update_controller_speed = True  # 不更新控制器速度记录
        self.action_seq = [
            Advance(speed=30),       # 前进，速度30
            Sleep(sleep_time=1),         # 持续1秒
            
            ShiftLeft(speed=30),     # 向左平移
            Sleep(sleep_time=2),          # 持续1秒
            
            BackUp(speed=30),        # 后退
            Sleep(sleep_time=1),          # 持续1秒
            
            ShiftRight(speed=30),    # 向右平移
            Sleep(sleep_time=2),          # 持续1秒
            
            LeftOblique(speed=30),   # 斜向左前方
            Sleep(sleep_time=2),          # 持续1秒
            
            RightOblique(speed=30), # 斜向右前方
            Sleep(sleep_time=2),         # 持续0.8秒
            Stop()
        ]

ctrl = Controller()
ctrl.execute(Shift())