import time
import numpy as np
import cv2
from src.scenes.lane_following_threshold import extract_yellow_region, getEdgeImg, roi_mask, process_image, getRLaneLine

def get_x0(img_path):
    """计算目标位置X₀"""
    # 读取图像
    img = cv2.imread(img_path)
    if img is None:
        print(f"Error: Could not read image at {img_path}")
        return
    
    print(f"Original image size: {img.shape}")
    
    
    # 缩放图像到1/4大小
    small_img = cv2.resize(img, (0, 0), fx=0.25, fy=0.25)
    rows, cols = small_img.shape[:2]
    print(f"Scaled image size: {small_img.shape}")
    
    # 1. 提取黄色车道线
    binary = extract_yellow_region(small_img)
    
    # 2. 获取边缘图像
    edges = getEdgeImg(binary)
    
    # 3. 设置ROI区域 (图像下半部分的3/4区域)
    corner_points = np.array([[
        [0, rows], 
        [0, int(rows*0.25)], 
        [cols, int(rows*0.25)], 
        [cols, rows]
    ]])
    
    # 4. 应用ROI掩膜
    roi_edges = roi_mask(edges, corner_points)
    
    # 5. 处理图像，保留右侧车道线
    processed_img = process_image(roi_edges)
    
   # 6. 获取右侧车道线（不缩放坐标）
    slope, intercept = getRLaneLine(processed_img)  # 关键修改：scale_factor=1
    
    if slope is not None and intercept is not None:
        # 计算右侧车道线与图像底部的交点 (y=rows-1)
        x0_small = (rows-1 - intercept) / slope  # 小图坐标系中的x0
        
        # 缩放回原图尺寸
        x0 = x0_small * 4  # 原图宽度是小图的4倍
        
        print(f"slope (small image): {slope}")
        print(f"intercept (small image): {intercept}")
        print(f"x0 (small image): {x0_small}")
        print(f"Final x0 (original image): {int(x0)}")
        
        # 可视化（在小图坐标系中绘制）
        vis_img = small_img.copy()
        cv2.polylines(vis_img, [corner_points], isClosed=True, color=(0, 255, 0), thickness=1)
        y1 = int(rows*0.25)
        y2 = rows-1
        x1 = int((y1 - intercept) / slope)
        x2 = int((y2 - intercept) / slope)
        cv2.line(vis_img, (x1, y1), (x2, y2), (0, 0, 255), 2)
        cv2.circle(vis_img, (int(x0_small), rows-1), 5, (255, 0, 0), -1)
        
        cv2.imshow("Detection Result (Small Image)", vis_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        
        return x0
    else:
        print("未检测到车道线，请检查图像或调整参数")
        return None

if __name__ == "__main__":
    img_path = '/root/cyCar/capture/lane.jpg'
    get_x0(img_path)