import time
from abc import ABC,abstractmethod

class BaseAction(ABC):
    def __init__(self,*args,**kwds) -> None:
        # 初始化动作的速度和舵机角度
        self.speed = kwds.get('speed',-1) # 默认速度-1表示需要更新
        self.servo_angle = kwds.get('servo',[-1,-1])# 默认舵机角度[-1,-1]表示需要更新
        self.motor_rating = [1,1,1,1] # 电机比例系数
        self.update_speed = False# 是否需要更新速度
        self.update_servo = True # 是否需要更新舵机角度

        if self.speed == -1:
            self.update_speed = True
        
        if self.servo_angle[0] == -1 and self.servo_angle[1] == -1:
            self.update_servo = True

        #由速度生成方法将抽象的总体速度计算为4个电机的速度并输出为list
        self.speed_setting = self.generate_speed_setting(self.speed)
        self.fix_speed()# 根据电机比例调整速度

    def fix_speed(self):# 根据电机比例调整速度
        #是一个四个元素的列表，代表四个速度
        self.speed_setting = [int(speed * ratio) for speed,ratio in zip(self.speed_setting,self.motor_rating)]

    @staticmethod
    @abstractmethod
    def generate_speed_setting(speed,degree=0):
        #抽象方法，用于生成电机速度设置
        pass

    def __call__(self,speed,servo_angle):
        #调用动作时更新速度和舵机角度
        if self.update_servo:
            self.servo_angle = servo_angle
        if self.update_speed:
            degree = 0
            if hasattr(self,'degree'):#检查当前动作是否有degree属性
                degree = self.degree
            self.speed_setting = self.generate_speed_setting(speed,degree)
            self.fix_speed()
        
        return self.speed_setting + self.servo_angle
    
#前进
class Advance (BaseAction):
    @staticmethod
    def generate_speed_setting (speed,degree=0):
        return[speed,speed,speed,speed]

#后退
class BackUp(BaseAction):
    @staticmethod
    def generate_speed_setting(speed, degree=0):
        return[-speed,-speed,-speed,-speed]

# 停止
class Stop(BaseAction):
    @staticmethod
    def generate_speed_setting(speed, degree=0):
        return [0, 0, 0, 0]
    
# 延迟
class Sleep(BaseAction):
    def __init__(self, *args, **kwds): 
        self.sleep_time = kwds.get('sleep_time', 0)
        self.speed_setting = None
        self.servo_angle = [-1, -1]
        self.update_speed = False
        self.update_servo = False

    @staticmethod
    def generate_speed_setting(speed, degree=0):
        return []

    def __call__(self, speed, servo_angle):
        time.sleep(self.sleep_time)#单纯延迟，不控制电机
        return None

#左转
class TurnLeft(BaseAction):
    def __init__(self, *args, **kwds):
        self.degree = kwds.get('degree', 0)#转弯角度
        self.update_controller_speed = False  # 禁止更新控制器速度
        super().__init__(*args, **kwds)
        self.speed_setting = self.generate_speed_setting(speed=self.speed, degree=self.degree)
        self.fix_speed()

    @staticmethod
    def generate_speed_setting(speed, degree=0):
        left_speed = int(speed * (1 - degree))
        right_speed = int(speed * (1 + degree))
        return [left_speed, left_speed, right_speed, right_speed]

#右转
class TurnRight(BaseAction):
    def __init__(self, *args, **kwds):
        self.degree = kwds.get('degree', 0)
        self.update_controller_speed = False  # 禁止更新控制器速度
        super().__init__(*args, **kwds)
        self.speed_setting = self.generate_speed_setting(speed=self.speed, degree=self.degree)
        self.fix_speed()

    @staticmethod
    def generate_speed_setting(speed, degree=0):
        left_speed = int(speed * (1 + degree))
        right_speed = int(speed * (1 - degree))
        return [left_speed, left_speed, right_speed, right_speed]

#顺时针旋转
class SpinClockwise(BaseAction):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.speed_setting = self.generate_speed_setting(speed=self.speed)
        self.fix_speed()

    @staticmethod
    def generate_speed_setting(speed, degree=0):
        return [speed, speed, -speed, -speed]

#逆时针旋转
class SpinAntiClockwise(BaseAction):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.speed_setting = self.generate_speed_setting(speed=self.speed)
        self.fix_speed()

    @staticmethod
    def generate_speed_setting(speed, degree=0):
        return [-speed, -speed, speed, speed]
    
#左平移
class ShiftLeft(BaseAction):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.speed_setting = self.generate_speed_setting(speed=self.speed)
        self.fix_speed()

    @staticmethod
    def generate_speed_setting(speed, degree=0):
        return [speed,-speed,speed,-speed]

#右平移
class ShiftRight(BaseAction):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.speed_setting = self.generate_speed_setting(speed=self.speed)
        self.fix_speed()

    @staticmethod
    def generate_speed_setting(speed, degree=0):
        return [-speed,speed,-speed,speed]
    
#斜向左
class LeftOblique(BaseAction):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.speed_setting = self.generate_speed_setting(speed=self.speed)
        self.fix_speed()

    @staticmethod
    def generate_speed_setting(speed, degree=0):
        return [speed,0,speed,0]

#斜向右
class RightOblique(BaseAction):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.speed_setting = self.generate_speed_setting(speed=self.speed)
        self.fix_speed()

    @staticmethod
    def generate_speed_setting(speed, degree=0):
        return [0,speed,0,speed]
    
#调整舵机角度时，小车不动
class SetServo(BaseAction):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.speed = 0
        if 'servo' in kwds:
            self.servo_angle = kwds['servo']
        elif len(args) > 0:
            self.servo_angle = args[0]
        else:
            self.servo_angle = [100, 60]  # 默认值改为 [100,60]
        
        self.update_servo = True  # 强制更新舵机
        self.update_speed = False  # 不更新速度

    @staticmethod
    def generate_speed_setting(speed, degree=0):
        return [0, 0, 0, 0]  # 电机停止
    
    
#方便修改平移的四个动作
class CustomAction(BaseAction):

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.speed_setting = kwds.get('motor_setting',[0,0,0,0])
        self.update_controller_speed = False
        self.update_speed = False

    @staticmethod
    def generate_speed_setting(speed, degree=0):
        return [0,0,0,0]