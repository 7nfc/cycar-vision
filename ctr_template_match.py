import os
from multiprocessing import Process, Queue,shared_memory
import time
from src.scenes import Helper_template_match
from src.utils import getKey, log, CameraBroadcaster, CAMERA_INFO, Controller
from src.actions import Stop

def main():
    # 初始化消息队列和控制器
    msg_queue = Queue()
    controller = Controller()
    
    # 创建并启动摄像头进程
    camera = CameraBroadcaster(CAMERA_INFO)
    camera_process = Process(target=camera.run)
    camera_process.start()
    
    # 等待相机初始化（添加延迟）
    time.sleep(2.0)  # 等待2秒让相机完成初始化

     # 使用固定共享内存名称
    shared_mem_name = 'cycar_camera_frame'
    try:
        # 验证共享内存是否可用
        temp_shm = shared_memory.SharedMemory(name=shared_mem_name, create=False)
        temp_shm.close()
        print(f"使用共享内存: {shared_mem_name}")
    except FileNotFoundError:
        raise RuntimeError("相机未能初始化共享内存")
    
    # 创建并启动模板匹配进程
    template_matcher = Helper_template_match(shared_mem_name, CAMERA_INFO, msg_queue)
    process = Process(target=template_matcher.loop)
    process.start()
    
    log.info("模板匹配控制器已启动。按ESC键退出。")
    
    try:
        while True:
            key = getKey()
            if key == 'esc':
                log.info("按下ESC,停止进程...")
                break
            msg_queue.put(key)
    except KeyboardInterrupt:
        log.info("收到键盘中断，停止...")
    except Exception as e:
        log.error(f"主循环中出错: {str(e)}")
    finally:
         # 终止进程
        process.terminate()
        camera_process.terminate()

        # 确保进程已加入
        process.join()
        camera_process.join()

        # 停止车辆
        controller.execute(Stop())

        # 清理共享内存
        try:
            shm = shared_memory.SharedMemory(name='cycar_camera_frame', create=False)
            shm.close()
            shm.unlink()
            log.info("共享内存已清理")
        except FileNotFoundError:
            pass
    
        log.info("进程已停止，车辆已停下。")
        
if __name__ == '__main__':
    main()