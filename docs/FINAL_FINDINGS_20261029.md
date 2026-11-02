# 国内传统 WAP/WML 存活站点调查 — 最终清单

> **历史记录提示（2026-11-02）：** 下文的 GitHub Actions 运行编号来自已删除的旧仓库（Repository ID `1436882222`），不再对应可打开的新仓库运行页面。原始研究资料保留于私人备份；这些编号只作为历史索引，公开文档中的哈希、方法和结论保持不变。

**快照日期：2026-10-29（UTC+8）；调查状态：R8 已完成。**

> **结论先行：**在本次优先检查的 8 个国内历史 WAP 入口中，发现 **5 个域名**当前仍能公开提供「HTTP 200 + WML 首页 + 从首页实际链接进入的同源 WML 第二页」。另有 **2 个**只能证明 WML 首页还在，**1 个**原历史路径已转向其他服务。这不是中国所有 WAP 站点的穷尽统计，也不等于老手机实机可用。

## 一、最终站点清单（按本轮真实联网证据）

| 站点 / 精确入口 | 首页原站 WML | 同源二级 WML | 实际可见内容 / 限制 |
| --- | --- | --- | --- |
| **书法集** — [http://wap.shufaji.com/](http://wap.shufaji.com/) | **通过**（HTTP 200、WML 1.1） | **通过**：`/0x541B.wml` | “君”字字典、释义与书法内容；Nokia7110 和 S60v3 两种请求画像均复验。独立 HTTPS 连接超时 |
| **我要起名网** — [http://wap.517ming.com/](http://wap.517ming.com/) | **通过**（HTTP 200、WML 1.1） | **通过**：`/helian-xing.wml` | “赫连”姓名字列表；Nokia7110 和 S60v3 画像均复验；表单提交未测试 |
| **易易手机游戏** — [http://wap.ee1234.com/](http://wap.ee1234.com/) | **通过**（HTTP 200、WML 1.1） | **通过**：`/dongzuo-p1.wml` | 动作游戏分类及具体游戏条目；仅验证浏览，未尝试游戏下载 |
| **UC123 导航** — [http://wap.uc123.com/](http://wap.uc123.com/) | **通过**（HTTP 200、WML 1.1） | **通过**：`/s_3457/` | 二级页是跳转新浪移动站的 WML 中转卡片；证明「同源 WML 第二页」，**不证明站外链接可用** |
| **蓝G / Blue G Lab** — [http://wap.yuyangzhou.name/](http://wap.yuyangzhou.name/) | **通过**（HTTP 200、GB2312 WML 1.1） | **通过**：`/m_service/default.wml` 与 `/download/default.wml` | 手机运营商服务选择与下载分类；默认首个链接会打开 WMLScript，不能把它误判为 WML 子页 |
| **天下网** — [https://tx.com.cn/](https://tx.com.cn/) | **通过**（HTTP 200，WML 首页） | **未证实** | 首页 6960 B、1 卡、40 链接；分类 / 服务跳向 HTTP 访客入口，小说栏目 HTTP 502；**没有理由因此强制注册** |
| **CCTV 历史 WAP** — [http://www.cctv.com/wap/index.wml](http://www.cctv.com/wap/index.wml) | **通过**（HTTP 200，WML） | **未证实** | 页面内容和链接指向 **2006 年**新闻，且子栏目链接改用 `wap.cctv.com`，不同于所测 `www.cctv.com` 原站；不能声称央视 WAP 新闻仍在更新 |
| **IP138 历史列车 WML** — [http://qq.ip138.com/train/search_train.wml](http://qq.ip138.com/train/search_train.wml) | **未证实** | **未证实** | 精确路径 HTTP 301 到 HTTPS；HTTPS 随后 HTTP 302 转向 `dnsdblookup.com`；未自动跟随，也未获得 WML 正文 |

**通过的含义：**这里是本调查研究者依据原始 HTTP 响应、MIME、body SHA-256、冻结 R5 解析和（适用时）独立 WaveNav 解析作出的**人工 HTTP/WML 证据判定**。它不是 CI 自动颁发的等级。仓库原 `pipeline` 的 `A_origin`、`A_navigation` 机器字段继续保持 `PENDING`，防止后续自动采集误把成功工作流当成成功网站。本清单不对 WSP/WDP、实体机或完整 WML DTD 一致性签署通过。

**统计口径：**5 个「HTTP WML 双页可浏览」域名、2 个「原站 WML 首页但二级未证实」域名、1 个「精确历史路径重定向、WML 未证实」域名。多个网站存在互相引用的友情链接，**不代表五名互相独立的经营者或五种独立后端**。

## 二、独立交叉验证与可复核证据

- **采集：**固定 Nokia 7110 与 S60v3 请求头；公开 GET、DNS 公网 IP 固定、无代理、无自动重定向、无登录、无表单提交；响应头 / 正文 / 时间 / IP / SHA-256 留存在限期私有 GitHub Actions 工件中。
- **第一解析器：**仓库冻结 R5，解析从实际原站获得的字节，验证同源页面的真实导航链接。
- **独立解析器：**[WAP Labs / WaveNav](https://github.com/dills122/wap-labs)，固定源码提交 `9cd7ab97dc6752fc1616feb3505a58603f6a45df`；以独立 Rust WML 引擎加载并生成渲染帧。R7 六份、R8 七份和蓝G 三份（经严格 GB2312→Unicode 文本解码）的校验与加载结果分别为 **6/6、7/7、3/3**。合计 16 个验证输入；其中存在同一 URL 的不同时间/UA 采集，**不是 16 个互不相同的网页**。
- **证据主入口：**R6 公共栏目及历史入口采集（旧库 Actions 运行 `40846429748`）、R6/S60 复核（旧库 Actions 运行 `40846746719`）、R7 独立复核（旧库 Actions 运行 `40847596595`）、R8 余下候选（旧库 Actions 运行 `40848278136`）、R8 Rust 独立复核（旧库 Actions 运行 `40848787056`）、蓝G 两条公开 WML 导航（旧库 Actions 运行 `40848675568`）、蓝G GB2312 独立复核（旧库 Actions 运行 `40848992644`）、天下网匿名访客尝试（旧库 Actions 运行 `40845259067`）。
- **原始工件保留期：**多为 3 天；可能含 `Set-Cookie`，不公开、也不写入 Git 历史。审计者应在工件有效期内保留受控副本；本仓库保存脱敏的原始哈希、运行 ID 和状态，供后续对照。R8 一次 Rust 脚手架因 `replace` 参数类型错误编译失败，下一提交已修复并完整重跑，不能把该编译失败解释为 WML 失败。

### R8 新增原始字节 SHA-256

| 捕获正文 | SHA-256 |
| --- | --- |
| 易易手机游戏首页 | `2d6a001b69b55cfccc8f895cddf89e3e9efeb1cf0c5c03f63b7030994a81a818` |
| 易易动作页 | `dd2df6f440f3c7a3e761d181b5fd7702de32be254cb5d44f88b1ec1b9153c4e3` |
| UC123 首页 | `93261ba17104a3f46faa9cc1a1a4b891add97301ca930cd77d789ac5e1271f99` |
| UC123 中转页 | `519ce2e7a7532c42e7653d146c438411091dccaeafd6e029a069b049475cb530` |
| CCTV 2006 历史 WML 首页 | `86e8f7205f14f030c754c305d6cfa0a2a6784792f000816eda040f916ae4deef` |
| 我要起名网 S60 首页 | `138946dc46ea189b058d41cedc4b684a9ab48cb7a958db434113a115a3ff3819` |
| 我要起名网 S60 子页 | `0bcb8c9140e87f92489690aced907f82cd481a4b9489e5c94b4fce91c8e82a06` |
| 蓝G GB2312 首页 | `97deed8c5332a314e8cb163ce61ff5a6576358427c015f6180f4e8a8bd227a6a` |
| 蓝G GB2312 手机服务页 | `93342fd63493503b096a470671a7e8bd6f4fc7ddee3961136083c5022335c11d` |
| 蓝G GB2312 下载分类页 | `14b631d4ff22792183c375b0f001e49e52c418bf4036b09808a4971dcaaeeea3` |

早期书法集 / 我要起名网 Nokia7110 页面、天下网及其他样本的哈希与取证详情见 [R6/R7 原始记录](LIVE_CAPTURE.md)。

## 三、旧手机真实可用性：另行判断

| 设备环境 | 从本轮证据能作何判断 | 尚缺什么 |
| --- | --- | --- |
| **Nokia E63 / S60v3** | 厂家规格支持 HTTP、WAP2.0 和 WML；已有使用 E63 UA 的真实 HTTP/WML 成功采集，是**较有希望**的实体机复测平台 | 真机联网、浏览器是否正确处理中文编码与 WML、能否选中链接、完整页面布局 |
| **Nokia 7110 / WAP1.x** | Nokia7110 UA 已通过服务器响应测试，**但 UA 不是实机**。该世代通常依赖电路交换/SMS 承载与 WAP 网关，而不是直接用现代 HTTP 栈访问任意站点 | 可用的数据承载／拨号环境、WSP/WDP 网关、WMLC 编码与旧机 deck 大小限制、中文字体与实机操作 |
| **WAP Labs 网关** | 公共网关主要供作者允许的第一方测试域使用，不应未经许可拿它中转这里的任意第三方网站 | 若需要原生 WSP/WDP，应另建合法受控网关或仅使用授权的实验 origin |

参考设备资料：[Nokia E63 设备规格](https://www.somanuals.com/html/24/Nokia-ESERIES-E63-User-Manual.html)、[Nokia 7110 手册](https://www.somanuals.com/html/24/Nokia-7110-User-Manual.html)、[Kannel 对 Nokia 7110 的网关配置说明](https://www.kannel.org/compatibility.shtml)。

**重要限制：**没有对实际 Nokia 7110/E63 做操作；没有取得此五站原生 `application/vnd.wap.wmlc` 编译数据，也没有完成真实 WSP/WDP 会话；没有验证小游戏下载安装、表单 POST、登录、跨域跳转或动态服务是否仍有实际效果。特定时间地点的运营商可用性亦不在本研究范围。

## 四、收尾决定

- **研究问题「2026 年是否仍有国内传统 WAP/WML 网站可浏览多个页面？」答案：是。** 五个域名已取得原站 HTTP 双页证据并经过两套独立 WML 解析验证，且内容类别确实不同。三处（书法、起名、游戏下载目录）具备可以直接阅读的实质子页；导航中转站要单独注明。
- **本轮 R8 到此完成。** 保持冻结 R5 和现有正式采集工具，不继续创建 R9/R10、不开启周期性探测，也不为天下网注册账号。
- **实体旧机可用性列为独立的「待真机验收」事项**，不阻止本次「在线 WML 存活」研究结项，也不虚报为已经解决。
