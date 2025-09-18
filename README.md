Reel Profit Calculator

Overview

This CLI app helps you track your stock operations and compute your real (inflation-adjusted) profit. It supports:

- US and TR stocks
- TR or US inflation as the reference basis
- Automatic USD/TRY retrieval (with manual fallback)
- Purchase/Sale logging and current portfolio summary
- Editing inflation data (add/edit/delete) and listing all inflation rows


Requirements

- Python 3.10+
- Packages: requests, lxml

Install dependencies:

```bash
pip install requests lxml
```


Project Files

- main.py: Application entry and CLI menu
- operations.csv: Logged transactions
- shares.csv: Current holdings (derived from operations)
- inflation.csv: Monthly inflation data by country (TR/US)
- info.txt: User metadata (auto-created)


CSV Schemas

inflation.csv

```csv
month,year,country,rate
8,2025,TR,2.04
9,2025,TR,3.10
...
```

- month: 1-12
- year: 2000-2100
- country: TR or US
- rate: monthly percent (e.g., 2.04 means 2.04%)

operations.csv

```csv
id,stock_name,country_name,transaction_type,share_price,number_of_shares,transaction_fee,exchange_rate,currency,date,tl_price,usd_price
1,NVDA,US,purchase,181.68,0.39,1.5,41.2865,USD,2025-08-15,2925.3632,70.8552
```

- transaction_type: purchase or sale
- currency: TL or USD (native input currency during the operation)
- tl_price/usd_price: computed totals per transaction

shares.csv

```csv
share_name,country_name,quantity
NVDA,US,1.23
```


Running

```bash
python main.py
```

Main Menu

1. US Stock Operations
2. TR Stock Operations
3. Edit Inflation Rates
4. Calculate my reel profit
5. Show my stock summary
0. Exit


Editing Inflation Data

Use menu 3:

- Add/Edit/Delete monthly rows
- Show all inflation rows

Note: For real profit calculation, from the earliest transaction month to the current month, inflation rows must exist for the chosen reference country (TR/US). Missing months will be reported and calculation aborted.


Calculate Real Profit (Method)

Reference selection

- Choose TR or US as the reference inflation series
- Reference currency is derived: TR → TL, US → USD

Index and deflators

- Build a monthly CPI index starting from the earliest transaction month as base (index = 1)
- For month m with monthly rate r_m (%): I_m = I_{m-1} × (1 + r_m/100)
- Deflator for month m: D_m = 1 / I_m (base month has D = 1)

Cash flows (real terms)

- For each operation:
  - Use tl_price if reference is TL, else usd_price
  - Purchases are negative cash flows; sales are positive
  - Real cash flow = nominal × D_{month(op.date)}

Current portfolio (real terms)

- Prompt current price per holding in its native currency (USD for US, TL for TR)
- Convert to reference currency using USD/TRY (auto via web or manual input)
- Nominal portfolio = Σ(quantity × price_in_reference)
- Real portfolio = nominal × D_{current_month}

Real profit and ROI

- Real net gain: G_real = RealPortfolio + Σ RealCashFlows
- Invested real capital: sum of negative real cash flows (absolute value)
- Real ROI (%): G_real / InvestedReal × 100 (if invested real > 0)
- Also reports period CPI change from base to current


Notes & Tips

- If USD/TRY fetch fails, you can enter the rate manually
- All monetary calculations use Decimal and banker's rounding via round_money
- If you add inflation rows, ensure continuity (no missing months from base to current)


Troubleshooting

- Missing inflation data: Add monthly rows covering the gap for the selected reference country
- Network issues for USD/TRY: Use manual rate entry when prompted
- CSV write errors on macOS: Ensure the app has permission to write to the project folder


Roadmap

- Include transaction fees directly in cash flows
- Add nominal vs real breakdown per holding
- Optional IRR/TWR methods


