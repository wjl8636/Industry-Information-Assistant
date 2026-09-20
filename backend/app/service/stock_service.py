# Copyright © 2026 深圳市深维智见教育科技有限公司 版权所有
# 未经授权，禁止转售或仿制。

"""股票资讯服务 - 聚合数据股票API"""
import os
import httpx
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class StockMarket(Enum):
    """股票市场"""
    SHANGHAI = "sh"  # 上海证券交易所
    SHENZHEN = "sz"  # 深圳证券交易所


@dataclass
class StockInfo:
    """股票信息"""
    gid: str  # 股票编号
    name: str  # 股票名称
    nowPri: str  # 当前价格
    increase: str  # 涨跌额
    increPer: str  # 涨跌幅
    todayStartPri: str  # 今日开盘价
    yestodEndPri: str  # 昨日收盘价
    todayMax: str  # 今日最高价
    todayMin: str  # 今日最低价
    traAmount: str  # 成交量
    traNumber: str  # 成交额

    @classmethod
    def from_dict(cls, data: Dict) -> "StockInfo":
        return cls(
            gid=data.get("gid", ""),
            name=data.get("name", ""),
            nowPri=data.get("nowPri", ""),
            increase=data.get("increase", ""),
            increPer=data.get("increPer", ""),
            todayStartPri=data.get("todayStartPri", ""),
            yestodEndPri=data.get("yestodEndPri", ""),
            todayMax=data.get("todayMax", ""),
            todayMin=data.get("todayMin", ""),
            traAmount=data.get("traAmount", ""),
            traNumber=data.get("traNumber", ""),
        )

    def to_dict(self) -> Dict:
        return {
            "gid": self.gid,
            "name": self.name,
            "nowPri": self.nowPri,
            "increase": self.increase,
            "increPer": self.increPer,
            "todayStartPri": self.todayStartPri,
            "yestodEndPri": self.yestodEndPri,
            "todayMax": self.todayMax,
            "todayMin": self.todayMin,
            "traAmount": self.traAmount,
            "traNumber": self.traNumber,
        }

    def format_display(self) -> str:
        """格式化显示"""
        return f"""
📈 {self.name} ({self.gid})
━━━━━━━━━━━━━━━━━━━━━━━━
当前价格: ¥{self.nowPri}
涨跌额: {self.increase} ({self.increPer})
今开: ¥{self.todayStartPri} | 昨收: ¥{self.yestodEndPri}
最高: ¥{self.todayMax} | 最低: ¥{self.todayMin}
成交量: {self.traAmount} | 成交额: ¥{self.traNumber}
"""


class StockService:
    """股票资讯服务"""

    # 聚合数据股票API
    BASE_URL = "http://web.juhe.cn/finance/stock/hs"
    SHANGHAI_ALL_URL = "http://web.juhe.cn/finance/stock/shall"
    SHENZHEN_ALL_URL = "http://web.juhe.cn/finance/stock/szall"

    def __init__(self):
        self.api_key = os.getenv("JUHE_STOCK_API_KEY", "")
        if not self.api_key:
            print("警告: JUHE_STOCK_API_KEY 环境变量未设置")

    async def get_stock_by_code(self, stock_code: str) -> Dict[str, Any]:
        """
        根据股票代码查询股票信息

        Args:
            stock_code: 股票代码，如 "sh601009" (上证) 或 "sz000001" (深证)
                       也可以不带前缀，如 "601009"，会自动判断市场

        Returns:
            包含股票信息的字典
        """
        # 处理股票代码
        gid = self._normalize_stock_code(stock_code)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "gid": gid,
                        "key": self.api_key
                    }
                )
                response.raise_for_status()
                data = response.json()

                if data.get("resultcode") == "200":
                    result = data.get("result", [])
                    if result and len(result) > 0:
                        stock_data = result[0].get("data", {})
                        stock_info = StockInfo.from_dict(stock_data)
                        return {
                            "success": True,
                            "data": stock_info.to_dict(),
                            "display": stock_info.format_display()
                        }

                return {
                    "success": False,
                    "error": data.get("reason", "查询失败"),
                    "data": None
                }

        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "请求超时",
                "data": None
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

    async def search_stock(self, keyword: str) -> Dict[str, Any]:
        """
        搜索股票（暂时通过遍历方式，后续可接入搜索API）

        Args:
            keyword: 股票名称或代码关键词

        Returns:
            匹配的股票列表
        """
        # 如果看起来像股票代码，直接查询
        if keyword.isdigit() or keyword.startswith(("sh", "sz", "SH", "SZ")):
            result = await self.get_stock_by_code(keyword)
            if result["success"]:
                return {
                    "success": True,
                    "results": [result["data"]],
                    "count": 1
                }

        # 否则尝试按代码查询（兼容纯数字代码）
        for prefix in ["sh", "sz"]:
            if keyword.isdigit():
                result = await self.get_stock_by_code(f"{prefix}{keyword}")
                if result["success"]:
                    return {
                        "success": True,
                        "results": [result["data"]],
                        "count": 1
                    }

        return {
            "success": False,
            "error": "未找到匹配的股票，请提供准确的股票代码（如 sh601009 或 sz000001）",
            "results": []
        }

    async def get_market_stocks(self, market: str = "shanghai", page: int = 1) -> Dict[str, Any]:
        """
        获取市场股票列表

        Args:
            market: 市场类型，"shanghai" 或 "shenzhen"
            page: 页码

        Returns:
            股票列表
        """
        url = self.SHANGHAI_ALL_URL if market == "shanghai" else self.SHENZHEN_ALL_URL

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    url,
                    params={
                        "key": self.api_key,
                        "page": page
                    }
                )
                response.raise_for_status()
                data = response.json()

                if data.get("resultcode") == "200":
                    result = data.get("result", {})
                    stocks = result.get("data", [])

                    return {
                        "success": True,
                        "market": market,
                        "page": page,
                        "total_count": result.get("totalCount", 0),
                        "stocks": [StockInfo.from_dict(s.get("data", {})).to_dict() for s in stocks[:20]]  # 限制返回数量
                    }

                return {
                    "success": False,
                    "error": data.get("reason", "查询失败"),
                    "stocks": []
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "stocks": []
            }

    def _normalize_stock_code(self, code: str) -> str:
        """
        标准化股票代码

        Args:
            code: 原始股票代码

        Returns:
            标准化后的代码（如 sh601009）
        """
        code = code.strip().lower()

        # 如果已经有市场前缀
        if code.startswith(("sh", "sz")):
            return code

        # 根据股票代码判断市场
        if code.isdigit():
            # 6开头是上海，0/3开头是深圳
            if code.startswith("6"):
                return f"sh{code}"
            elif code.startswith(("0", "3")):
                return f"sz{code}"

        # 默认返回原始代码
        return code


# 单例
_stock_service: Optional[StockService] = None


def get_stock_service() -> StockService:
    """获取股票服务单例"""
    global _stock_service
    if _stock_service is None:
        _stock_service = StockService()
    return _stock_service
