import os
import pandas as pd
from datetime import datetime, date
from typing import List, Dict, Optional
from pathlib import Path


class DataLoader:
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self._cache: Dict[date, pd.DataFrame] = {}
        self._trading_days: Optional[List[date]] = None

    def discover_trading_days(self) -> List[date]:
        if self._trading_days is not None:
            return self._trading_days

        days = []
        for year_dir in sorted(self.data_dir.iterdir()):
            if not year_dir.is_dir():
                continue
            for day_dir in sorted(year_dir.iterdir()):
                if not day_dir.is_dir():
                    continue
                csv_file = day_dir / f"{self.data_dir.name}.csv"
                if csv_file.exists():
                    try:
                        d = date.fromisoformat(day_dir.name)
                        days.append(d)
                    except ValueError:
                        continue

        self._trading_days = sorted(days)
        return self._trading_days

    def load_day(self, d: date) -> Optional[pd.DataFrame]:
        if d in self._cache:
            return self._cache[d]

        year_str = str(d.year)
        day_str = d.isoformat()
        ticker = self.data_dir.name
        csv_path = self.data_dir / year_str / day_str / f"{ticker}.csv"

        if not csv_path.exists():
            return None

        df = pd.read_csv(csv_path, dtype={
            "TranID": int,
            "Time": str,
            "Price": float,
            "Volume": int,
            "SaleOrderVolume": int,
            "BuyOrderVolume": int,
            "Type": str,
            "SaleOrderID": int,
            "SaleOrderPrice": float,
            "BuyOrderID": int,
            "BuyOrderPrice": float,
        })

        def parse_dt(t_str: str) -> datetime:
            return datetime.strptime(f"{day_str} {t_str}", "%Y-%m-%d %H:%M:%S")

        df["Datetime"] = df["Time"].apply(parse_dt)
        df["Type"] = df["Type"].str.strip().str.upper()

        self._cache[d] = df
        return df

    def load_all(self) -> Dict[date, pd.DataFrame]:
        days = self.discover_trading_days()
        for d in days:
            self.load_day(d)
        return self._cache

    def get_cached(self, d: date) -> Optional[pd.DataFrame]:
        return self._cache.get(d)
