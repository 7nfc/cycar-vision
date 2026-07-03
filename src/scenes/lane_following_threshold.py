import time
import numpy as np
import cv2
from src.actions import SetServo,Stop,Start,TurnLeft,TurnRight,Advance
from src.scenes.base_scene import BaseScene
from src.utils import log

def extract_yellow_region(image):
    """提取黄色车道线区域"""
    # 1. 转换为HSV色彩空间
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # 2. 定义黄色的HSV范围
    lower_yellow = np.array([10, 30, 80])  # H下限, S下限, V下限
    upper_yellow = np.array([40, 255, 255]) # H上限, S上限, V上限
    
    # 3. 创建黄色区域的掩膜
    mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
    
    # 4. 应用掩膜获取黄色区域
    yellow_region = cv2.bitwise_and(image, image, mask=mask)
    
    # 5. 转换为灰度图并二值化
    gray = cv2.cvtColor(yellow_region, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY)
    
    return binary

def getEdgeImg(binary_img):
    """使用Canny算子提取边缘"""
    # 参数说明：
    # binary_img - 输入二值图像
    # 50 - 低阈值
    # 150 - 高阈值
    # apertureSize - Sobel算子大小，默认为3
    edges = cv2.Canny(binary_img, 50, 150)
    return edges

def roi_mask(img, corner_points):
    """设置感兴趣区域(ROI)"""
    # 1. 创建与输入图像相同大小的全黑掩膜
    mask = np.zeros_like(img)
    
    # 2. 在掩膜上填充多边形区域（白色）
    cv2.fillPoly(mask, [corner_points], 255)
    
    # 3. 应用掩膜，只保留ROI区域
    masked_img = cv2.bitwise_and(img, mask)
    
    return masked_img

def process_image(image):
    """处理图像，保留右侧车道线的内线"""
    rows, cols = image.shape
    for i in range(rows):  # 遍历每一行
        for j in range(cols-1, -1, -1):  # 从右向左遍历每一列
            if image[i, j] != 0:  # 找到第一个非零像素（右侧车道线）
                # 将该像素左侧的2个像素置零（去除外侧线）
                for k in range(max(0, j-2), j):
                    image[i, k] = 0
                break  # 处理完当前行后跳到下一行
    return image

def getRLaneLine(edges_img):
    """使用霍夫变换检测右侧车道线（不缩放坐标）"""
    lines = cv2.HoughLinesP(edges_img, rho=1, theta=np.pi/180, threshold=3, minLineLength=15, maxLineGap=30)
    
    if lines is not None:
        right_lines = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 == x1:
                continue
            slope = (y2 - y1) / (x2 - x1)
            if slope > 0:
                right_lines.append(line[0])
        
        if right_lines: # 如果检测到右车道候选线
            # 计算每条线段的欧氏距离，选出最长的
            longest_line = max(right_lines, key=lambda line: np.linalg.norm(line[2:]-line[:2]))
            x1, y1, x2, y2 = longest_line  # 直接使用小图坐标 ，提取最长线段的端点坐标
            slope = (y2 - y1) / (x2 - x1)
            intercept = y1 - slope * x1#截距
            return slope, intercept  # 返回小图坐标系的斜率和截距
    
    return None, None

def get_cur_offset_x(imgOri):
    """计算小车当前位置与目标位置的偏移量"""
    # 1. 缩放图像到1/4大小
    small_img = cv2.resize(imgOri, (int(imgOri.shape[1]/4), int(imgOri.shape[0]/4)))
    
    # 2. 提取黄色车道线区域
    roi_binary = extract_yellow_region(small_img)
    
    # 3. 获取边缘图像
    edges = getEdgeImg(roi_binary)
    
    # 4. 设置ROI区域（图像下半部分的3/4区域）
    rows, cols = edges.shape
    points = np.array([[
        [0, rows],         # 左下角
        [0, int(rows*0.25)],  # 左上角
        [cols, int(rows*0.25)], # 右上角
        [cols, rows]       # 右下角
    ]])
    
    # 5. 应用ROI掩膜
    roi_edges = roi_mask(edges, points)
    
    # 6. 处理图像，保留右侧车道线
    processed_img = process_image(roi_edges)
    
    # 7. 获取右侧车道线参数
    slope, intercept = getRLaneLine(processed_img)
    if slope is None or intercept is None:
        log.warning("未检测到车道线，保持直行")
        return None  # 返回0偏移量，保持直行
    
    # 8. 计算当前车道线与图像底部的交点 (y=rows-1)
    cur_pos = int((rows-1 - intercept) / slope)
    
    # 9. 计算偏移量 (目标位置X₀需要根据实际测量确定)
    X0 = 380  
    delta_X = cur_pos - X0
    
    # 10. 缩放回原图尺寸
    return delta_X * 4

class LF_threshold(BaseScene):
    def __init__(self, memory_name, camera_info, msg_queue, config=None):
       # 在类初始化时添加可配置参数
        super().__init__(memory_name, camera_info, msg_queue)
        self.forward_spd = 15  # 将spd重命名为forward_spd以保持一致性
        self.servo_h = 100    # 添加servo_h初始化
        self.servo_v = 60     # 添加servo_v初始化
        self.config = config or {
           'hsv_lower': [10, 30, 80],
           'hsv_upper': [40, 255, 255],
           'canny_thresh': [50, 150],
           'hough_params': {'rho': 1, 'theta': np.pi/180, 'threshold': 50, 
                           'minLineLength': 50, 'maxLineGap': 20}
       }


    def init_state(self):
        log.info(f'start init {self.__class__.__name__}')  
        self.ctrl.execute(SetServo(servo=[100,60])) 
        return False
    
    def adjust_position(self, x_offset):
       
        """
        根据横向偏移量调整小车位置
        参数:
            x_offset: 横向偏移量(像素) 
                - 正数: 车辆偏右，需左转修正
                - 负数: 车辆偏左，需右转修正
                - None: 未检测到车道线
        """
        print(f"DEBUG - x_offset: {x_offset}")  # 添加调试输出
        # 1. 处理检测不到车道线的情况
        if x_offset is None:
            log.warning("未检测到车道线，降速直行")
            self.ctrl.execute(Advance(speed=self.forward_spd//2))
            return
        
        # 根据x_offset的值执行不同的控制指令
        if -60 < x_offset <= 60:
            log.info(f"偏移量 {x_offset:.1f}px 在允许范围内，保持直行")
            self.ctrl.execute(Advance(speed=self.forward_spd))
            
        elif 60 < x_offset <= 90:
            log.info(f"车辆偏左 {x_offset:.1f}px,右转 0.05rad")
            self.ctrl.execute(TurnRight(speed=self.forward_spd, degree=0.05))
        elif 90 < x_offset <= 120:
            log.info(f"车辆偏左 {x_offset:.1f}px,右转 0.10rad")
            self.ctrl.execute(TurnRight(speed=self.forward_spd, degree=0.10))
        elif 120 < x_offset <= 150:
            log.info(f"车辆偏左 {x_offset:.1f}px,右转 0.16rad")
            self.ctrl.execute(TurnRight(speed=self.forward_spd, degree=0.16))
        elif 150 < x_offset <= 180:
            log.info(f"车辆偏左 {x_offset:.1f}px,右转 0.20rad")
            self.ctrl.execute(TurnRight(speed=self.forward_spd, degree=0.20))
        elif 180 < x_offset <= 240:
            log.info(f"车辆偏左 {x_offset:.1f}px,右转 0.28rad")
            self.ctrl.execute(TurnRight(speed=self.forward_spd, degree=0.28))
        elif 240 < x_offset <= 300:
            log.info(f"车辆偏左 {x_offset:.1f}px,右转 0.36rad")
            self.ctrl.execute(TurnRight(speed=self.forward_spd, degree=0.36))
        elif x_offset > 300:
            log.info(f"车辆偏左 {x_offset:.1f}px,右转 0.45rad")
            self.ctrl.execute(TurnRight(speed=self.forward_spd, degree=0.45))
            
        elif -90 < x_offset <= -60:
            log.info(f"车辆偏右 {abs(x_offset):.1f}px,左转 0.05rad")
            self.ctrl.execute(TurnLeft(speed=self.forward_spd, degree=0.05))
        elif -120 < x_offset <= -90:
            log.info(f"车辆偏右 {abs(x_offset):.1f}px,左转 0.10rad")
            self.ctrl.execute(TurnLeft(speed=self.forward_spd, degree=0.10))
        elif -150 < x_offset <= -120:
            log.info(f"车辆偏右 {abs(x_offset):.1f}px,左转 0.16rad")
            self.ctrl.execute(TurnLeft(speed=self.forward_spd, degree=0.16))
        elif -180 < x_offset <= -150:
            log.info(f"车辆偏右 {abs(x_offset):.1f}px,左转 0.20rad")
            self.ctrl.execute(TurnLeft(speed=self.forward_spd, degree=0.20))
        elif -240 < x_offset <= -180:
            log.info(f"车辆偏右 {abs(x_offset):.1f}px,左转 0.28rad")
            self.ctrl.execute(TurnLeft(speed=self.forward_spd, degree=0.28))
        elif -300 < x_offset <= -240:
            log.info(f"车辆偏右 {abs(x_offset):.1f}px,左转 0.36rad")
            self.ctrl.execute(TurnLeft(speed=self.forward_spd, degree=0.36))
        elif x_offset <= -300:
            log.info(f"车辆偏右 {abs(x_offset):.1f}px,左转 0.45rad")
            self.ctrl.execute(TurnLeft(speed=self.forward_spd, degree=0.45))


    def loop(self):
        """
        车道保持主循环，包含完整的异常处理和资源管理
        """
        # 1. 初始化舵机角度
        try:
            self.ctrl.execute(SetServo(servo=[100, 60]))
            log.info("舵机初始化完成")
        except Exception as e:
            log.error(f"舵机初始化失败: {str(e)}")
            self.ctrl.execute(Stop())
            return

        # 2. 初始化状态检查
        if self.init_state():
            log.error('初始化失败，退出车道保持')
            self.ctrl.execute(Stop())
            return

        # 3. 摄像头共享内存检查
        try:
            frame = np.ndarray(
                (self.height, self.width, 3), 
                dtype=np.uint8, 
                buffer=self.broadcaster.buf
            )
            if frame.size == 0:
                raise ValueError("空帧缓冲区")
        except Exception as e:
            log.error(f'摄像头共享内存不可用: {str(e)}')
            self.ctrl.execute(Stop())
            return

        # 4. 主处理循环
        last_valid_time = time.time()
        max_no_signal_time = 5.0  # 最大无有效信号时间(秒)

        try:
            while not self.stop_sign.value:
                current_time = time.time()

                # 4.1 处理暂停状态
                if self.pause_sign.value:
                    self.ctrl.execute(Stop())
                    time.sleep(0.1)
                    continue

                try:
                    # 4.2 获取当前帧
                    img_bgr = frame.copy()
                    if img_bgr.size == 0:
                        raise ValueError("接收到空帧")

                    # 4.3 计算偏移量
                    x_offset = get_cur_offset_x(img_bgr) #四倍的

                    # 4.4 处理无车道线情况
                    if x_offset is None:
                        if current_time - last_valid_time > max_no_signal_time:
                            log.error("长时间未检测到车道线，停止车辆")
                            self.ctrl.execute(Stop())
                            break
                        
                        log.warning("未检测到车道线，临时停止")
                        self.ctrl.execute(Stop())
                        time.sleep(0.5)
                        continue
                    
                    # 4.5 更新最后有效时间
                    last_valid_time = current_time

                    # 4.6 调整位置
                    self.adjust_position(x_offset)

                    # 4.7 控制循环频率
                    time.sleep(0.05)  # 约20Hz频率

                except Exception as e:
                    log.error(f'图像处理错误: {str(e)}')
                    self.ctrl.execute(Stop())

                    # 严重错误时退出循环
                    if isinstance(e, (MemoryError, BufferError)):
                        break
                    
                    time.sleep(1)

        except KeyboardInterrupt:
            log.info('用户中断，停止车辆')
        except Exception as e:
            log.error(f'主循环异常: {str(e)}')
        finally:
            # 5. 最终清理
            try:
                self.ctrl.execute(Stop())
                log.info("车道保持已安全停止")
            except Exception as e:
                log.error(f'停止指令发送失败: {str(e)}')

            # 释放资源
            if hasattr(self, 'broadcaster'):
                try:
                    self.broadcaster.close()
                except:
                    pass