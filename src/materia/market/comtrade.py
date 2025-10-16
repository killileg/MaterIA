import os
import time
import pandas as pd

from materia.io.files import gen_json_objects

from materia.io import paths as IO_PATHS
from materia.core import constants as C

import comtradeapicall


def get_unique_hs_codes():
    """Extracts a set of unique HS codes from the generated product JSON files."""
    hs_codes = {
        product["HS Code"]
        for _, product in gen_json_objects(IO_PATHS.GEN_PRODUCTS_FOLDER)
        if isinstance(product, dict) and "HS Code" in product
    }
    return hs_codes


def fetch_trade_data_for_hs_code(hs_code, comtradeapikey):
    try:
        params = dict(
            typeCode="C",
            freqCode="A",
            clCode="HS",
            period=",".join(C.TRADE_YEARS),
            reporterCode=C.TRADE_TARGET,
            cmdCode=hs_code,
            flowCode=C.TRADE_FLOW,
            partnerCode=None,
            partner2Code=None,
            customsCode=None,
            motCode=None,
            maxRecords=2500,
            format_output="JSON",
            aggregateBy=None,
            breakdownMode="classic",
            countOnly=None,
            includeDesc=True,
        )
        df = comtradeapicall.getFinalData(comtradeapikey, **params)
        if isinstance(df, pd.DataFrame) and not df.empty:
            out = os.path.join(IO_PATHS.IMPORTS_FOLDER, f"I_{hs_code}.csv")
            df.to_csv(out, index=False)
            return out
        print(f"No data for HS {hs_code}")
    except Exception as e:
        print(f"Error fetching data for HS {hs_code}: {e}")
    finally:
        time.sleep(1)
    return None
