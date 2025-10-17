import time
import pandas as pd
from tqdm import tqdm
import comtradeapicall

from materia.io.files import gen_json_objects
from materia.io import paths as IO_PATHS
from materia.core import constants as C
from materia.resources import update_user_data
from materia.core.constants import TRADE_ROW_REGIONS


def get_unique_hs_codes():
    """Extracts a set of unique HS codes from the generated product JSON files."""
    hs_codes = {
        product["HS Code"]
        for _, product in gen_json_objects(IO_PATHS.GEN_PRODUCTS_FOLDER)
        if isinstance(product, dict) and "HS Code" in product
    }
    return hs_codes


def fetch_trade_data_for_hs_code(
    hs_code: str, comtradeapikey: str
) -> pd.DataFrame | None:
    try:
        params = dict(
            typeCode="C",
            freqCode="A",
            clCode="HS",
            period=",".join(C.TRADE_YEARS),
            reporterCode=C.TRADE_TARGET,
            cmdCode=hs_code,
            flowCode=C.TRADE_FLOW,
            format_output="JSON",
            includeDesc=True,
            maxRecords=2500,
            breakdownMode="classic",
        )
        df = comtradeapicall.getFinalData(comtradeapikey, **params)
        if isinstance(df, pd.DataFrame) and not df.empty:
            return df
        print(f"No data for HS {hs_code}")
    except Exception as e:
        print(f"Error fetching data for HS {hs_code}: {e}")
    finally:
        time.sleep(1)
    return None


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


def update_shares(comtradeapikey: str) -> None:
    hs_codes = get_unique_hs_codes()

    for hs_code in tqdm(hs_codes, desc="Updating market shares"):
        df = fetch_trade_data_for_hs_code(hs_code, comtradeapikey)
        if df is not None:
            market_shares = estimate_market_shares(df)
            update_user_data("market_shares", f"{hs_code}.json", market_shares)
