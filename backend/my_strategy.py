from collections import deque
import atexit
import json

from backtester.strategy import (
    BaseStrategy,
    Fill,
    MarketState,
    Order,
    Settlement,
    Side,
    Token,
)


class MyStrategy(BaseStrategy):
    def __init__(self, config: dict) -> None:
        self.price_history = deque(maxlen=40)

        self.base_order_size = config["base_order_size"]
        self.min_momentum = config["min_momentum"]
        self.max_token_ask = config["max_token_ask"]
        self.take_profit = config["take_profit"]
        self.stop_loss = config["stop_loss"]
        self.min_time_remaining = config["min_time_remaining"]
        self.max_time_remaining = config["max_time_remaining"]

        self.entry_price: dict[tuple[str, Token], float] = {}

        # Chart telemetry
        self.chart_points: list[dict] = []
        self._chart_every_n_ticks = 10
        self._tick_counter = 0

        atexit.register(self._emit_chart_data)

    def _emit_chart_data(self) -> None:
        if not self.chart_points:
            return

        print("CHART_DATA_START")
        print(json.dumps(self.chart_points))
        print("CHART_DATA_END")

    def _record_chart_point(self, state: MarketState) -> None:
        self._tick_counter += 1
        if self._tick_counter % self._chart_every_n_ticks != 0:
            return

        time_label = state.timestamp_utc
        if "T" in time_label:
            time_label = time_label.split("T")[1].replace("Z", "")

        self.chart_points.append(
            {
                "time": time_label,
                "btc_price": round(float(state.btc_mid), 2),
                "portfolio_value": round(float(state.total_portfolio_value), 2),
            }
        )

    def _is_btc_5m(self, slug: str, interval: str) -> bool:
        s = slug.lower()
        return interval == "5m" and (s.startswith("btc-") or s.startswith("bitcoin-"))

    def on_tick(self, state: MarketState) -> list[Order]:
        orders: list[Order] = []

        self._record_chart_point(state)

        if state.btc_mid > 0:
            self.price_history.append(state.btc_mid)

        if len(self.price_history) < 10:
            return orders

        start_price = self.price_history[0]
        if start_price <= 0:
            return orders

        momentum = (self.price_history[-1] - start_price) / start_price

        for slug, pos in state.positions.items():
            market = state.markets.get(slug)
            if market is None or not self._is_btc_5m(slug, market.interval):
                continue

            if pos.yes_shares > 0:
                entry = self.entry_price.get((slug, Token.YES))
                if entry is not None and entry > 0 and market.yes_bid > 0:
                    pnl_pct = (market.yes_bid - entry) / entry
                    if (
                        pnl_pct >= self.take_profit
                        or pnl_pct <= -self.stop_loss
                        or market.time_remaining_s < self.min_time_remaining
                        or momentum < -self.min_momentum
                    ):
                        orders.append(
                            Order(slug, Token.YES, Side.SELL, pos.yes_shares, market.yes_bid)
                        )

            if pos.no_shares > 0:
                entry = self.entry_price.get((slug, Token.NO))
                if entry is not None and entry > 0 and market.no_bid > 0:
                    pnl_pct = (market.no_bid - entry) / entry
                    if (
                        pnl_pct >= self.take_profit
                        or pnl_pct <= -self.stop_loss
                        or market.time_remaining_s < self.min_time_remaining
                        or momentum > self.min_momentum
                    ):
                        orders.append(
                            Order(slug, Token.NO, Side.SELL, pos.no_shares, market.no_bid)
                        )

        open_positions = sum(
            1 for p in state.positions.values()
            if p.yes_shares > 0 or p.no_shares > 0
        )
        if open_positions > 0:
            return orders

        for slug, market in state.markets.items():
            if not self._is_btc_5m(slug, market.interval):
                continue

            if not (self.min_time_remaining <= market.time_remaining_s <= self.max_time_remaining):
                continue

            if market.yes_ask <= 0 or market.no_ask <= 0:
                continue

            if momentum > self.min_momentum and market.yes_ask <= self.max_token_ask:
                cost = self.base_order_size * market.yes_ask
                if state.cash >= cost:
                    self.entry_price[(slug, Token.YES)] = market.yes_ask
                    return [Order(slug, Token.YES, Side.BUY, self.base_order_size, market.yes_ask)]

            if momentum < -self.min_momentum and market.no_ask <= self.max_token_ask:
                cost = self.base_order_size * market.no_ask
                if state.cash >= cost:
                    self.entry_price[(slug, Token.NO)] = market.no_ask
                    return [Order(slug, Token.NO, Side.BUY, self.base_order_size, market.no_ask)]

        return orders

    def on_fill(self, fill: Fill) -> None:
        pass

    def on_settlement(self, settlement: Settlement) -> None:
        self.entry_price.pop((settlement.market_slug, Token.YES), None)
        self.entry_price.pop((settlement.market_slug, Token.NO), None)