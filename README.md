# 指数多空信号仪表盘

每日自动更新的三大美股指数信号页面（标普500/纳斯达克/道琼斯）。

## 部署到 GitHub Pages（5分钟完成）

### 第一步：创建 GitHub 仓库
1. 打开 https://github.com/new
2. 仓库名填 `market-signals`（或任意名称）
3. 选 **Public**（GitHub Pages 免费版需要公开仓库）
4. 点击 Create repository

### 第二步：上传文件
把以下文件上传到仓库根目录：
- `index.html`
- `generate_signals.py`
- `signals.json`
- `.github/workflows/update_signals.yml`

方法：在仓库页面点 "uploading an existing file"，把这四个文件拖进去，点 Commit changes。

### 第三步：开启 GitHub Pages
1. 进入仓库 → Settings → Pages
2. Source 选 **Deploy from a branch**
3. Branch 选 **main**，文件夹选 **/ (root)**
4. 点 Save

等约 1 分钟，你的网站地址就会显示为：
`https://<你的用户名>.github.io/market-signals/`

### 第四步：让 Actions 有写入权限
1. 仓库 → Settings → Actions → General
2. 滚到底部 "Workflow permissions"
3. 选 **Read and write permissions**
4. 点 Save

### 第五步：验证自动更新
- Actions 会在每个交易日 UTC 22:30（北京时间次日 06:30）自动运行
- 也可以手动触发：Actions → Update Signals Daily → Run workflow

## 文件说明

| 文件 | 用途 |
|------|------|
| `index.html` | 网页仪表盘，自动读取 signals.json |
| `generate_signals.py` | 信号生成脚本，GitHub Actions 每日运行 |
| `signals.json` | 当日信号数据，由脚本自动更新 |
| `.github/workflows/update_signals.yml` | 定时任务配置 |

## 信号逻辑

**入场（满仓做多）** — 以下条件全部满足：
- 价格站上 MA20（快速）或 MA50（稳健）
- 5日收益率 > 0
- 21日收益率 > 0
- VIX 从近期峰值回落 > 15%

**出场（空仓现金）** — 以下任一条件触发：
- 价格跌破对应均线
- 21日跌幅 > 3%
- VIX 10日内飙升 > 40%
