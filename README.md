# Ashare-LLM-Analyst

一个基于Python的A股智能分析工具，结合大语言模型提供数据驱动的投资建议和市场洞察。

## 项目简介

Ashare-LLM-Analyst 是一个A股市场的技术分析工具，通过[Ashare](https://github.com/mpquant/Ashare)采集股票历史数据，[MyTT](https://github.com/mpquant/MyTT)计算常见技术指标（如MACD、KDJ、RSI等），并利用大语言模型（Deepseek）生成可读性强的投资建议和市场分析。

该工具能够自动生成完整的HTML分析报告，包括基础数据分析、技术指标计算、趋势判断、支撑/阻力位识别以及AI辅助的专业投资建议。

## 在线预览

您可以访问 [此处](https://ala.oganneson.com) 查看分析报告的示例效果。

## 主要功能

- 自动获取A股历史交易数据
- 计算超过25种技术指标（MA、MACD、KDJ、RSI、BOLL等）
- 生成详细的技术分析图表
- 使用Deepseek大语言模型提供专业的投资分析和建议
- 输出美观的HTML格式分析报告

## 使用方法

### 前置准备

1. 确保安装了所有必需的依赖项:
```bash
pip install pandas numpy matplotlib pytz
```

2. 配置大语言模型API信息（两种方式）： 方式一：使用环境变量（推荐）
```bash
# Linux/Mac
export LLM_API_KEY="your_api_key_here"
export LLM_BASE_URL="https://api.deepseek.com"  # 或其他LLM服务提供商的API地址
export LLM_MODEL="deepseek-chat"  # 使用的模型名称

# Windows (命令提示符)
set LLM_API_KEY=your_api_key_here
set LLM_BASE_URL=https://api.deepseek.com
set LLM_MODEL=deepseek-chat

# Windows (PowerShell)
$env:LLM_API_KEY="your_api_key_here"
$env:LLM_BASE_URL="https://api.deepseek.com"
$env:LLM_MODEL="deepseek-chat"
```
方式二：直接在代码中设置
```python
analyzer = StockAnalyzer(
    stock_info, 
    llm_api_key="your_api_key_here",
    llm_base_url="https://api.deepseek.com",
    llm_model="deepseek-chat"
)
```

### 运行分析

1. 在`main.py`中设置要分析的股票代码：
```python
stock_info = {
    '股票名称': '股票代码',  # 例如 '上证指数': 'sh000001'
}
```

2. 运行主程序：
```bash
python main.py
```

3. 分析报告将自动生成并保存在`public/index.html`路径下

## 服务模式（持续自动更新，推荐）

一次部署，长期运行，自动定时更新报告并对外提供访问页面。还支持从 Git 自动拉取仓库更新并自我重启应用，真正做到“部署一次，长期免维护”。

- 启动命令：python server.py
- 默认端口：8000（可通过环境变量 PORT 修改）
- 默认更新频率：每 60 分钟（可通过 UPDATE_INTERVAL_MINUTES 修改）
- 默认输出目录：public/index.html（可通过 PUBLIC_DIR 修改）

1) 快速开始

- 安装依赖（推荐使用 requirement.txt）
  pip install -r requirement.txt

- 指定要分析的股票（两种方式任选其一）
  方式一：在仓库根目录创建 stocks.json
  {
    "上证指数": "sh000001",
    "平安银行": "sz000001"
  }
  方式二：使用环境变量传入 JSON
  export STOCKS_JSON='{"上证指数":"sh000001","平安银行":"sz000001"}'

- 启动服务
  python server.py
  浏览器访问 http://<服务器IP>:8000

2) 常用环境变量（可选）

- PORT：HTTP 服务端口，默认 8000
- PUBLIC_DIR：静态文件输出目录，默认 ./public
- UPDATE_INTERVAL_MINUTES：自动更新间隔（分钟），默认 60
- HISTORY_COUNT：历史数据条数，默认 120
- LLM_API_KEY / LLM_BASE_URL / LLM_MODEL：启用 AI 分析所需配置
- STOCKS_FILE：自定义股票配置文件路径（默认 ./stocks.json）
- STOCKS_JSON：直接传入 JSON 字符串（高优先级）
- AUTO_GIT_UPDATE：是否开启 Git 自动拉取更新，默认 1（开启）
- GIT_REMOTE / GIT_BRANCH：Git 远端与分支，默认 origin/main
- AUTO_UPDATE_PIP：拉取代码后是否自动 pip install -r requirement.txt，默认 0（关闭）

3) 内置 HTTP 接口

- GET /          当前生成的报告页面（public 目录）
- GET /status    查看最近一次更新状态、更新时间、当前 Commit 等
- GET /update    立刻触发一次后台更新（异步）
- GET /healthz   健康检查

4) 开机自启（systemd 示例）

- /etc/systemd/system/ashare-llm.service（示例）：
  [Unit]
  Description=Ashare LLM Analyst (auto update server)
  After=network.target

  [Service]
  WorkingDirectory=/opt/ashare-llm-analyst
  ExecStart=/usr/bin/python3 server.py
  Environment=PORT=8000
  Environment=UPDATE_INTERVAL_MINUTES=60
  Environment=AUTO_GIT_UPDATE=1
  Restart=always

  [Install]
  WantedBy=multi-user.target

- 启动与开机自启
  sudo systemctl daemon-reload
  sudo systemctl enable --now ashare-llm.service

## 技术架构

- 数据获取：使用Ashare模块获取A股历史数据
- 技术分析：使用MyTT库进行技术指标计算
- 图表生成：使用Matplotlib生成技术分析图表
- AI分析：通过Deepseek API获取专业的投资建议
- 报告生成：生成包含详细分析的HTML报告

## 输出示例

生成的分析报告包含以下内容：

1. 基础技术分析（收盘价、涨跌幅、成交量等）
2. 技术指标详情（各项指标的最新值）
3. 技术指标图表（多维度的股票走势分析图）
4. 人工智能分析报告（基于历史数据的专业分析和投资建议）

## 重要说明

- **安全提示**：该项目是由个人自用的私有仓库公开而来，API凭据的存储并未做特别的安全防范措施。请务必妥善保管你的API密钥，建议使用环境变量或配置文件来存储敏感信息。

- **输出位置**：分析结果会输出到根目录下的`public`文件夹中。如果文件夹不存在，程序会自动创建。

- **免责声明**：本工具仅供学习和研究使用，不构成任何投资建议。投资有风险，入市需谨慎。用户应对自己的投资决策负责。

## 后续开发计划

- 添加更多技术指标和分析维度
- 支持批量分析多只股票
- 提供更丰富的可视化选项
- 增加历史数据对比和回测功能
- 优化AI分析模型和提示词设计

## 许可证

[MIT License](LICENSE)

## 赞助

<a href="https://edgeone.ai/?from=github">
<img src="https://edgeone.ai/media/34fe3a45-492d-4ea4-ae5d-ea1087ca7b4b.png" alt="Tencent EdgeOne" width="200">
</a>

CDN acceleration and security protection for this project are sponsored by Tencent EdgeOne.

