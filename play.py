import arc_agi
from arcengine import GameAction
from human_player.config import get_render_mode

arc = arc_agi.Arcade()
env = arc.make("ls20", render_mode=get_render_mode())
# env = arc.make("ls20")

# See available actions
print(env.action_space)

# Take an action
obs = env.step(GameAction.ACTION1)

# Check your scorecard
print(arc.get_scorecard())