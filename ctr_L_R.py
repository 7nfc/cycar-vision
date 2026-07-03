from src.actions.base_action import Advance, TurnLeft, TurnRight, Sleep, Stop
from src.utils import Controller

class Left_Right():
    def __init__(self):
        self.force = True  # 强制执行动作序列
        self.update_controller_speed = True  # 不更新控制器速度记录
        self.action_seq = [
            Advance(speed=32),          # 前进
            Sleep(sleep_time=2),             # 持续2秒
            TurnLeft(speed=32, degree=90),  # 左转，速度32，转向程度80%
            Sleep(sleep_time=2),             # 持续2秒
            TurnRight(speed=32, degree=90), # 右转，速度32，转向程度80%
            Sleep(sleep_time=2),              # 持续2秒
            Stop()
        ]

# 创建控制器并执行动作序列
ctrl = Controller()
ctrl.execute(Left_Right())