try:
    from ompl import util as ou
    from ompl import base as ob
    from ompl import geometric as og
except ImportError:
    # if the ompl module is not in the PYTHONPATH assume it is installed in a
    # subdirectory of the parent directory called "py-bindings."
    from os.path import abspath, dirname, join
    import sys
    sys.path.insert(0, join(dirname(dirname(abspath(__file__))), 'ompl/py-bindings'))
    # sys.path.insert(0, join(dirname(abspath(__file__)), '../whole-body-motion-planning/src/ompl/py-bindings'))
    print(sys.path)
    from ompl import util as ou
    from ompl import base as ob
    from ompl import geometric as og
import pybullet as p
# import utils
import utils.ompl_utils as utils
import time
from itertools import product
import copy
from Robot import Robot

INTERPOLATE_NUM = 1000
DEFAULT_PLANNING_TIME = 20.0
SAMPLING_DISTANCE = 0.05

class PbOMPLRobot(Robot):
    '''
    To use with Pb_OMPL. You need to construct a instance of this class and pass to PbOMPL.

    Note:
    This parent class by default assumes that all joints are acutated and should be planned. If this is not your desired
    behaviour, please write your own inheritated class that overrides respective functionalities.
    '''
    def __init__(self, id_client) -> None:
        super().__init__(id_client)
        # Public attributes


        # prune fixed joints
        self.joint_bounds = []



    def _is_not_fixed(self, joint_idx):
        joint_info = p.getJointInfo(self.id_robot, joint_idx,physicsClientId=self.id_client)
        return joint_info[2] != p.JOINT_FIXED

    def get_joint_bounds(self):
        '''
        Get joint bounds.
        By default, read from pybullet
        '''
        # for i, joint_id in enumerate(self.joint_idx):
        #     joint_info = p.getJointInfo(self.id_robot, joint_id)
        #     low = joint_info[8] # low bounds
        #     high = joint_info[9] # high bounds
        #     if low < high:
        #         self.joint_bounds.append([low, high])
        # print("Joint bounds: {}".format(self.joint_bounds))

        for i, joint_id in enumerate(self.ids_avail_joints):
            joint_info = p.getJointInfo(self.id_robot, joint_id,physicsClientId=self.id_client)
            low = joint_info[8]  # low bounds
            high = joint_info[9] # high bounds
            if low < high:
                self.joint_bounds.append([low, high])
                print(f"Joint {joint_id} bounds: {low} {high}")



        return self.joint_bounds

    def get_cur_state(self):
        return copy.deepcopy(self.state)

    def set_state(self, state):
        '''
        Set robot state.
        To faciliate collision checking
        Args:
            state: list[Float], joint values of robot
        '''
        # self._set_joint_positions(self.joint_idx, state)
        self.set_joints_states(state)
        self.state = state

    def reset(self):
        '''
        Reset robot state
        Args:
            state: list[Float], joint values of robot
        '''
        state = [0] * self.num_avail_joints
        # self._set_joint_positions(self.joint_idx, state)
        self.set_joints_states(state)
        self.state = state

    def _set_joint_positions(self, joints, positions):
        for joint, value in zip(joints, positions):
            p.resetJointState(self.id_robot, joint, value, targetVelocity=0,physicsClientId=self.id_client)

class PbStateSpace(ob.RealVectorStateSpace):
    def __init__(self, num_dim) -> None:
        super().__init__(num_dim)
        self.num_dim = num_dim
        self.state_sampler = None

    def allocStateSampler(self):
        '''
        This will be called by the internal OMPL planner
        '''
        # WARN: This will cause problems if the underlying planner is multi-threaded!!!
        if self.state_sampler:
            return self.state_sampler

        # when ompl planner calls this, we will return our sampler
        return self.allocDefaultStateSampler()

    def set_state_sampler(self, state_sampler):
        '''
        Optional, Set custom state sampler.
        '''
        self.state_sampler = state_sampler

class PbOMPL():
    def __init__(self, robot:PbOMPLRobot, obstacles = []) -> None:
        '''
        Args
            robot: A PbOMPLRobot instance.
            obstacles: list of obstacle ids. Optional.
        '''
        self.robot = robot
        self.robot_id = robot.id_robot
        self.obstacles = obstacles
        print(self.obstacles)

        self.space = PbStateSpace(robot.num_avail_joints)

        bounds = ob.RealVectorBounds(robot.num_avail_joints)
        joint_bounds = self.robot.get_joint_bounds()
        for i, bound in enumerate(joint_bounds):
            bounds.setLow(i, bound[0])
            bounds.setHigh(i, bound[1])
        self.space.setBounds(bounds)

        self.ss = og.SimpleSetup(self.space)
        self.ss.setStateValidityChecker(ob.StateValidityCheckerFn(self.is_state_valid))
        self.si = self.ss.getSpaceInformation()
        self.si.setStateValidityCheckingResolution(SAMPLING_DISTANCE)
        # self.collision_fn = pb_utils.get_collision_fn(self.robot_id, self.robot.joint_idx, self.obstacles, [], True, set(),
        #                                                 custom_limits={}, max_distance=0, allow_collision_links=[])
        self.check_link_pairs = []
        self.set_obstacles(obstacles)
        self.set_planner("RRT") # RRT by default

    def set_obstacles(self, obstacles):
        self.obstacles = obstacles

        # update collision detection
        self.setup_collision_detection(self.robot, self.obstacles)

    def add_obstacles(self, obstacle_id):
        self.obstacles.append(obstacle_id)

    def remove_obstacles(self, obstacle_id):
        self.obstacles.remove(obstacle_id)

    def is_state_valid(self, state):
        # satisfy bounds TODO
        # Should be unecessary if joint bounds is properly set

        # check self-collision
        self.robot.set_state(self.state_to_list(state))
        for link1, link2 in self.check_link_pairs:
            if utils.pairwise_link_collision(self.robot_id, link1, self.robot_id, link2,physicsClientId=self.robot.id_client):
                # print(get_body_name(body), get_link_name(body, link1), get_link_name(body, link2))
                return False

        # check collision against environment
        for body1, body2 in self.check_body_pairs:
            if utils.pairwise_collision(body1, body2,physicsClientId=self.robot.id_client):
                # print('body collision', body1, body2)
                # print(get_body_name(body1), get_body_name(body2))
                return False
        return True

    def setup_collision_detection(self, robot:PbOMPLRobot, obstacles, self_collisions = True, allow_collision_links = []):
        self.check_link_pairs = utils.get_self_link_pairs(robot.id_robot, robot.ids_avail_joints,physicsClientId=self.robot.id_client) if self_collisions else []
        moving_links = frozenset(
            [item for item in utils.get_moving_links(robot.id_robot, robot.ids_avail_joints,physicsClientId=self.robot.id_client) if not item in allow_collision_links])
        moving_bodies = [(robot.id_robot, moving_links)]
        self.check_body_pairs = list(product(moving_bodies, obstacles))

    def set_planner(self, planner_name):
        '''
        Note: Add your planner here!!
        '''
        if planner_name == "PRM":
            self.planner = og.PRM(self.ss.getSpaceInformation())
        elif planner_name == "RRT":
            self.planner = og.RRT(self.ss.getSpaceInformation())
            self.planner.setRange(0.5)
        elif planner_name == "RRTConnect":
            self.planner = og.RRTConnect(self.ss.getSpaceInformation())
            self.planner.setRange(0.005)
        elif planner_name == "RRTstar":
            self.planner = og.RRTstar(self.ss.getSpaceInformation())
        elif planner_name == "EST":
            self.planner = og.EST(self.ss.getSpaceInformation())
        elif planner_name == "FMT":
            self.planner = og.FMT(self.ss.getSpaceInformation())
        elif planner_name == "BITstar":
            self.planner = og.BITstar(self.ss.getSpaceInformation())
        else:
            print("{} not recognized, please add it first".format(planner_name))
            return


        self.ss.setPlanner(self.planner)

    # def plan_start_goal(self, start, goal, allowed_time = DEFAULT_PLANNING_TIME):
    #     '''
    #     plan a path to gaol from the given robot start state
    #     '''
    #     print("start_planning")
    #     print(self.planner.params())
    #
    #     orig_robot_state = self.robot.get_cur_state()
    #
    #     # set the start and goal states;
    #     s = ob.State(self.space)
    #     g = ob.State(self.space)
    #     for i in range(len(start)):
    #         s[i] = start[i]
    #         g[i] = goal[i]
    #
    #     self.ss.setStartAndGoalStates(s, g)
    #
    #     # attempt to solve the problem within allowed planning time
    #     solved = self.ss.solve(allowed_time)
    #     res = False
    #     sol_path_list = []
    #     if solved:
    #         print("Found solution: interpolating into {} segments".format(INTERPOLATE_NUM))
    #         # print the path to screen
    #         sol_path_geometric = self.ss.getSolutionPath()
    #         print('solution path point length: {}'.format(sol_path_geometric.getStateCount()))
    #         sol_path_geometric.interpolate(INTERPOLATE_NUM)
    #         sol_path_states = sol_path_geometric.getStates()
    #         sol_path_list = [self.state_to_list(state) for state in sol_path_states]
    #         # print(len(sol_path_list))
    #         # print(sol_path_list)
    #         for i,sol_path in enumerate(sol_path_list):
    #             # self.is_state_valid(sol_path)
    #             if not self.is_state_valid(sol_path):
    #                 print("Invalid path:", sol_path,"No. of states: ", i)
    #         res = True
    #     else:
    #         print("No solution found")
    #
    #     # reset robot state
    #     self.robot.set_state(orig_robot_state)
    #     return res, sol_path_list


    def plan_start_goal(self, start, goal, allowed_time = DEFAULT_PLANNING_TIME,ret_all=False):
        '''
        plan a path to gaol from the given robot start state
        '''
        ori_path = []
        print("start_planning")
        print(self.planner.params())

        orig_robot_state = self.robot.get_cur_state()

        # set the start and goal states;
        s = ob.State(self.space)
        g = ob.State(self.space)
        for i in range(len(start)):
            s[i] = start[i]
            g[i] = goal[i]

        self.ss.setStartAndGoalStates(s, g)

        # attempt to solve the problem within allowed planning time
        solved = self.ss.solve(allowed_time)
        is_exact = str(solved) == "Exact solution"
        is_approx = str(solved) == "Approximate solution"
        res = False
        sol_path_list = []
        if is_exact:
            print("Found solution: interpolating into {} segments".format(INTERPOLATE_NUM))
            # print the path to screen
            sol_path_geometric = self.ss.getSolutionPath()
            ori_path = [self.state_to_list(state) for state in sol_path_geometric.getStates()]
            print('solution path point length: {}'.format(sol_path_geometric.getStateCount()))
            sol_path_geometric.interpolate(INTERPOLATE_NUM)
            sol_path_states = sol_path_geometric.getStates()
            sol_path_list = [self.state_to_list(state) for state in sol_path_states]
            # print(len(sol_path_list))
            # print(sol_path_list)
            for i,sol_path in enumerate(sol_path_list):
                # self.is_state_valid(sol_path)
                if not self.is_state_valid(sol_path):
                    print("Invalid path:", sol_path,"No. of states: ", i)
            res = True
        else:
            print("No solution found")

        # reset robot state
        self.robot.set_state(orig_robot_state)
        if ret_all:
            si = self.ss.getSpaceInformation()  # SpaceInformation
            pd = ob.PlannerData(si)
            self.ss.getPlannerData(pd)
            solved_time = self.ss.getLastPlanComputationTime()

            return is_exact, ori_path, sol_path_list, solved_time, pd.numVertices()

        return res, sol_path_list

    def plan(self, goal, allowed_time = DEFAULT_PLANNING_TIME):
        '''
        plan a path to gaol from current robot state
        '''
        start = self.robot.get_cur_state()
        return self.plan_start_goal(start, goal, allowed_time=allowed_time)

    def execute(self, path, dynamics=False):
        '''
        Execute a planned plan. Will visualize in pybullet.
        Args:
            path: list[state], a list of state
            dynamics: allow dynamic simulation. If dynamics is false, this API will use robot.set_state(),
                      meaning that the simulator will simply reset robot's state WITHOUT any dynamics simulation. Since the
                      path is collision free, this is somewhat acceptable.
        '''
        for q in path:
            if dynamics:
                for i in range(self.robot.num_avail_joints):
                    p.setJointMotorControl2(self.robot.id_robot, i, p.POSITION_CONTROL, q[i],force=10000 * 240.,
                                    positionGain = 0.5,  # KP
                                    velocityGain = 1.5,  # KD
                                            physicsClientId=self.robot.id_client

                                            )
            else:
                self.robot.set_state(q)
            p.stepSimulation(physicsClientId=self.robot.id_client)
            time.sleep(1/240.)



    # -------------
    # Configurations
    # ------------

    def set_state_sampler(self, state_sampler):
        self.space.set_state_sampler(state_sampler)

    # -------------
    # Util
    # ------------

    def state_to_list(self, state):
        return [state[i] for i in range(self.robot.num_avail_joints)]