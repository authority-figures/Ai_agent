import time
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ''))
import numpy as np
import pybullet as p
import pybullet_data
from agent_project.simulation.Robot import Robot

id_client = p.connect(p.GUI)
p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 1, shadowMapWorldSize=1, shadowMapIntensity=1, physicsClientId=id_client)
p.setAdditionalSearchPath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../Robot/urdf/'))
# 设置数据搜索路径
p.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=id_client)

planeId = p.loadURDF("plane.urdf")

cam_urdf = "../models/camera/urdf/camera.urdf"
camera = Robot(id_client)
camera.f_print = True
camera.load_urdf(fileName=cam_urdf,basePosition=(0,0,0.1),baseOrientation=p.getQuaternionFromEuler([1.57, 0, 0]),useFixedBase=1)


while True:
    p.stepSimulation()
    time.sleep(1/240.)