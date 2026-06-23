# 台股每日篩選與推薦流程

本專案提供一個可調整商業邏輯的台股篩選系統雛形，目標是每天更新基本面、籌碼面與價格資料，產出「基本面佳、籌碼面佳、價格完成整理」的推薦清單。

## 資料流程

1. **資料擷取**
   - 價格：可使用永豐 Shioaji API 或證交所 `STOCK_DAY` 日成交資訊。
   - 籌碼：可使用永豐 API、證交所三大法人買賣超、融資融券，以及集保戶股權分散資料。
   - 基本面：可匯入公開資訊觀測站、證交所彙整資料或付費資料源的營收、EPS、ROE、毛利率、負債比。
2. **標準化**
   - 輸出三份處理後 CSV：`fundamentals.csv`、`chips.csv`、`prices.csv`。
   - `stock_id` 是三份資料的共同鍵。
3. **評分**
   - 基本面與籌碼面以 `config/screener.yaml` 的權重和門檻計分。
   - 價格面以規則判斷：修正、整理中、完成整理、已噴出。
4. **推薦**
   - 只保留總分達門檻、且價格狀態等於 `completed_base` 的股票。
   - 每日排程可用 cron、GitHub Actions、Airflow 或內部排程器執行 `select-tw-update`。

## 處理後資料欄位

### `data/processed/fundamentals.csv`

| 欄位 | 說明 |
| --- | --- |
| `stock_id` | 股票代號 |
| `revenue_growth_yoy` | 月營收年增率 |
| `operating_margin` | 營業利益率 |
| `roe` | 股東權益報酬率 |
| `eps_growth_yoy` | EPS 年增率 |
| `debt_ratio_inverse` | 負債比反向分數用欄位，數值越高越好 |

### `data/processed/chips.csv`

| 欄位 | 說明 |
| --- | --- |
| `stock_id` | 股票代號 |
| `foreign_net_buy_ratio_5d` | 外資 5 日買超占成交量比例 |
| `investment_trust_net_buy_ratio_5d` | 投信 5 日買超占成交量比例 |
| `dealer_net_buy_ratio_5d` | 自營商 5 日買超占成交量比例 |
| `margin_balance_change_5d_inverse` | 融資餘額 5 日變化反向指標 |
| `main_holder_ratio_change_4w` | 大戶持股比例 4 週變化 |

### `data/processed/prices.csv`

| 欄位 | 說明 |
| --- | --- |
| `stock_id` | 股票代號 |
| `date` | 交易日期 |
| `close` | 收盤價 |
| `volume` | 成交量 |

## 每日執行範例

```bash
select-tw-update --config config/screener.yaml --data-dir data/processed --output reports/recommendations.csv
```

若要調整選股邏輯，優先修改 `config/screener.yaml`：

- `fundamental_score.weights`：基本面因子權重。
- `chip_score.weights`：籌碼面因子權重。
- `price_stage`：價格型態門檻。
- `run.minimum_total_score`：總分下限。
- `run.require_price_stage`：必要價格階段。
