# 金铲铲AI助手
 注：用到dify，需自行下载安装
 
- `playwright` 抓取金铲铲官网数据
- 通过本地文件或腾讯云 COS 存储抓取结果
- 通过 `FastMCP` 暴露给 Dify 调用

## 目录结构

```text
src/chanchan/
  cli.py
  config.py
  storage.py
  repository.py
  notice_parser.py
  crawlers/
  mcp/server.py
tests/
```

## 安装

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

## 配置

复制 `.env.example` 后按需设置环境变量。

- 本地调试建议：`GCC_STORAGE_BACKEND=local`
- 接 COS 建议：`GCC_STORAGE_BACKEND=cos`，并填写 `GCC_COS_*`

## 使用

### 抓取

```powershell
python -m chanchan crawl heroes
python -m chanchan crawl traits
python -m chanchan crawl runes
python -m chanchan crawl equipment
python -m chanchan crawl notices
python -m chanchan crawl all
```

### 启动 MCP

```powershell
python -m chanchan mcp --transport stdio
python -m chanchan mcp --transport sse --host 0.0.0.0 --port 8000
```

