# Copyright © 2026 深圳市深维智见教育科技有限公司 版权所有
# 未经授权，禁止转售或仿制。

"""
DeepResearch V2.0 - Agents 模块

导出所有专家Agent
"""

from .base import BaseAgent, AgentRegistry
from .architect import ChiefArchitect
from .scout import DeepScout
from .wizard import CodeWizard
from .critic import CriticMaster
from .writer import LeadWriter
from .data_analyst import DataAnalyst

__all__ = [
    'BaseAgent',
    'AgentRegistry',
    'ChiefArchitect',
    'DeepScout',
    'CodeWizard',
    'CriticMaster',
    'LeadWriter',
    'DataAnalyst'
]
