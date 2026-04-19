from __future__ import annotations

from collections import deque

from backtester.strategy import (
    BaseStrategy,
    MarketState,
    MarketView,
    Order,
    PositionView,
    Side,
    Token,
)

MAX_SHARES_PER_TOKEN = 500


def _yes_no_shares_and_buy_room(
    position: PositionView | None,
    cap: float = MAX_SHARES_PER_TOKEN,
) -> tuple[float, float, float, float]:
    """yes_shares, no_shares, remaining buy room per side under the share cap."""
    if position is None:
        return (0.0, 0.0, cap, cap)
    ys = position.yes_shares
    ns = position.no_shares
    return (
        ys,
        ns,
        max(0.0, cap - ys),
        max(0.0, cap - ns),
    )


class MyStrategy(BaseStrategy):
    def __init__(self):
        self.price_history = deque(maxlen=31)  # ~30 seconds if called every second

        # Aggressive sizing
        self.base_order_size = 12.0
        self.max_order_size = 40.0

        # Still keep cheap complete-set arb if it appears
        self.arb_threshold = 0.99
        self.arb_order_size = 4.0

    def in_scope(self, slug: str, market: MarketView) -> bool:
        if market.interval != "5m":
            return False
        s = slug.lower()
        return s.startswith("btc-") or s.startswith("bitcoin-")

    def _imbalance(self, bid: float, ask: float) -> float:
        total = bid + ask
        if total <= 0:
            return 0.0
        return (bid - ask) / total

    def _signal(self, mom10: float, mom30: float, imbalance: float, time_frac: float) -> float:
        signal = 0.0

        # Momentum matters most
        if mom10 > 0:
            signal += 2.0
        elif mom10 < 0:
            signal -= 2.0

        if mom30 > 0:
            signal += 3.0
        elif mom30 < 0:
            signal -= 3.0

        # Book confirmation
        if imbalance > 0.15:
            signal += 1.5
        elif imbalance < -0.15:
            signal -= 1.5

        # Press harder later in the market
        if time_frac < 0.40:
            signal *= 1.20
        if time_frac < 0.25:
            signal *= 1.25

        return signal

    def _size_from_strength(self, strength: float, cap_left: float, cash: float, price: float) -> float:
        # Aggressive scaling
        if strength >= 7:
            size = self.max_order_size
        elif strength >= 6:
            size = 30.0
        elif strength >= 5:
            size = 22.0
        else:
            size = self.base_order_size

        return min(size, cap_left, cash / price)

    def on_tick(self, state: MarketState):
        self.price_history.append(state.btc_mid)
        if len(self.price_history) < 11:
            return []

        cash = state.cash
        orders: list[Order] = []

        mom10 = self.price_history[-1] - self.price_history[-11]
        mom30 = self.price_history[-1] - self.price_history[0]

        candidates: list[tuple[float, str, Token, float, float]] = []
        # (edge_strength, slug, token, ask_price, cap_left)

        arb_thr = self.arb_threshold
        arb_sz = self.arb_order_size

        for slug, market in state.markets.items():
            if not self.in_scope(slug, market):
                continue

            # Skip very end where fills can get weird, and very early where signal is weaker
            if market.time_remaining_s < 20 or market.time_remaining_s > 240:
                continue

            yes_ask = market.yes_ask
            no_ask = market.no_ask
            yes_bid = market.yes_bid
            no_bid = market.no_bid

            if yes_ask <= 0 or no_ask <= 0:
                continue

            pos = state.positions.get(slug)
            yes_pos, no_pos, yes_cap_left, no_cap_left = _yes_no_shares_and_buy_room(pos)

            imbalance = self._imbalance(
                market.yes_book.total_bid_size,
                market.yes_book.total_ask_size,
            )

            signal = self._signal(mom10, mom30, imbalance, market.time_remaining_frac)

            # Opportunistic complete-set arb
            total_cost = yes_ask + no_ask
            if total_cost < arb_thr and yes_cap_left > 0 and no_cap_left > 0 and cash > total_cost:
                arb_size = min(
                    arb_sz,
                    yes_cap_left,
                    no_cap_left,
                    cash / total_cost,
                )
                if arb_size > 0:
                    orders.append(Order(slug, Token.YES, Side.BUY, arb_size, yes_ask))
                    orders.append(Order(slug, Token.NO, Side.BUY, arb_size, no_ask))
                    cash -= arb_size * total_cost
                    yes_cap_left -= arb_size
                    no_cap_left -= arb_size

            # Exit losers aggressively
            if yes_pos > 0 and signal <= -4.5 and yes_bid > 0:
                sell_size = min(yes_pos, 25.0)
                orders.append(Order(slug, Token.YES, Side.SELL, sell_size, yes_bid))

            if no_pos > 0 and signal >= 4.5 and no_bid > 0:
                sell_size = min(no_pos, 25.0)
                orders.append(Order(slug, Token.NO, Side.SELL, sell_size, no_bid))

            # Directional entries
            # Penalize expensive side a bit, but let strong signal dominate
            yes_edge = signal - (yes_ask - 0.5) * 4.0
            no_edge = -signal - (no_ask - 0.5) * 4.0

            if yes_edge >= 4.0 and yes_cap_left > 0:
                candidates.append((yes_edge, slug, Token.YES, yes_ask, yes_cap_left))

            if no_edge >= 4.0 and no_cap_left > 0:
                candidates.append((no_edge, slug, Token.NO, no_ask, no_cap_left))

        # Take multiple strong trades, not just one
        candidates.sort(reverse=True, key=lambda x: x[0])

        trades_taken = 0
        for edge, slug, token, ask, cap_left in candidates:
            if trades_taken >= 3:
                break
            if cash <= ask:
                break

            size = self._size_from_strength(edge, cap_left, cash, ask)
            if size <= 0:
                continue

            orders.append(Order(slug, token, Side.BUY, size, ask))
            cash -= size * ask
            trades_taken += 1

        return orders
