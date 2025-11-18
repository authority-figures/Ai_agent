import pyrealsense2 as rs
import cv2

import numpy as np
class RealSenseRGB:
    def __init__(self):
        self.pipeline = rs.pipeline()
        self.config = rs.config()
        self.started = False

    def start(self):
        """启动相机流"""

        # 获取设备的流配置列表
        pipeline_wrapper = rs.pipeline_wrapper(self.pipeline)
        pipeline_profile = self.config.resolve(pipeline_wrapper)

        color_sensor = pipeline_profile.get_device().query_sensors()[1]  # color sensor
        color_sensor.set_option(rs.option.enable_auto_exposure, False)
        color_sensor.set_option(rs.option.exposure,300)  # 单位：微秒
        color_sensor.set_option(rs.option.gain, 0)  # 范围一般是 0~255
        # 设置锐化、对比度等
        color_sensor.set_option(rs.option.sharpness, 50)
        color_sensor.set_option(rs.option.contrast, 100)
        color_sensor.set_option(rs.option.saturation,0)



        self.config.enable_stream(rs.stream.color, 1920, 1080, rs.format.bgr8, 30)
        self.pipeline.start(self.config)
        self.started = True
        print("[INFO] RealSense 相机已启动。")


    def get_intrinsics(self):
        """获取相机内参"""
        if not self.started:
            raise RuntimeError("请先调用 start() 方法启动相机。")

        frames = self.pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        if not color_frame:
            print("[WARNING] 无法获取颜色帧。")
            return None
        color_stream_profile = color_frame.get_profile().as_video_stream_profile()
        intrinsics = color_stream_profile.get_intrinsics()

        # 内参矩阵格式输出
        K = np.array([
            [intrinsics.fx, 0, intrinsics.ppx],
            [0, intrinsics.fy, intrinsics.ppy],
            [0, 0, 1]
        ])
        D = np.array(intrinsics.coeffs)

        return K,D


    def get_rgb_frame(self):
        """获取一帧 RGB 图像"""
        if not self.started:
            raise RuntimeError("请先调用 start() 方法启动相机。")

        frames = self.pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        if not color_frame:
            print("[WARNING] 无法获取颜色帧。")
            return None
        return np.asanyarray(color_frame.get_data())

    def release(self):
        """释放资源"""
        if self.started:
            self.pipeline.stop()
            self.started = False
            print("[INFO] RealSense 相机已关闭。")

    def detect_cirle(self,image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
        flags = cv2.CALIB_CB_SYMMETRIC_GRID

        ret, centers = cv2.findCirclesGrid(gray,(7,7), flags=flags)

        if not ret:
            print("[×] 未能在图像中识别圆点标定板")
            return False
        else:
            print(f"[✓] 圆点检测成功！绘制识别结果")
            vis_img = cv2.drawChessboardCorners(image.copy(), (7,7), centers, ret)
            cv2.imshow("Detected Circles Grid", vis_img)
            cv2.waitKey(1)
            return True






if __name__ == "__main__":
    camera = RealSenseRGB()
    camera.start()  # 显式启动

    try:
        while True:
            frame = camera.get_rgb_frame()
            if frame is not None:
                cv2.imshow("RGB", frame)
                camera.detect_cirle(camera.get_rgb_frame())
            if cv2.waitKey(1) & 0xFF == ord('d'):
                camera.detect_cirle(camera.get_rgb_frame())

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()