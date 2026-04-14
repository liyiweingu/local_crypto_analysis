from pydantic import BaseModel
from typing import Optional, Dict

class Coin(BaseModel):
    symbol: str
    name: str

class Indicator(BaseModel):
    name: str
    calc_method: str
    description: str

class NewsSource(BaseModel):
    name: str
    url: str

class PromptsUpdate(BaseModel):
    prompts: Dict[str, str]

class AIConfigUpdate(BaseModel):
    configs: Dict[str, str]
