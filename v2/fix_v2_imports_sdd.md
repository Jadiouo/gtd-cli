# SDD：修正 v2 package import 問題

## 問題描述

`pip install -e .` 後執行 `gtd --help` 報錯：

```
ModuleNotFoundError: No module named 'storage'
```

原因：`v2/` 目錄下的所有 Python 檔案使用**裸 import**（bare import），例如：

```python
from storage import TaskStorage   # ❌ 只在直接執行時有效
```

裝成 package 後，Python 無法解析這些模組名稱，必須改為 **relative import**：

```python
from .storage import TaskStorage  # ✅ package 內正確寫法
```

---

## 需要修改的檔案

### `v2/main.py`

將以下 import 改為 relative import：

```python
# 修改前
from storage import TaskStorage
from commands import TaskManager

# 修改後
from .storage import TaskStorage
from .commands import TaskManager
```

### `v2/commands.py`

```python
# 修改前
from report import format_report
from task import Task
from storage import TaskStorage

# 修改後
from .report import format_report
from .task import Task
from .storage import TaskStorage
```

另外 `commands.py` 內部有一行 inline import：

```python
# update_task 方法裡
from datetime import datetime  # 這個是標準庫，不用改
```

### `v2/storage.py`

```python
# 修改前
from task import Task

# 修改後
from .task import Task
```

### `v2/report.py`

```python
from task import Task

# 修改後
from .task import Task
```

### `v2/task.py`

此檔案只 import 標準庫（`datetime`、`typing`），**不需要修改**。

---

## 修改後的驗證步驟

1. 在專案根目錄重新安裝：
   ```powershell
   pip install -e .
   ```

2. 確認 CLI 可用：
   ```powershell
   gtd --help
   ```

3. 確認各功能正常：
   ```powershell
   gtd add --title "Test" --due 2026-12-31
   gtd list --all
   gtd report
   ```

4. 確認在 `v2/` 目錄下直接執行仍然可用（因為有 relative import，需透過 package 執行）：
   ```powershell
   # 從專案根目錄
   python -m v2.main --help
   ```

---

## 注意事項

- `v2/__init__.py` 已存在，不需新增
- `setup.py` 的 entry point 需確認指向 `v2.main:cli`：
  ```python
  entry_points={
      "console_scripts": [
          "gtd=v2.main:cli",
      ],
  },
  ```
- 修改 relative import 後，不能再用 `python v2/main.py` 直接執行，應改用 `python -m v2.main` 或直接用 `gtd`
