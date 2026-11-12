"""Solar imbalance cost: what forecast errors cost per MWh produced, from real imbalance prices."""
import pandas as pd


def _window(index: pd.DatetimeIndex, months: int) -> pd.PeriodIndex:
    """The last `months` complete calendar months present in `index` (UTC hours).

    A month is complete when the data reach its last hour. A partial final month
    is skipped; if no month is complete at all, every month present is used.
    """
    naive = index.tz_localize(None) if index.tz is not None else index
    periods = naive.to_period("M")
    last = periods.max()
    if naive.max() < last.end_time.floor("h"):
        last = last - 1
    if last < periods.min():  # nothing complete: use what exists
        return pd.period_range(periods.min(), periods.max(), freq="M")
    return pd.period_range(max(last - (months - 1), periods.min()), last, freq="M")


def imbalance_cost(
    imbalance: pd.Series,
    prices: pd.Series,
    solar_shape: pd.Series,
    error_share: float = 0.10,
    months: int = 24,
) -> float:
    """Imbalance cost of a solar producer in EUR per MWh produced.

    Method: the producer misses a share `error_share` of its output (forecast
    error) and settles that volume at the imbalance price instead of the day-ahead
    price, so each MWh costs `error_share` x |imbalance - day-ahead|. The
    deviation is averaged over the last `months` complete calendar months of the
    imbalance series, weighting each hour by the solar shape (so night hours,
    when nothing is produced, do not count).
    """
    df = pd.concat({"imb": imbalance, "price": prices, "w": solar_shape}, axis=1).dropna()
    if df.empty:
        raise ValueError("imbalance, prices and solar shape have no common hours")
    window = _window(imbalance.dropna().index, months)
    naive = df.index.tz_localize(None) if df.index.tz is not None else df.index
    df = df[naive.to_period("M").isin(window)]
    if df.empty or df["w"].sum() <= 0:
        raise ValueError("no solar-weighted hours in the imbalance window")
    deviation = (df["imb"] - df["price"]).abs()
    return float(error_share * (deviation * df["w"]).sum() / df["w"].sum())
