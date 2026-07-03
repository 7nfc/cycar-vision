import cv2
import numpy as np
import os

class TemplateMatcher:
    def __init__(self, template_dir, match_threshold, nms_threshold=0.4):
        self.template_dir = template_dir
        self.match_threshold = match_threshold
        self.nms_threshold = nms_threshold
        self.templates = self._load_templates()
        
    def _load_templates(self):
        templates = {}
        for filename in os.listdir(self.template_dir):
            if filename.endswith(('.jpg', '.png')):
                name = filename.split('_')[0]
                path = os.path.join(self.template_dir, filename)# 从文件名提取类别名（如"left_1.png" → "left"）
                template = cv2.imread(path, cv2.IMREAD_COLOR)  # 先加载为彩色图（方便缩小）
                if template is not None:
                    # 缩小为1/4
                    template = cv2.resize(template, (0, 0), fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
                    # 转为灰度图
                    template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                    # 高斯模糊
                    template = cv2.GaussianBlur(template, (3, 3), 0)
                    
                    if name not in templates:
                        templates[name] = []
                    templates[name].append(template)
        return templates
    
    def infer(self, frame):
        """执行模板匹配"""
        results = []
        # 缩小为1/4
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
        # 转为灰度
        gray_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        # 高斯模糊
        gray_frame = cv2.GaussianBlur(gray_frame, (3, 3), 0)
        
        for name, template_list in self.templates.items(): # 遍历所有类别（如"left"、"right"）
            for template in template_list: # 遍历该类别的所有模板
                h, w = template.shape
                # 计算模板与目标图像的相似度
                res = cv2.matchTemplate(gray_frame, template, cv2.TM_CCOEFF_NORMED)
                loc = np.where(res >= self.match_threshold) # 找出高于阈值的匹配位置
                
                # 生成边界框（注意坐标需放大4倍，因图像被缩小过）
                boxes = []
                for pt in zip(*loc[::-1]):
                    # 坐标需要放大4倍（因为图像缩小了1/4）
                    x1, y1 = pt[0] * 4, pt[1] * 4
                    x2, y2 = (pt[0] + w) * 4, (pt[1] + h) * 4
                    score = res[pt[1], pt[0]]
                    boxes.append([x1, y1, x2, y2, score])
                # 应用非极大值抑制
                boxes = self.nms(np.array(boxes))
                
                for box in boxes:
                    results.append({
                        'name': name,
                        'box': box[:4],
                        'score': box[4]
                    })
        
        return results
    
    def nms(self, boxes):#抑制（删除）与该目标重叠度过高的其他候选目标（认为它们是重复检测）。
        if len(boxes) == 0:
            return []
        
        # 提取坐标和得分
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        scores = boxes[:, 4]
        
        # 计算框面积
        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        
        # 按得分降序排序
        order = scores.argsort()[::-1]
        
        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i) # 保留得分最高的框
            
            # 计算与剩余框的重叠率（IoU）
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            
            w = np.maximum(0.0, xx2 - xx1 + 1)
            h = np.maximum(0.0, yy2 - yy1 + 1)
            overlap = (w * h) / areas[order[1:]] # IoU = 重叠面积 / 并集面积
            
            # 保留重叠率低于阈值的框
            inds = np.where(overlap <= self.nms_threshold)[0]
            order = order[inds + 1]
        
        return boxes[keep]