from pydantic import BaseModel, Field


class StrategyConfig(BaseModel):
    base_order_size: float = Field(default=20.0, gt=0, le=200)
    min_momentum: float = Field(default=0.0005, gt=0, lt=0.01)
    max_token_ask: float = Field(default=0.65, gt=0, lt=1)
    take_profit: float = Field(default=0.05, gt=0, lt=1)
    stop_loss: float = Field(default=0.03, gt=0, lt=1)
    min_time_remaining: int = Field(default=30, ge=0, le=300)
    max_time_remaining: int = Field(default=240, ge=1, le=300)