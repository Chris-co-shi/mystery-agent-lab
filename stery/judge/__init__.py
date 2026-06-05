# stery/judge/__init__.py

"""
Judge package.

不要在这里主动 import RuleJudge / ScoringConfig。

原因：
当外部导入 stery.judge.scoring 时，Python 会先执行 stery.judge.__init__。
如果 __init__ 又导入 rule_judge，而 rule_judge 又导入 scoring，
就容易形成循环导入。

请在使用处直接导入具体模块：

from stery.judge.rule_judge import RuleJudge
from stery.judge.scoring import ScoringConfig
"""