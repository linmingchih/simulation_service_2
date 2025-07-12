## Simulation Service 架構白皮書（基於 Windows + Flask + 多程序處理）

本文件旨在描述一套可於 Windows 平台上執行之工程模擬服務架構（Simulation Service），此架構透過 Flask 為基礎的 Web 框架，整合模組化流程控制機制與可擴展的後台任務排程，適用於多使用者、多模擬作業並行的研究與產業應用環境。

### 系統組成與關鍵技術元件

* **使用者介面（UI）：** 採用 Bootstrap 5 搭配 Jinja2 模板引擎，並保留進階整合 React 的彈性，用以建構具一致性與響應式特性的操作介面。
* **應用伺服器層（Backend）：** 採用 Flask 架構設計 RESTful API，並透過 `waitress` 作為 WSGI 層級之生產級伺服引擎，支援 Windows 本地部署。
* **非同步作業調度機制：**

  * 可選用 Python 標準之 `multiprocessing` 或 `concurrent.futures` 實作獨立流程執行。
  * 為支援前端即時監控任務進度，可輔以 `Flask-SocketIO` 或 `Flask-Executor` 建立事件驅動式通知架構。
* **資料儲存機制：** 適合儲存模擬設定、作業紀錄與執行狀態之元資料，可採用 SQLite、TinyDB 或結構化 JSON 檔案。

### 執行流程定義與作業模型

* **流程（Flow）：** 定義為一組具有明確順序與相依性的模擬步驟組合，例如：前處理 → 模擬求解 → 結果後處理。每一流程透過 `flow.json` 描述其結構，對應實作則以 Python 腳本形式模組化配置，具備可插拔性。
* **作業（Job）：** 使用者依據特定流程所建立之單次模擬任務，其包含上傳檔案、設定參數、執行中間資料與最終結果。每筆作業皆配置獨立資料夾儲存，並由後端定期更新 `status.json` 紀錄執行進度。

流程與作業相互映射，構成平台核心邏輯。流程提供結構性框架，作業承載動態輸入與計算內容，可支援多使用者並行執行與資源排程最佳化。

### 專案結構規劃與模組配置（含每流程、每步驟專屬頁面設計）

每個流程（flow）皆擁有獨立的頁面樣板配置資料夾，包含該流程所有步驟對應的 `step.html` 檔案。這些樣板檔案位於對應流程資料夾下之 `templates/steps/` 中，例如：

```
flows/
├── Flow_DCIR/
│   ├── flow.json
│   ├── step_01.py
│   ├── step_02.py
│   ├── step_03.py
│   └── templates/steps/
│       ├── step_01.html
│       ├── step_02.html
│       └── step_03.html
├── Flow_SIwave/
│   ├── flow.json
│   └── templates/steps/
│       ├── step_01.html
│       └── step_02.html
```

```
project_root/
├── app/
│   ├── __init__.py                # 應用初始化主模組
│   ├── routes.py                  # API 路由設定（含使用者與流程）
│   ├── admin.py                   # 系統管理 API（人員、資源、授權）
│   ├── templates/                 # Jinja2 模板檔案（支援 Bootstrap 樣式）
│   │   ├── layout.html
│   │   ├── deck.html
│   │   ├── flow.html
│   │   ├── admin_dashboard.html
│   │   ├── logs.html
│   │   └── steps/                 # 每一個流程步驟對應專屬頁面（如 step_01.html）
│   │       ├── step_01.html
│   │       ├── step_02.html
│   │       └── step_03.html
│   ├── static/                    # 前端靜態檔案
│   └── flows/                     # 插件式模擬流程模組（熱插拔）
│       ├── Flow_DCIR/
│       │   ├── flow.json
│       │   ├── step_01.py
│       │   ├── step_02.py
│       │   └── step_03.py
│       └── Flow_SIwave/
│           └── ...
├── jobs/                          # 動態作業儲存區（依作業 ID 分目錄）
│   └── job_001/
│       ├── input_files/
│       ├── output_files/
│       ├── config.json
│       └── status.json
├── run.py                         # 系統主啟動入口（提供給 waitress）
├── requirements.txt               # 套件依賴清單
└── README.md
```

### 環境建置與自動化安裝程序

為協助新環境部署與開發測試，可使用下列 `install.bat` 批次檔自動完成虛擬環境建置與套件安裝流程：

```bat
@echo off
python -m venv venv
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
pause
```

其中 `requirements.txt` 建議納入以下模組：

* `Flask`
* `waitress`
* `pyaedt[all]`
* `matplotlib`
* `flask_executor`

建議於不同部署環境建立獨立虛擬環境，以維持套件相容性與執行穩定性。

### 測試與預設登入帳號

開發與測試階段預設提供以下登入憑證：

* 管理者帳號：帳號 `admin` / 密碼 `admin`
* 一般使用者：帳號 `abc` / 密碼 `1234`

使用者可登入後瀏覽 Deck、啟動流程、管理模擬作業。部署至正式環境時，請立即移除或更新預設憑證以強化系統資安。

---

若需進一步補充模擬流程注入方法、自動註冊與排程 API、或整合 React 前端框架的進階介接範例，請提出後續需求。
