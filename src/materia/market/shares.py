import pandas as pd
from materia.core.constants import TRADE_ROW_REGIONS


def estimate_market_shares(df):
    """Estimate market shares from import data (compact, no new helpers)."""
    df.columns = [c.lower().strip() for c in df.columns]
    if not {"partneriso", "qty"}.issubset(df.columns):
        print("❌ Missing required columns:", df.columns.tolist())
        return {}

    s = df[df["partneriso"] != "W00"].groupby("partneriso", as_index=False)["qty"].sum()
    row_qty = s.loc[s["partneriso"].isin(TRADE_ROW_REGIONS), "qty"].sum()

    m = pd.concat(
        [
            s[~s["partneriso"].isin(TRADE_ROW_REGIONS)],
            pd.DataFrame([{"partneriso": "RoW", "qty": row_qty}]),
        ],
        ignore_index=True,
    )

    tot = m["qty"].sum()
    if tot == 0:
        return {}

    m["share"] = m["qty"] / tot
    small = (m["partneriso"] != "RoW") & (m["share"] < 0.01)

    if small.any():
        m.loc[m["partneriso"] == "RoW", "qty"] += m.loc[small, "qty"].sum()
        m = m[~small]
        m["share"] = m["qty"] / m["qty"].sum()

    m["share"] /= m["share"].sum()
    return dict(zip(m.sort_values("share", ascending=False)["partneriso"], m["share"]))
