import datetime
import os
import cv2
import numpy as np
import time
from src.actions import Advance, BackUp, Sleep, Stop, TurnLeft, TurnRight, SpinClockwise, SpinAntiClockwise, ShiftLeft, ShiftRight, LeftOblique, RightOblique, SetServo, CustomAction

from src.scenes.base_scene import BaseScene
from src.utils import log

class Manual(BaseScene):
    def __init__(self, memory_name, camera_info, msg_queue):
        super().__init__(memory_name, camera_info, msg_queue)
        self.speed = 15 #默认速度
        self.speed_step = 5  # 设置速度调整步长
        self.min_speed = 10  # 最小速度
        self.max_speed = 50  # 最大速度
        self.save_dir = os.path.join(os.getcwd(), 'capture') #截图保存目录
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir, exist_ok=True)

        # 初始化舵机角度
        self.servo_h = 100  # 水平角度
        self.servo_v = 60  # 垂直角度
        self.servo_step = 5  # 每次按键调整的角度步长

        #初始化预览窗口
        self.preview_window = "Live Camera Preview"
        cv2.namedWindow(self.preview_window, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.preview_window, 640, 480)

         # 添加状态变量
        self.last_key = None
        self.last_action_time = 0
        self.action_cooldown = 0.1  # 动作冷却时间(秒)

        def adjust_speed(self, increase=True):
            """调整速度并确保在合理范围内"""
            if increase:
                self.speed = min(self.max_speed, self.speed + self.speed_step)
            else:
                self.speed = max(self.min_speed, self.speed - self.speed_step)
        
            # 如果当前有移动动作，更新速度
            if isinstance(self.last_action, (Advance, BackUp, TurnLeft, TurnRight)):
                self.last_action.speed = self.speed
                self.last_action.speed_setting = self.last_action.generate_speed_setting(speed=self.speed)
                self.last_action.fix_speed()
                self.ctrl.execute(self.last_action)

    def init_state(self):
        self.ctrl.execute(Stop())  # 先停止
        log.info(f'start init {self.__class__.__name__}')  
        self.ctrl.execute(SetServo(servo=[100,60])) 
        log.info(f"Current servo angle: {self.ctrl.servo_angle}")  # 打印当前舵机角度
        return False
        
      
    def loop(self):
        """手动控制场景主循环"""
        ret = self.init_state()
        last_update = time.time()
    
        if ret:
            log.error(f'[{self.__class__.__name__}] init failed')
            return
        
        #从共享内存中读取图像帧数据，以及记录日志标记场景循环开始
        frame = np.ndarray([self.height, self.width, 3], dtype=np.uint8, buffer=self.broadcaster.buf)
        log.info(f'[{self.__class__.__name__}] loop start')
    
        # 初始化时只发送一次舵机角度
        self.ctrl.execute(SetServo(servo=[self.servo_h, self.servo_v]))
    
        last_action = Stop()  # 初始化默认动作为停止
        default_degree = 45   # 定义默认转向角度
        
        while True:
            current_time = time.time()
            
            # 每0.3秒刷新画面
            if current_time - last_update >= 0.3:
                try:
                    # 从共享内存获取帧
                    frame = np.ndarray(
                        [self.height, self.width, 3], 
                        dtype=np.uint8, 
                        buffer=self.broadcaster.buf
                    )
                    if frame is None or frame.size == 0:
                        log.warning("接收到空帧，跳过处理")
                        time.sleep(0.1)
                        continue
                    
                    # 显示画面（带FPS提示和舵机角度信息）
                    fps_text = f"FPS: {1/(current_time - last_update):.1f}" if last_update != 0 else "Initializing..."
                    servo_text = f"Servo: H={self.servo_h} V={self.servo_v}"
                    cv2.putText(frame, fps_text, (10, 30), #绘制文本
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)#字体
                    cv2.putText(frame, servo_text, (10, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.imshow(self.preview_window, frame)
                    
                    # 必须调用waitKey才能显示窗口
                    if cv2.waitKey(1) & 0xFF == ord('q'):#等待用户按键
                        break
                        
                    last_update = current_time
                    
                except Exception as e:
                    log.error(f"画面刷新失败: {str(e)}")
                    time.sleep(0.1)
    
            try:
                if not self.msg_queue.empty():
                    key = self.msg_queue.get()  # 获取按键
                else:
                    continue
            except KeyboardInterrupt:
                self.ctrl.execute(Stop())
                break
            
            # 按键映射到动作
            if key == 'w':
                last_action = Advance(speed=self.speed)
            elif key == 'a':
                last_action = TurnLeft(speed=self.speed, degree=default_degree)
            elif key == 's':
                last_action = BackUp(speed=self.speed)
            elif key == 'd':
                last_action = TurnRight(speed=self.speed, degree=default_degree)
            elif key == 'q':
                last_action = SpinAntiClockwise(speed=self.speed)
            elif key == 'e':
                last_action = SpinClockwise(speed=self.speed)
            elif key == 'r':
                last_action = ShiftLeft(speed=self.speed)
            elif key == 't':
                last_action = ShiftRight(speed=self.speed)
            elif key == 'x':
                last_action = RightOblique(speed=self.speed)
            elif key == 'z':
                last_action = LeftOblique(speed=self.speed)
            elif key == 'up':
                self.speed = min(60, self.speed + 10)
                if isinstance(last_action, (Advance, BackUp, TurnLeft, TurnRight, SpinClockwise, SpinAntiClockwise, ShiftLeft, ShiftRight, LeftOblique, RightOblique)):
                    last_action.speed = self.speed
                    # 对于转向动作，保持原来的值
                    if isinstance(last_action, (TurnLeft, TurnRight)):
                        last_action.speed_setting = last_action.generate_speed_setting(speed=self.speed, degree=default_degree)
                    else:
                        last_action.speed_setting = last_action.generate_speed_setting(speed=self.speed)
                    last_action.fix_speed()
            
            elif key == 'down': 
                self.speed = max(0, self.speed - 10)  
                if isinstance(last_action, (Advance, BackUp, TurnLeft, TurnRight, SpinClockwise, SpinAntiClockwise, ShiftLeft, ShiftRight, LeftOblique, RightOblique)):
                    last_action.speed = self.speed
                    # 对于转向动作，保持原来的值
                    if isinstance(last_action, (TurnLeft, TurnRight)):
                        last_action.speed_setting = last_action.generate_speed_setting(speed=self.speed, degree=default_degree)
                    else:
                        last_action.speed_setting = last_action.generate_speed_setting(speed=self.speed)
                    last_action.fix_speed()
    
            # 修改舵机控制部分
            elif key in ['i', 'j', 'k', 'l']:
                if key == 'i': 
                    self.servo_v = min(90, self.servo_v + self.servo_step)
                elif key == 'k': 
                    self.servo_v = max(0, self.servo_v - self.servo_step)
                elif key == 'j': 
                    self.servo_h = min(180, self.servo_h + self.servo_step)
                elif key == 'l': 
                    self.servo_h = max(0, self.servo_h - self.servo_step)
    
                # 直接发送SetServo指令
                action = SetServo(servo=[self.servo_h, self.servo_v])
                action.update_servo = True
                ret = self.ctrl.execute(action)
                log.info(f"Set servo to {self.servo_h},{self.servo_v}, ret={ret}")
                continue  # 跳过后续动作处理
            
            elif key == 'c': 
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                try:
                    cv2.imwrite(os.path.join(self.save_dir, f"capture_{timestamp}.jpg"), frame)
                    log.info(f"图像已保存: capture_{timestamp}.jpg")
                    # 显示捕获确认
                    cv2.putText(frame, "CAPTURED!", (50, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    cv2.imshow(self.preview_window, frame)
                    cv2.waitKey(300)
                except Exception as e:
                    log.error(f"保存图像失败: {str(e)}")        
                
            elif key == 'space':
                last_action = Stop()
                self.speed = 15  # 重置为默认速度
    
            # 执行动作
            self.ctrl.execute(last_action)
    
        cv2.destroyAllWindows()
        self.ctrl.execute(Stop())