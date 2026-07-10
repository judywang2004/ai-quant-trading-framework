from pathlib import Path

import yfinance as yf


def main():

    output_dir = Path("data/historical")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "USDJPY_M5.csv"

    df = yf.download(
        "JPY=X",
        interval="5m",
        period="60d",
        progress=False,
    )

    if df.empty:
        print("Download failed.")
        return

    # Flatten MultiIndex columns if necessary
    if hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)

    # Move Datetime index into a normal column
    df.reset_index(inplace=True)

    # Rename columns to match our loader
    df.rename(
        columns={
            "Datetime": "timestamp",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        },
        inplace=True,
    )

    df.to_csv(output_file, index=False)

    print(f"Downloaded {len(df)} candles")
    print(f"Saved to {output_file}")


if __name__ == "__main__":
    main()