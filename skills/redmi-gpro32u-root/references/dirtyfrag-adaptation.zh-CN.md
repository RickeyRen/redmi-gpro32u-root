# DirtyFrag / DFRoot：32U 固件适配笔记

目标为 `OS3.0.120.0.UFFMAMN` 的 32U，Android 14，内核 `5.15.148-android14-11-g37010446f523`。这是实测链路的技术记录，未把实验 APK 整理为可从零独立构建的发行版。文件位置、偏移、模块或触发条件都应在自己的同版系统上离线核对。

## 1. 固定输入，先验证原语

- 从与显示器完全一致的官方 OTA 提取原始镜像和 vendor 文件，记录 SHA-256。实测原始 `boot.img` 为 78,643,200 字节，SHA-256 为 `2da03026766b4fbf4d01f468a8b3d7f5b9572ee0f546cd0ce683d043b4483e42`，仅作离线对照，本路线不刷写它。
- 对照 [DFRoot 源码基线](https://github.com/diabl0w/DFRoot/commit/7a6513a69ce4c1a90b68d857c26347bf166ffe10) 和 [DirtyFrag 上游研究](https://github.com/V4bel/dirtyfrag)。本机所用的 `4.7.4-32u-*` 是实验版本名，不是建议寻找的上游发行版。
- 该内核的 `CONFIG_XFRM_USER`、`CONFIG_INET_ESP` 与 `CONFIG_INET6_ESP` 都是 `y`，系统可见 `android.net.IIpSecService`。这支持选择 DirtyFrag 的 ESP 路线；仅凭内核版本或这些配置不能排除补丁回移。GhostLock 在这台内核上找到了可疑原语，但缺少 BTF 及所需偏移，没有用它取得 root。
- 上游的缓存写入是原语，后续要选能执行、能触发的目标。我们的桥接实验使用 `crash_dump64` 的页缓存和 `splicehelper`，然后写入 vendor 脚本的页缓存。旧的 `mtk_logwrapper` 变体把当时的进程 PID 编进程序，跨重启会卡住；最终的开机恢复流程不等待这个 PID。

## 2. 用标记验证真正的 root 执行域

在该版 `/vendor/etc/init/hw/init.mt9655.rc` 中，`sys.boot_completed=1` 且 `bluetooth.wake_up_rc` 触发时，会启动一次 `bt-wakeuprc`。它通过 `/vendor/bin/sh` 运行 `/vendor/bin/update_wakeup_rc.sh`，域为 `u:r:bt_wake-svc:s0`。

第一次只替换该脚本的页缓存内容，写一个标记：

```sh
#!/vendor/bin/sh
id >/mnt/vendor/tmp/gpro32u-id
cat /proc/self/attr/current >/mnt/vendor/tmp/gpro32u-context
```

这是目标脚本的**内容示例**，不是向只读 vendor 分区复制文件的命令。实验的原脚本窗口为 160 字节：用 LF 换行，并在末尾用注释补到目标窗口，不越界；写前验证大小和内容，写后验证补丁进入预期目标。只看到写入成功还不够。清除自己的旧标记再测，触发后实际读到新标记的 UID 0 和 `bt_wake-svc`，才通过。普通 ADB 没权限读取时，用受控的日志或标记检查方式验证，不要用扩大目录权限来猜测。

## 3. 让属性真正更新

仅重启 MiBluetooth 并不能让 init 重跑脚本。日志显示它读取并重用了相同的遥控器列表，属性没有产生新的变化。实测方案先改变广播接收端的识别分支，再给该包一个受控的测试事件：

| 阶段 | 这台 32U 的证据与验收 |
| --- | --- |
| 定位接收端 | 目标 APK 为 `/system_ext/app/MiBluetooth/MiBluetooth.apk`。离线检查 `RcManager$1.onReceive` 对 `HID_INFO` 的处理，以及 `GuangDianRc.isGenInstance` 的判定。 |
| 核对页缓存窗口 | 本样本的 `classes.dex` 是 ZIP 内可直接定位的条目，数据从 `0xf5c` 开始；`isGenInstance` 指令偏移为 DEX 内 `0x2fc0d8`，合计 APK 偏移 `0x2fd034`。适配把该方法改为返回真。先检查原指令、条目存储方式与长度；偏移只是实测样本坐标，不能盲写。 |
| 发送测试事件 | 等蓝牙服务就绪，把 `android.bluetooth.input.profile.action.HID_INFO` 发给 `com.mi.bluetooth`，携带测试用的本地管理地址作为 `BluetoothDevice.EXTRA_DEVICE`，让属性值不同于前一次；实验也传入设备 PID/VID 参数。不要删除真实遥控器配对来制造变化。 |
| 确认执行 | 顺着日志检查接收、地址保存、属性更新与 init 服务；最终核对新标记。广播发出、页缓存修改或软件界面显示成功，任何一项都不足以作为 root 证据。 |

如果只见到页缓存写入而没有新标记，先查进程是否读取了补丁后的指令、事件是否被包接收、属性值是否真的改变。做有次数上限的重试，不要循环重启系统服务或改真实遥控器地址。

## 4. 把验证过的执行域用于 root，再验证恢复

本机实测顺序为：MiBluetooth DEX 页缓存阶段 → 模块兼容阶段 → 脚本页缓存阶段 → 新的 HID 事件 → 单独验证 UID。最早试了 `edma.ko`，后改为 `mtk_test_cdev.ko`，对应 DFRoot 的 `android14-5.15` KMI；实测 APK 用这个阶段的日志作为进入触发步骤的门槛。最终实验脚本先尝试加载模块，再由 **vendor init 的 root 脚本**启动测试 shell。脚本允许加载失败后继续；后来抽查时未见对应模块已加载，也没有 `/dev/df`。能够确认的是这个脚本的 shell 返回 UID 0，不能据此宣称 KernelSU、兼容模块加载或系统级 `su` 已实现。

手动阶段通过后，应用才加入开机回调。实测版保留标准 Android 和小米启动事件，同时使用获得通知访问权限的 `NotificationListenerService` 在系统绑定时启动一次恢复。它等蓝牙可用，重新走上述缓存阶段和属性触发，再处理 ADB 守护。页缓存不会跨重启保留，保留的是用户区应用和它的启动资格。实测没有依靠替换原厂桌面。

每次实验保留一份可脱敏的结果：原始镜像哈希、适配版本、写入阶段、标记 UID 和 SELinux 域、外部 shell 的 UID、重启前后 `boot_id` 是否变化。完整的连接、验收与撤销见[主教程](root-guide.zh-CN.md)。
