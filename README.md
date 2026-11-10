# REDMI G Pro 32U 2026：运行时 root 实测与 Codex Skill

在一台 **REDMI G Pro 32U 2026**（`MiTV-MFFU1 / beekeeper`）上，用 DirtyFrag / DFRoot 做了固件适配。实测在 **Bootloader 仍锁定**时取得 `uid=0(root)`，并在一次完整重启后由应用自动恢复。这里记录操作过程、失败分支和判定方法，并提供一个只读核验脚本。

| 验证项 | 结果 |
| --- | --- |
| Android / 固件 | Android 14 / `OS3.0.120.0.UFFMAMN` |
| 内核 / 安全补丁 | `5.15.148-android14-11-g37010446f523` / `2025-07-05` |
| 运行时权限 | 实测 `uid=0`、`u:r:bt_wake-svc:s0`、SELinux `Permissive` |
| 启动状态 | Verified Boot 为 `green`，Bootloader 为 `locked` |
| 跨重启 | 实测应用重新取得 root；每次开机的结果仍以实测为准 |
| 永久 root | 本机未解锁 Bootloader，也没有刷入 Magisk |

- [中文教程：连接、使用、验证与撤销](skills/redmi-gpro32u-root/references/root-guide.zh-CN.md)
- [固件适配记录：从 DirtyFrag 到 root 进程](skills/redmi-gpro32u-root/references/dirtyfrag-adaptation.zh-CN.md)
- [Codex Skill](skills/redmi-gpro32u-root/SKILL.md) · [只读核验脚本](skills/redmi-gpro32u-root/scripts/probe.py)

本仓库发布教程、Skill 和只读核验工具。实验版安装包、预编译提权程序和厂商固件不随仓库发布。从原厂状态首次复现，需要自行完成适配；上游 DFRoot 的通用 APK 不是本机实测的实验版。

## 使用 Codex Skill

在 Codex 中使用 `$skill-installer`，指定 [Skill 的 GitHub 目录](https://github.com/RickeyRen/redmi-gpro32u-root/tree/main/skills/redmi-gpro32u-root)。也可参考 [Codex 官方文档](https://developers.openai.com/codex/skills)，将整个 `redmi-gpro32u-root` Skill 目录复制到项目的 `.agents/skills/`。安装后在 Codex 中输入：

> 用 $redmi-gpro32u-root 核验我的 32U 固件、当前 root 状态和重启后是否恢复。

## 命令行快速核验

需要 Python 3；使用 ADB 模式时，另需 [Android Platform-Tools](https://developer.android.com/tools/releases/platform-tools)。克隆仓库并进入目录后，将占位值替换为自己的设备信息：

```sh
adb devices -l
python3 skills/redmi-gpro32u-root/scripts/probe.py adb --serial YOUR_ADB_SELECTOR
python3 skills/redmi-gpro32u-root/scripts/probe.py tcp --host YOUR_MONITOR_IP
```

Windows 可用 `python` 代替 `python3`。最后一条只用于已存在的授权 root 通道；它不会启用监听端口。退出码 `0` = 固件匹配且该通道返回 UID 0；`1` = 固件匹配但该通道非 root；`2` = 无法完成核验或固件不匹配。

## 来源与许可

提权研究来自 [V4bel/dirtyfrag](https://github.com/V4bel/dirtyfrag) 和 [diabl0w/DFRoot](https://github.com/diabl0w/DFRoot)。本文的固件适配和验证结果来自一台 32U 的实测。本仓库原创文档与核验工具采用 [MIT 许可](LICENSE)；上游 DFRoot 及其衍生代码仍受各自的许可证约束。
