# REDMI G Pro 32U 2026：root 教程

这台机器取得的是**运行时 root**：原厂启动链照常启动，安装在用户区的实验应用再触发一次提权。一次完整重启后实测能自动恢复；原厂 Bootloader 仍锁定。以下步骤针对自有设备，32U 以外的型号、其他固件或更新后的内核都要重新验证。

## 1. 确认你连到的是这台 32U

在显示器打开 ADB 调试，按需在屏幕上批准这台电脑。使用 USB，或者在隔离的测试局域网中使用设备实际开放的 ADB 地址：

```sh
adb devices -l
# 仅在显示器已开放该 ADB 端口时使用这一行。
adb connect YOUR_MONITOR_IP:5555
adb devices -l
adb -s YOUR_ADB_SELECTOR shell "id; getprop ro.product.model; getprop ro.product.device; getprop ro.build.version.incremental; uname -r"
```

把 `YOUR_ADB_SELECTOR` 换成 `adb devices -l` 第一列中这台显示器的值。用网络连接时，通常是它的 `IP:端口`；USB 时是序列号。电脑接着其他手机或电视时，每条设备命令都写 `-s`。出现 `unauthorized` 时在显示器确认授权；`offline` 或连不上则先查调试开关、线材和局域网。别从“未连接”推断 root 失败。

匹配目标为 `MiTV-MFFU1`、`beekeeper`、Android 14、`OS3.0.120.0.UFFMAMN` 与 `5.15.148-android14-11-g37010446f523`。同型号不同固件不能套用下文的偏移。普通 ADB 返回 `uid=2000(shell)` 是正常基线；即使另外取得了 root，ADB 也可以仍是普通 shell。

## 2. 从原厂状态复现

先按[固件适配记录](dirtyfrag-adaptation.zh-CN.md)完成离线指纹、DirtyFrag 缓存写入和无害标记三个检查。只有实际得到 **UID 0 的标记**，才继续做 root 通道与重启恢复。通用 DFRoot 在这台机器上停在选择 SU 管理器；直接装上游 APK、Magisk 或 KernelSU 管理器，不能复现本文结果。

自行编译、签名并核实针对本机的实验 APK 后，可用 `adb -s YOUR_ADB_SELECTOR install YOUR_VALIDATED_BUILD.apk` 侧载。首次从显示器桌面手动打开应用并在前台完成标记测试。先验证一次手动 root，再逐个加入开机恢复、ADB 恢复。实测版本使用 Android 的通知访问服务来获得启动机会；如果自己的实现采用这个入口，在显示器上只授予自己审核过的应用。仅注册开机广播不足以覆盖所有启动状态；从未打开或被强行停止的侧载应用尤其需要检查。

本文的实测环境使用了临时的明文 TCP root shell。不要把它接入共享网络或做端口转发。新实现宜优先采用仅设备本地可达的传输（例如仅监听回环地址，并通过已授权的 ADB 转发）；这一改法需要自己验证，原实验没有把它作为验收结果。

## 3. 从 Windows 或 Mac 使用已经存在的 root

若自己的实验版本已经在隔离网络开放了 2323，在同一隔离网段的 Mac 终端可以连接：

```sh
nc -nv YOUR_MONITOR_IP 2323
```

连接后键入 `id`、`getenforce`，再输入 `exit`。已有通道可能没有交互提示，直接输入即可。实测 `id` 返回：

```text
uid=0(root) gid=0(root) groups=0(root) context=u:r:bt_wake-svc:s0
```

Windows 或 Mac 均可用 [probe.py](../scripts/probe.py) 做同样的只读验证：

```sh
python3 scripts/probe.py tcp --host YOUR_MONITOR_IP
```

这条路径假定当前目录是 Skill 目录。核对 `status=root_verified`、`uid=0`、`verified_boot=green` 与 `bootloader=locked`。裸端口可连、应用日志写“成功”、`getenforce` 显示 `Permissive`，单独都不能证明 UID 为 0。`exit` 只关掉这一次连接，不会关监听。也不要把这条通道当成 `adb root` 或假定系统安装了 `su`。

## 4. 区分开机恢复与 ADB 守护

1. 先从已经证实为 root 的同一通道记下 `boot_id` 和 UID。
2. 自己执行一次正常的完整重启。屏幕变黑或待机唤醒不能证明内核重启。
3. 等 Android 桌面和蓝牙服务就绪，检查 `sys.boot_completed=1`。不要手动打开应用触发提权，再用同一核验命令取值。
4. 新旧 `boot_id` 不同、前后均为 `uid=0`，才证明这一次自动恢复。若 UID 只能在手动打开后恢复，查应用启动权限和通知监听服务；若 ID 未变，重做一次完整重启。如果 ID 读不到，保留“未能区分重启与待机”的结论。

ADB 守护是 root 已经起来之后的单独步骤。实测版本会尝试维护调试属性和 `adbd`；屏幕上的调试开关和实际监听状态可能不一致。用 `adb devices -l`、`adb -s YOUR_ADB_SELECTOR shell id` 和脚本的 `adbd`、`adb_tcp_port` 分开核对。ADB 断了而现有 root 通道仍返回 UID 0，优先排查调试守护；ADB 连接正常而 root 通道没有证据，则排查提权链。

## 5. 撤销与失败时怎么停

- 测试前记录应用和调试开关的原始状态。如果自己调整了 ADB 配置，也记录原有端口和 USB 模式。结束后撤回实验应用的通知访问，关闭其开机恢复和 ADB 守护，按需卸载自己侧载的实验应用。
- 完整重启，重新核对之前的 root 通道不再给出 UID 0、ADB 恢复到预期状态。如果发现仍能得到 UID 0，先查是否有其他启动入口或 root 方案。不要为验证结果而恢复出厂。
- 不要读取 `/proc/utopia_mdb/xc`。这台机器实测连读取该调试节点都触发了内核 CFI 崩溃。用 `getprop`、`id`、`getenforce`、`uname` 和已知日志入口做诊断。
- 不要用机器人画面判断 Fastboot。这台 32U 当时 `fastboot devices -l` 没列出目标；Windows 的 Code 43 节点拔光显示器线后仍存在，不能作为显示器的枚举证据。27U 的同平台记录见 [MiTV-Beekeeper-Tools #5](https://github.com/Packeting1/MiTV-Beekeeper-Tools/issues/5)，只作旁证。解锁 Bootloader 可能清空数据；本教程无需解锁或刷写。
