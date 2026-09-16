# gtd-cli

終端機裡的 Getting Things Done：把事情丟進 inbox → 決定下一步行動 → 標上情境（@home、@office…）→ 每週做一次 review。一個 JSON 檔、一個 `gtd` 指令，沒有帳號、沒有同步、沒有通知。

```
$ gtd add --title "寫季報" --project work --priority 4 --due 2026-09-20 --context @office
✅ Added: [1] 寫季報 (Project: work, Priority: 4, Due: 2026-09-20, Context: @office)

$ gtd next --context @office
ID   | Title                  | Project      | Ctx      | Pri | Due          | Status       | Created
-----------------------------------------------------------------------------------------------------
1    | 寫季報                  | work         | @office  | 4   | 2026-09-20   | next-action  | 2026-09-16

$ gtd review
=== Weekly Review — 2026-09-16 ===

⚠️  Overdue (0)
  nothing overdue

📅 Due in the next 7 days (1)
  [1] 寫季報 (work) @office due 2026-09-20

📥 Inbox to process (decide: next-action / waiting / done / remove) (2)
  [2] 買牛奶 @errands
  [3] 回信給房東
...
```

## 安裝

```bash
pip install git+https://github.com/Jadiouo/gtd-cli.git
# 或 clone 後
pip install -e .
```

需要 Python 3.9+，唯一的相依套件是 `click`。任務存在 `~/.gtd/tasks.json`，可用環境變數 `GTD_FILE` 或 `gtd --file PATH` 改位置（多個清單、放進 Dropbox 都行）。

## 指令

| 指令 | 用途 |
|---|---|
| `gtd add --title T [--project P] [--priority 1-5] [--due YYYY-MM-DD] [--context @c]` | 捕捉：新任務進 inbox |
| `gtd list [--status S] [--project P] [--priority N] [--context @c] [--due-before D] [--all]` | 列表；預設只顯示 inbox 與 next-action，逾期任務標 ⚠️ 並排最前 |
| `gtd next [--context @c] [--project P]` | GTD 的「下一步行動清單」：現在、在這個情境下能做的事 |
| `gtd update --id N [--title/--project/--priority/--status/--due/--context ...]` | 修改；`--no-project`、`--no-due`、`--no-context` 清除欄位 |
| `gtd check --id N` | 標記完成 |
| `gtd remove --id N [--id M ...] [--force]` | 刪除，預設先確認；找不到的 ID 會列出並詢問是否繼續 |
| `gtd undo` | 還原上一次寫入前的備份（每次存檔前都會複製一份 `tasks.json.bak`） |
| `gtd show --id N` | 單一任務細節 |
| `gtd report [--project P]` | 統計：各狀態數量、專案分布、逾期警示 |
| `gtd review` | 每週回顧：逾期、7 天內到期、待處理 inbox、waiting-for、14 天沒動的任務、本週完成 |

狀態流：`inbox → next-action → done`，卡在別人手上的用 `waiting`。情境是 GTD 用來回答「我現在人在這裡、手上有這些工具，能做什麼」的標籤：`@home`、`@office`、`@phone`、`@errands`——`gtd next --context @phone` 就是打電話清單。

## 設計

```
gtd_cli/
  main.py      click 指令定義、輸出格式、退出碼（2 = 參數錯誤，1 = 找不到 / 執行錯誤）
  commands.py  TaskManager：所有業務邏輯（篩選、排序、review 彙整），不碰 I/O
  storage.py   TaskStorage：JSON 讀寫、原子寫入（先寫 .tmp 再 os.replace）、自動備份
  task.py      Task 資料模型與驗證；from_dict() 對舊版檔案向下相容
  report.py    純函式：把任務清單 / review dict 排成文字
```

- **排序規則**：逾期優先 → priority 5→1 → 到期日近的優先 → id。這是 `list` 和 `next` 共用的。
- **向下相容**：v1 的檔案沒有 `due_date`、v2 的沒有 `context`，`from_dict()` 全部當成 `None`；ID 不重複使用（刪掉 2 之後新任務是 3，不會又變成 2）。
- **錯誤處理**：所有錯誤走 `❌ Error:` 前綴輸出到 stderr，參數錯誤退出碼 2、其他 1，方便在 shell script 裡判斷。

前兩個版本是用 Spec-Driven Development 做的：先寫 SDD，再照規格實作，v2 的需求是由 agent 讀 v1 程式碼後產生的。那段過程與設計決策保留在 [`docs/design-notes.md`](docs/design-notes.md)，規格文件在 `docs/sdd_v1.md`、`docs/requirements_v2.md`、`docs/sdd_v2.md`；v1 程式碼在 `legacy/v1/`。

## Changelog

**3.0.0**
- 重構成正式 Python 套件（`pyproject.toml`、`gtd_cli/`、相對匯入），移除 `sys.path` hack
- 新增情境（`--context`）、`gtd next`、`gtd review`、`gtd undo`
- 存檔改為原子寫入 + 自動備份；`GTD_FILE` / `--file` 可指定任務檔
- ID 不再重複使用
- pytest 測試 15 條 + GitHub Actions

**2.0.0** — 截止日期、`--due-before` 篩選與逾期警示、`report`、批次刪除與確認流程
**1.0.0** — add / list / update / check / remove / show

## 開發

```bash
pip install -e ".[test]"
python -m pytest
```

## 授權

MIT
