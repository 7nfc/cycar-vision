import logging
import os
import time
import numpy as np
from src.actions import SetServo, Stop, TurnLeftInPlace, TurnRightInPlace, TurnAround, Start
from src.scenes.base_scene import BaseScene
from src.scenes.logo_match import TemplateMatcher
from src.utils import log
from src.utils.logger import logger_instance  # 引入日志实例
import cv2

class Helper_template_match(BaseScene):
    def __init__(self, memory_name, camera_info, msg_queue):
        super().__init__(memory_name, camera_info, msg_queue)

        self.template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        logger_instance.info(f"模板目录已设置为: {self.template_dir}")

        self.capture_dir = "captures"
        os.makedirs(self.capture_dir, exist_ok=True)

        self.tm = None
        self.last_detection_time = 0
        self.detection_cooldown = 0.1
        
    def init_state(self):
        logger_instance.info(f'开始初始化 {self.__class__.__name__} 场景')
        try:
            self.tm = TemplateMatcher(self.template_dir, match_threshold=0.73, nms_threshold=0.5)
            
            self.ctrl.execute(SetServo(servo=[100, 60]))
            logger_instance.info('舵机已设置为默认角度 [100, 60]')

            self.ctrl.execute(Start())
            logger_instance.info('控制器已启动')

            return False  # 初始化成功
        except Exception as e:
            log.error(f'初始化失败: {str(e)}')
            return True  # 初始化失败

    def loop(self):
        if self.init_state():
            log.error('初始化失败，退出')
            self.ctrl.execute(Stop())
            return

        frame = np.ndarray(
            (self.height, self.width, 3),
            dtype=np.uint8,
            buffer=self.broadcaster.buf
        )

        while not self.stop_sign.value:
            current_time = time.time()

            try:
                # 1. 获取并预处理图像
                img_bgr = frame.copy()
                img_yuv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YUV)
                img_yuv[:,:,0] = cv2.equalizeHist(img_yuv[:,:,0])
                img_bgr = cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)
                logger_instance.debug('图像已完成预处理')

                # 2. 执行模板匹配（仅一次）
                results = self.tm.infer(img_bgr)
                logger_instance.info(f"模板匹配完成，检测到 {len(results)} 个可能的路标")

                # 新增详细日志信息
                if results:
                    logger_instance.info("以下是检测到的路标详情:")
                    for i, result in enumerate(results, 1):
                        name = result['name']
                        score = result['score']
                        box = result['box']
                        center_x = (box[0] + box[2]) // 2
                        center_y = (box[1] + box[3]) // 2
                        logger_instance.info(f"  路标 {i}: 类型 - {name}, 匹配分数 - {score:.3f}, 中心点坐标 - ({center_x}, {center_y})")

                # 3. 绘制检测框和保存图像
                debug_img = img_bgr.copy()

                for result in results:
                    name = result['name']
                    box = result['box']
                    score = result['score']
                    x1, y1, x2, y2 = box
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2

                    logger_instance.debug(f"正在处理 {name} 路标，中心点坐标为 ({center_x}, {center_y})，冷却剩余时间: {self.detection_cooldown - (current_time - self.last_detection_time):.1f} 秒")

                    # 绘制框和标签
                    cv2.rectangle(debug_img, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), (0, 255, 0), 2)
                    cv2.putText(debug_img, f"{name}:{score:.2f}", (int(box[0]), int(box[1])-10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                # 保存图像（无论是否检测到路标）
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                cv2.imwrite(
                    f"{self.capture_dir}/frame_{timestamp}_detected.jpg" if results 
                    else f"{self.capture_dir}/frame_{timestamp}_no_result.jpg",
                    debug_img
                )
                logger_instance.debug(f"图像已保存为 {self.capture_dir}/frame_{timestamp}_{'detected' if results else 'no_result'}.jpg")

                # 4. 动作触发逻辑
                for result in results:
                    name = result['name']
                    box = result['box']
                    score = result['score']
                    x1, y1, x2, y2 = box
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2

                    if current_time - self.last_detection_time >= self.detection_cooldown:
                        if name == 'left' and 500 < center_x < 800 and center_y >= 360:
                            logger_instance.info(f"★ 满足左转条件，中心点坐标: ({center_x}, {center_y})，执行左转动作")
                            self.ctrl.execute(TurnLeftInPlace())
                            self.last_detection_time = current_time
                            break
                        elif name == 'right' and 500 < center_x < 800 and center_y >= 360:
                            logger_instance.info(f"★ 满足右转条件，中心点坐标: ({center_x}, {center_y})，执行右转动作")
                            self.ctrl.execute(TurnRightInPlace())
                            self.last_detection_time = current_time
                            break
                        elif name == 'turnaround' and 500 < center_x < 800 and center_y >= 360:
                            logger_instance.info(f"★ 满足掉头条件，中心点坐标: ({center_x}, {center_y})，执行掉头动作")
                            self.ctrl.execute(TurnAround())
                            self.last_detection_time = current_time
                            break

                # 5. 暂停处理
                if self.pause_sign.value:
                    self.ctrl.execute(Stop())
                    time.sleep(0.1)
                    continue

            except Exception as e:
                logger_instance.error(f'主循环中出现错误: {str(e)}')
                time.sleep(0.5)

        # 清理资源
        logger_instance.info('退出循环，停止控制器并清理资源')
        self.ctrl.execute(Stop())