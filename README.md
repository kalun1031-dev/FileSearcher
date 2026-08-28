# FileSearcher · 轻量文件搜索

一款 Windows 桌面本地文件搜索工具，参考 [Everything](https://www.voidtools.com/zh-cn/) / [Listary](https://www.listary.net/) 的使用习惯设计：**先建索引、后秒搜**，主打轻量、快速、颜值高。

用 Python + PySide6 编写，打包后双击即用，无需安装 Python 环境。

---

## 下载

| 平台 | 说明 |
|------|------|
| Windows 10 / 11 | 前往 [Releases 发布页](../../releases) 下载 `FileSearcher.exe`，双击即可运行 |

> 单文件绿色版，无需安装。首次启动会自动建立全盘索引（约几十秒），之后搜索毫秒级响应。索引缓存在 `%APPDATA%\FileSearcher\`，删除该文件夹即彻底卸载。

## 功能特性

### 索引式搜索，毫秒级响应
- 基于 `os.scandir` + 多线程目录队列并行扫描，比传统 `os.walk` 快 2~3 倍
- 索引持久化缓存，重启秒级加载
- 支持定时自动增量刷新，可随时手动重建
- 自动跳过符号链接 / junction / 系统目录 / `$` 前缀目录，避免死循环

### 6 种匹配模式 + Everything 风格高级语法

| 语法 | 作用 | 示例 |
|------|------|------|
| 普通关键词 | 文件名包含（多词 AND） | `年度报告` |
| `!关键词` | 排除关键词 | `报告 !草稿` |
| `*.扩展名` / `ext:` | 按扩展名（可多个） | `*.pdf`、`ext:doc,xls` |
| `size:` | 按大小（支持 `> < >= <=` 及区间） | `size:>100MB`、`size:1MB-10MB` |
| `path:` | 按路径过滤 | `path:下载` |
| `folder:` / `file:` | 只搜文件夹 / 文件 | `folder:项目` |
| 匹配模式 | 包含 / 精确 / 开头 / 结尾 / 通配符 / 正则 | 下拉切换 |

### 现代化界面（v2.0 全新设计）

- **三栏布局**：左侧分类导航（带实时计数）+ 磁盘位置筛选（显示剩余空间）；中部搜索与结果；右侧文件预览面板
- **亮 / 暗双主题**一键切换，全局同步（含菜单、滚动条、对话框）
- **自绘结果行**：分类彩色图标、关键词黄色高亮、路径超长自动省略
- **点击列头排序**：修改时间 / 名称 / 大小 / 路径，升降序任意切换
- **空状态引导**：无结果时展示搜索语法速查
- **分类 / 磁盘客户端过滤**：搜索后切换分类零延迟，不再重扫索引

### 实用功能

- 🖼️ **文件预览面板**：图片缩略图 + 名称 / 路径 / 类型 / 大小 / 修改时间
- 🖥️ **系统托盘常驻**：关闭窗口最小化到托盘
- ⌨️ **全局快捷键 `Ctrl + Shift + F`**：任何界面下呼出 / 隐藏窗口
- 📜 **搜索历史**：输入框下拉最近 15 条关键词，支持清空
- 📊 **选中统计**：状态栏实时显示选中数量与总大小
- ⇩ **导出 CSV**：当前结果一键导出，Excel 直接打开
- ⚙️ **设置中心**：索引范围 / 排除目录 / 自动刷新 / 防抖延迟 / 结果上限 / 托盘 / 预览面板
- 🔒 **本地运行**：无网络请求、无遥测，索引只存在本地

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl + Shift + F` | 全局呼出 / 隐藏窗口 |
| `Enter` | 立即搜索 |
| `Ctrl + F` / `Ctrl + L` | 聚焦搜索框 |
| `Esc` | 清空搜索 |
| `F5` | 重新搜索 |
| `Ctrl + E` | 打开所在文件夹 |
| `Ctrl + Shift + C` | 复制完整路径 |
| `Delete` | 删除文件（带确认） |
| `Ctrl + Q` | 退出程序 |

## 从源码运行

```bash
# 依赖
pip install PySide6

# 运行
python main.py
```

可选依赖（仅重新生成图标 / 打包时需要）：

```bash
pip install pillow pyinstaller
```

### 从源码打包 exe

```bash
# 生成应用图标
python make_icon.py

# 打包（单文件夹版）
python -m PyInstaller --noconfirm --windowed --onedir \
    --name FileSearcher --icon icon.ico \
    --distpath . --workpath build --specpath . main.py

# 打包（单文件版，适合发布）
python -m PyInstaller --noconfirm --windowed --onefile \
    --name FileSearcher --icon icon.ico \
    --distpath release --workpath build --specpath . main.py
```

### 运行自动化测试

```bash
python test_search.py
```

离屏（offscreen）模式验证搜索全链路：回调封送、分类过滤、大小语法、错误路径不卡死。

## 项目结构

```
├── main.py                    # 程序入口（依赖自检 + 全局字体/图标）
├── make_icon.py               # 生成 icon.ico（打包前运行一次）
├── test_search.py             # 离屏自动化回归测试
├── 启动搜索.bat                # 双击启动（优先 exe，回退 Python）
├── icon.ico                   # 应用图标
└── file_searcher/
    ├── main_window.py         # 主窗口：三栏 UI、自绘列表、全局快捷键
    ├── theme.py               # 亮/暗主题系统（调色板 + QSS 生成器）
    ├── indexer.py             # 索引引擎：scandir 多线程扫描 + 缓存
    ├── searcher.py            # 搜索匹配器：高级语法解析 + 并发丢弃
    ├── preview_panel.py       # 右侧预览面板
    ├── settings_dialog.py     # 设置对话框
    ├── settings.py            # 设置持久化
    └── utils.py               # 工具函数（格式化/分类/打开文件）
```

## 技术要点

- **跨线程 UI 更新**：搜索在工作线程执行，结果经 `QObject` 信号（QueuedConnection）封送回主线程，杜绝 `QTimer` 在无事件循环线程中永不触发的坑
- **搜索代际 ID**：连续输入时旧搜索的回调自动丢弃，防止慢查询覆盖新结果
- **统一轮询**：索引进度 / 分类统计 / 状态栏由单个 400ms 定时器驱动，无跨线程回调
- **防抖 + 即时过滤**：输入 150ms 防抖触发搜索；分类 / 磁盘筛选在客户端完成，零延迟

## 已知限制

- 仅支持 Windows（全局快捷键、磁盘扫描依赖 Win32 API）
- 只索引文件名，暂不支持文件内容搜索
- 图片预览加载超大文件（>80MB）时自动跳过

## License

[MIT](LICENSE)
