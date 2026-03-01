# 📚 一七小说书源 - legado自动维护版

> 针对 [一七小说 (1qxs.com)](https://www.1qxs.com) 的 **legado（阅读3.0）** 书源  
> 由 GitHub Actions 每日自动验证 & 更新，无需手动维护

---

## ⚡ 一键导入

在 **legado（阅读3.0）** App 中，按以下步骤导入：

```
我的 → 书源管理 → 右上角菜单 → 网络导入
```

粘贴以下链接：

```
https://github.com/cloudflare-01/1qxs-book-source/blob/main/sources/1qxs.json
```

## ✨ 功能特性

| 功能 | 状态 |
|------|------|
| 关键词搜索 | ✅ |
| 书库浏览 | ✅ |
| 书籍详情 | ✅ |
| 目录获取 | ✅ |
| 章节正文 | ✅ |
| 每日自动验证 | ✅ |
| 自动更新时间戳 | ✅ |

---

## 🔄 自动更新机制

GitHub Actions 每天 **北京时间 08:00** 自动运行：

1. 访问目标网站各关键页面
2. 验证书名、作者、目录、正文等 CSS 选择器
3. 更新书源 `lastUpdateTime` 时间戳
4. 自动提交变更并推送到仓库
5. 生成验证报告（见 `logs/validation_report.md`）

---

## 📂 项目结构

```
.
├── sources/
│   └── 1qxs.json              # legado 书源文件（主要文件）
├── logs/
│   └── validation_report.md   # 最新验证报告
├── validate.py                # 书源验证脚本
└── .github/
    └── workflows/
        └── update.yml         # GitHub Actions 定时任务
```

---

## 🛠️ 手动触发更新

进入仓库 → **Actions** 标签 → **📚 一七小说书源自动维护** → **Run workflow**

---

## ⚙️ 规则调试指南

如遇书源失效，查看 `logs/validation_report.md` 中的报告，找到 ❌ 的项目。

**常见问题排查：**

- **搜索失效** → 检查 `searchUrl` 格式，在浏览器中手动测试搜索 URL
- **目录不显示** → 打开书籍页面，右键检查目录 `<ul>/<li>` 的 class 名
- **正文为空** → 检查 `#content` 或 `.content` 是否存在，可能已改为动态加载

---

## 📜 免责声明

- 本项目仅供学习研究使用
- 请遵守目标网站的 `robots.txt` 及服务条款
- 不得用于任何商业用途
- 如侵权请联系删除
