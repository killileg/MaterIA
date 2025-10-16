import os
import json
import pandas as pd
from tqdm import tqdm

from materia.io.paths import IMPORTS_FOLDER, MARKET_FOLDER
from market.comtrade import get_unique_hs_codes, fetch_trade_data_for_hs_code
from market.shares import estimate_market_shares


def update_shares(comtradeapikey):
    hs_codes = get_unique_hs_codes()

    for hs_code in tqdm(hs_codes, desc="Fetching HS codes"):
        fetch_trade_data_for_hs_code(hs_code, comtradeapikey)

    for filename in tqdm(os.listdir(IMPORTS_FOLDER), desc="Processing trade files"):
        if filename.endswith(".csv") and filename.startswith("I_"):
            hs_code = filename[2:-4]
            filepath = os.path.join(IMPORTS_FOLDER, filename)
            market_file_path = os.path.join(MARKET_FOLDER, hs_code + ".json")
            try:
                df = pd.read_csv(filepath)
                market_shares = estimate_market_shares(df)
                with open(market_file_path, "w", encoding="utf-8") as f:
                    json.dump(market_shares, f, ensure_ascii=False, indent=2)

            except Exception as e:
                print(f"❌ Error processing {filename}: {e}")
