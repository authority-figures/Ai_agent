import os.path as osp
import pybullet as p
import math
import sys
import pybullet_data
sys.path.insert(0, osp.join(osp.dirname(osp.abspath(__file__)), '../'))

from agent_project.simulation import pb_ompl
from agent_project.simulation.Robot import Robot

class BoxDemo():
    def __init__(self):
        self.obstacles = []

        physics_client = p.connect(p.GUI)
        p.setGravity(0, 0, -9.8)
        p.setTimeStep(1./240.)

        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")

        # load robot
        urdf_path = r"../models/jaka_description/urdf/jaka_minicobo.urdf"
        robot = pb_ompl.PbOMPLRobot(physics_client)
        robot.f_print = True
        robot.load_urdf(fileName=urdf_path, basePosition=(0,0,0), baseOrientation=(0,0,0,1),
                        useFixedBase=1,
                        flags=p.URDF_USE_SELF_COLLISION,
                        )
        robot.reset()

        self.robot = robot

        # setup pb_ompl
        self.pb_ompl_interface = pb_ompl.PbOMPL(self.robot, self.obstacles)
        self.pb_ompl_interface.set_planner("BITstar")

        # add obstacles
        self.add_obstacles()

    def clear_obstacles(self):
        for obstacle in self.obstacles:
            p.removeBody(obstacle)

    def add_obstacles(self):
        # add box
        self.add_box([0.8, 0, 0.5], [0.5, 0.5, 0.05])

        # store obstacles
        self.pb_ompl_interface.set_obstacles(self.obstacles)

    def add_box(self, box_pos, half_box_size):
        colBoxId = p.createCollisionShape(p.GEOM_BOX, halfExtents=half_box_size)
        box_id = p.createMultiBody(baseMass=0, baseCollisionShapeIndex=colBoxId, basePosition=box_pos)

        self.obstacles.append(box_id)
        return box_id

    def demo(self):
        start = [0,0,0,-1,0,1.5,]
        goal = [0,-1.5,0,-0.1,0,0.2,]

        self.robot.set_state(start)
        res, path = self.pb_ompl_interface.plan(goal)
        if res:
            self.pb_ompl_interface.execute(path)
        return res, path

if __name__ == '__main__':
    env = BoxDemo()
    env.demo()