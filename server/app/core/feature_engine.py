import pandas as pd
import numpy as np
from datetime import date, datetime, time as dtime
from typing import List, Optional
from .models import WindowFeature, ExcursionRecord
from ..utils.time_utils import generate_windows, MORNING_START, AFTERNOON_END, MORNING_END, AFTERNOON_START


class FeatureEngine:
    def __init__(self, window_minutes: int = 5):
        self.window_minutes = window_minutes

    def extract_day_features(self, day: date, df: pd.DataFrame) -> List[WindowFeature]:
        trading_df = df[
            (
                (df["Datetime"].dt.time >= MORNING_START) &
                (df["Datetime"].dt.time <= MORNING_END)
            ) | (
                (df["Datetime"].dt.time >= AFTERNOON_START) &
                (df["Datetime"].dt.time <= AFTERNOON_END)
            )
        ].copy()

        windows = generate_windows(day, self.window_minutes)
        features: List[WindowFeature] = []

        # Track previous window's static features for delta calculation.
        # Reset at the start of each session (morning / afternoon).
        prev_force: Optional[float] = None
        prev_momentum: Optional[float] = None
        prev_accel: Optional[float] = None
        prev_force_delta: Optional[float] = None
        prev_momentum_delta: Optional[float] = None
        prev_accel_delta: Optional[float] = None
        prev_session: Optional[str] = None  # 'morning' or 'afternoon'

        for win_start, win_end in windows:
            mask = (trading_df["Datetime"] >= win_start) & (trading_df["Datetime"] < win_end)
            win_df = trading_df[mask]

            if len(win_df) == 0:
                continue

            feat_raw = self._compute_static_features(day, win_start, win_end, win_df)
            if feat_raw is None:
                continue

            force_ratio, price_momentum, trade_acceleration, tick_count, first_price, last_price = feat_raw

            # Determine session and whether it is the first window in this session
            if win_start.time() >= AFTERNOON_START:
                current_session = "afternoon"
            else:
                current_session = "morning"

            if prev_session != current_session or prev_force is None:
                force_ratio_delta = 0.0
                momentum_delta = 0.0
                acceleration_delta = 0.0
            else:
                force_ratio_delta = force_ratio - prev_force
                momentum_delta = price_momentum - prev_momentum
                acceleration_delta = trade_acceleration - prev_accel

            # Second-order delta (rate of change of the rate of change)
            if prev_force_delta is None or prev_session != current_session:
                force_ratio_delta2 = 0.0
                momentum_delta2 = 0.0
                acceleration_delta2 = 0.0
            else:
                force_ratio_delta2 = force_ratio_delta - prev_force_delta
                momentum_delta2 = momentum_delta - prev_momentum_delta
                acceleration_delta2 = acceleration_delta - prev_accel_delta

            features.append(WindowFeature(
                day=day,
                win_start=win_start,
                win_end=win_end,
                force_ratio=force_ratio,
                price_momentum=price_momentum,
                trade_acceleration=trade_acceleration,
                force_ratio_delta=force_ratio_delta,
                momentum_delta=momentum_delta,
                acceleration_delta=acceleration_delta,
                force_ratio_delta2=force_ratio_delta2,
                momentum_delta2=momentum_delta2,
                acceleration_delta2=acceleration_delta2,
                tick_count=tick_count,
                first_price=first_price,
                last_price=last_price,
            ))

            prev_force = force_ratio
            prev_momentum = price_momentum
            prev_accel = trade_acceleration
            prev_force_delta = force_ratio_delta
            prev_momentum_delta = momentum_delta
            prev_accel_delta = acceleration_delta
            prev_session = current_session

        return features

    def _compute_static_features(
        self,
        day: date,
        win_start: datetime,
        win_end: datetime,
        win_df: pd.DataFrame,
    ) -> Optional[tuple]:
        """Return (force_ratio, price_momentum, trade_acceleration, tick_count, first_price, last_price)."""
        if len(win_df) < 2:
            return None

        buy_df = win_df[win_df["Type"] == "B"]
        sell_df = win_df[win_df["Type"] == "S"]

        buy_vol_value = (buy_df["Price"] * buy_df["Volume"]).sum()
        sell_vol_value = (sell_df["Price"] * sell_df["Volume"]).sum()

        if sell_vol_value == 0:
            if buy_vol_value == 0:
                force_ratio = 1.0
            else:
                force_ratio = 10.0
        else:
            force_ratio = min(buy_vol_value / sell_vol_value, 10.0)

        first_price = win_df.iloc[0]["Price"]
        last_price = win_df.iloc[-1]["Price"]

        if first_price == 0:
            return None

        price_momentum = (last_price - first_price) / first_price

        mid_time = win_start + (win_end - win_start) / 2
        first_half = win_df[win_df["Datetime"] < mid_time]
        second_half = win_df[win_df["Datetime"] >= mid_time]

        n_first = len(first_half)
        n_second = len(second_half)

        if n_first == 0:
            trade_acceleration = 2.0
        else:
            trade_acceleration = min(n_second / n_first, 10.0)

        return force_ratio, price_momentum, trade_acceleration, len(win_df), float(first_price), float(last_price)

    def compute_excursion(
        self, day_df: pd.DataFrame, entry_time: datetime
    ) -> Optional[ExcursionRecord]:
        """
        Starting from entry_time, track all ticks until end of day
        (excluding lunch break 11:30-13:00) and compute MFE and MAE.

        MFE: maximum favorable excursion (max upside % from entry, positive)
        MAE: maximum adverse excursion (max drawdown % from entry, positive)
        end_return: return at the last tick of the day
        duration_to_mfe: number of ticks from entry to the MFE tick
        """
        # Only include ticks within trading hours on the same day
        entry_date = entry_time.date()
        trading_mask = (
            (
                (day_df["Datetime"].dt.time >= MORNING_START) &
                (day_df["Datetime"].dt.time <= MORNING_END)
            ) | (
                (day_df["Datetime"].dt.time >= AFTERNOON_START) &
                (day_df["Datetime"].dt.time <= AFTERNOON_END)
            )
        )
        trading_df = day_df[trading_mask]

        # Filter ticks from entry_time onwards
        future_ticks = trading_df[trading_df["Datetime"] >= entry_time]
        if len(future_ticks) < 2:
            return None

        entry_price = float(future_ticks.iloc[0]["Price"])
        if entry_price == 0:
            return None

        prices = future_ticks["Price"].values
        returns = (prices - entry_price) / entry_price

        mfe = float(np.max(returns))   # max upside
        mae = float(-np.min(returns))  # max drawdown (converted to positive)
        end_return = float(returns[-1])
        mfe_idx = int(np.argmax(returns))

        return ExcursionRecord(
            mfe=max(mfe, 0.0),
            mae=max(mae, 0.0),
            end_return=end_return,
            duration_to_mfe=mfe_idx,
        )
