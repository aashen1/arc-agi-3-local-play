import arc_agi
from arc_agi import OperationMode
from arcengine import GameAction

arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE)
env = arc.make("ls20")

print(env.action_space)

obs = env.step(GameAction.ACTION1)

if obs:
    print(f"State: {obs.state}")
