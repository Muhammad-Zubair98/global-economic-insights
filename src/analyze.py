from pathlib import Path
import time
import requests
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
FIG_DIR = ROOT / "reports" / "figures"
DATA_DIR.mkdir(exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

COUNTRIES = {
    "WLD": "World", "USA": "United States", "GBR": "United Kingdom",
    "DEU": "Germany", "IND": "India", "PAK": "Pakistan",
    "BRA": "Brazil", "ZAF": "South Africa", "ARE": "United Arab Emirates",
    "JPN": "Japan", "CHN": "China",
}
INDICATORS = {
    "NY.GDP.PCAP.CD": "gdp_per_capita_usd",
    "FP.CPI.TOTL.ZG": "inflation_pct",
    "SL.UEM.TOTL.ZS": "unemployment_pct",
    "IT.NET.USER.ZS": "internet_users_pct",
}


def fetch_indicator(code: str, name: str) -> pd.DataFrame:
    url = f"https://api.worldbank.org/v2/country/all/indicator/{code}"
    params = {"format": "json", "per_page": 20000, "date": "2010:2023"}
    last_error = None
    for attempt in range(3):
        try:
            response = requests.get(url, params=params, timeout=90)
            response.raise_for_status()
            payload = response.json()
            rows = []
            for item in payload[1]:
                country_code = item["countryiso3code"]
                if country_code in COUNTRIES and item["value"] is not None:
                    rows.append({
                        "country_code": country_code,
                        "country": COUNTRIES[country_code],
                        "year": int(item["date"]),
                        name: item["value"],
                    })
            return pd.DataFrame(rows)
        except requests.RequestException as exc:
            last_error = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"World Bank request failed for {code}: {last_error}")


def main() -> None:
    frames = [fetch_indicator(code, name) for code, name in INDICATORS.items()]
    data = frames[0]
    for frame in frames[1:]:
        data = data.merge(frame, on=["country_code", "country", "year"], how="outer")
    data = data.sort_values(["country", "year"])
    data.to_csv(DATA_DIR / "world_bank_indicators.csv", index=False)

    latest = data[data["year"] == data["year"].max()].copy()
    latest.sort_values("gdp_per_capita_usd", ascending=False).to_csv(DATA_DIR / "latest_snapshot.csv", index=False)

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(11, 6))
    for country in ["United States", "China", "India", "Pakistan", "Germany"]:
        subset = data[data["country"] == country]
        ax.plot(subset["year"], subset["gdp_per_capita_usd"], marker="o", linewidth=2, label=country)
    ax.set_title("GDP per Capita Trends, 2010–2023")
    ax.set_xlabel("Year")
    ax.set_ylabel("Current US dollars")
    ax.legend(ncol=2)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "gdp_per_capita_trends.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 6))
    plot_data = latest.sort_values("internet_users_pct", ascending=True)
    ax.barh(plot_data["country"], plot_data["internet_users_pct"], color="#2563eb")
    ax.set_title("Internet Use in the Latest Available Year")
    ax.set_xlabel("Individuals using the internet (%)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "internet_adoption_latest.png", dpi=180)
    plt.close(fig)

    summary = [
        "# Analysis outputs", "",
        f"The pipeline downloaded World Bank indicators for {len(COUNTRIES)} economies and the world aggregate for 2010–2023.",
        "",
        "The generated CSV files support further exploration without committing third-party raw data to the repository.",
        "",
        "## Important limitations", "",
        "Indicators have different reporting lags and may not share the same latest year. GDP per capita is measured in current US dollars, so exchange rates and inflation affect comparisons.",
        "",
        "The charts are descriptive and should not be interpreted as causal evidence.",
    ]
    (ROOT / "reports" / "insights.md").write_text("\n".join(summary) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
