import os
import subprocess

SIMULATION_RUNNER_PATH = r"F:\python\Ai_agent\agent_project\simulation\simulation_runner.py"
subprocess.Popen(["python", SIMULATION_RUNNER_PATH], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
