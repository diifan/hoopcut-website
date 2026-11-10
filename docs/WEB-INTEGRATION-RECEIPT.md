# 官网 → Supabase staging 联调回执

2026-11-09，官网会话接续 SERVER-IMPLEMENTATION-RECEIPT.md 的最新部署回执。

## 本轮实际完成

- 通过授权私有 SSH 通道只取得 staging 接收密钥，保存于112仓库外受限目录（0700/0600）；未拷贝生产密钥、service_role 或 AF Dev Key。
- 真实浏览器加载标准构建页面，实际触发 page_view、HTML5 video_play、下载 CTA；通过官网实际 handler/collect 转发到已部署的 web-attribution-events。
- 3个事件均获HTTP200 accepted；通过109既有管理工具执行只读SQL，确认3条staging持久行。重复提交返回3个duplicate；修改原payload、错误production环境、额外raw_ip字段均拒绝。SQL复核仍只有3条，原campaign未被覆盖。
- 修正首屏脚本自动播放误判user：默认banner播放记录autoplay，用户明确选择球员后记录user。
- Web字段校验与接收端对齐：严格UTC时间格式、拒绝原型属性事件名及非字符串路径。
- 新增受限本地staging测试服务 server/attribution-preview.js，支持Unix socket；没有将秘密写进构建产物。

## 证据

- docs/evidence/browser-live-staging.json：6次真实BFF请求回执，3个accepted，3个duplicate及拒绝结果。
- docs/evidence/bff-persisted-staging.json：SQL查询的对应3条staging行和原campaign/播放触发类型。
- tests/qa_attribution_live.py：需明确设置HOOPCUT_STAGING_SECRET_FILE才可运行，读取staging字段；会产生独立staging测试事件，不是默认单测。
- tests/attribution.test.js：6项后端测试通过；tests/qa_attribution.py：10项合成交互检查通过；标准构建及39页SEO检查通过。

## 真实限制

本机新TCP预览端口访问超时，浏览器通过HTTP-over-Unix-socket transport bridge访问实际Node服务。只有浏览器到本机服务的传输换成bridge；BFF到Supabase为真实HTTPS，不是mock，也不是已经在Vercel部署的公网验收。

仅测试staging，没有production合成事件。生产官网未部署这一版。真实YouTube iframe网络播放事件仍未验收；本轮验证的是首页真实HTML5视频。OneLink仍未提供，下载保持app_store_fallback，不宣称AF安装闭环。实际HTTP压力与公网Vercel入口行为待发布前/后按范围验证。

## 当前配置与下一步

接收端已经ACTIVE，不再把“函数404/密钥待提供”作为当前阻塞。Header确定为x-hoopcut-web-secret。官网生产环境仍需在正式部署时通过私有配置通道设置production对应secret、rate secret、准确origin；不能把staging配置用于production。

原协议第10节继续维护部署/联调状态。后续网站发布仍遵守版本审核；AF侧继续交付真实OneLink及安装证据，不以官网点击或accepted回执替代安装。

## 109 → 112 最后接线需求（2026-11-10）

用户已要求将官网待办集中更新在本文件。以下更新覆盖上文历史状态中的“OneLink仍未提供”：109 已创建并验证真实模板，不再等待链接。此处只交接需求，不表示112已经开发或上线。

### 112 负责：官网最后接线

正式配置（staging/production 同模板，事件环境仍严格隔离）：

```dotenv
HOOPCUT_ONELINK_BASE_URL=https://hoopcut.onelink.me/SDN0
HOOPCUT_ONELINK_ALLOWED_HOSTS=hoopcut.onelink.me
HOOPCUT_SMART_SCRIPT_SRC=https://onelinksmartscript.appsflyer.com/onelink-smart-script-latest.js
```

模板 HoopCut Main / SDN0，绑定 HoopCut iOS id6824860341。不要使用 onboarding 的 my_first_link / my_media_source 短链。官方脚本本次实测2.10.4，latest不是锁版。

1. **修复 assets/attribution.js 的 destination() 参数丢失**：真实Smart Script返回链接后，重建URL不能丢掉 `af_js_web=true` 和 `af_ss_ver`。仅保留可信SDK生成值（版本形如2_10_4，校验 `^\d+_\d+_\d+$`），不要从入站query透传或写死SDK版本。
2. 保持业务参数：`pid=hoopcut_website`；`c=session_campaign`；`af_channel=session_source`；`af_sub1=click_id`；`af_sub2=cta_id`；`af_sub3=session_medium`；`af_sub4=session_content`；`af_sub5=environment`。同次下载事件click_id必须与链接af_sub1一致，每次实际点击生成新ID，重试复用event_id。
3. 校验HTTPS、host=hoopcut.onelink.me、path=/SDN0，无URL账号密码；继续拒绝任意query、gclid、完整referrer、IP、visitor_id等非协议字段。不要原样透传SDK全部query。
4. 用真实SDK完成staging联调，不只mock。正常事件destination_type=onelink；加载/生成/校验失败立即fallback到 `https://apps.apple.com/app/id6824860341`，标记app_store_fallback。埋点异步，不等待回传才跳转。
5. 正式发布时通过私有配置通道取得production对应服务端secret，配置准确origin/rate secret，沿用 `x-hoopcut-web-secret`。不把staging凭据用于生产，不将任何秘密放前端、文档、Git。按官网原有发布审核流程部署，不将本交接视为绕过发布流程。
6. 验收公网入口/CSP/SDK加载、BFF落库与幂等、实际YouTube播放、正常跳商店及失败fallback；本机Unix-socket测试不能代替公网验收。生产不灌合成归因事件。

### 112 完成后在本文件回填

- commit、部署地址、部署时间与环境；未上线则明确标注。
- staging同一点击的Web事件与最终OneLink URL（click_id=af_sub1，af_sub5=staging），真实SDK版本和加载证据。
- BFF→Supabase回执/持久记录、失败fallback和公网/YouTube验收结果；未验项目不要标完成。

### 109 负责，不派给112

- AF实际安装首次打开验证、原始记录af_sub1/API数据权限和click lookback核对。
- AF安装数据→Supabase、App appsflyer_id→installation_id持久关联及归因面板。
- 缺失/受限归因保留unknown或aggregate，不通过IP+时间猜身份。install是首次打开，不是商店下载完成。

109当前已验证：模板已保存，官方真实脚本生成链接；iPhone/桌面请求均301至正确App Store。尚未验证真实安装闭环、未配置已安装App直接唤起。

证据及详细回执（既有109交接，不是要求112另建协议）：
`/data/swi-algo/hoopcut/handoffs/HoopCut-Web-AF-Attribution-2026-11-09/AF-ONELINK-HANDOFF.md`

唯一字段协议仍为同目录README.md；112进度继续维护本文件，不另起并行回执。

## 112 接线实施回填（2026-11-10）

此节覆盖上方历史“OneLink未提供/仅mock”状态。官网代码已完成接线，尚未发布生产。

- destination() 严格校验 HTTPS、精确 host/path、无账号密码；仅保留可信 SDK 的 af_js_web=true 和合法 af_ss_ver，未写死版本；保留业务参数并拒绝额外参数。
- 正式 npm run build 默认注入已确认 SDN0 模板和官方 Smart Script；环境变量可显式覆盖/关闭，无秘密进入前端。API maxDuration=15s，覆盖8s上游超时。
- 官方 SDK 实际下载 HTTP200，SHA在 smart-script-fetch.json；真实运行版本2_10_4。onelink-live-staging.json 保存完整测试链接，同次 click_id=af_sub1、af_sub5=staging。SDK不可用立即 App Store fallback。
- 4条 staging 事件经真实 Node BFF→Supabase accepted 并通过只读SQL核对持久化；重复提交duplicate，冲突/错误environment/raw_ip拒绝。证据 onelink-persisted-staging.json。未向production灌合成事件。
- OneLink iPhone/desktop 两种UA均301到正确App Store，见 onelink-redirects.json。
- 6项Node测试、11组浏览器回归（含5种恶意SDK返回值降级）通过；正式构建、blog/resources/39页SEO检查通过。
- 本地staging测试服务使用既有HTTPS代理解决Node直连失败，仅用于测试，不改变生产转发。

### 尚未完成的公网验收及精确卡点

112现有CLI凭据与109现有CLI凭据访问该Vercel项目管理接口均HTTP403。109当前Chrome无Vercel登录页；GitHub diifan登录正常，自动部署链路不因此判为不可用。缺的是配置该项目服务器环境变量的有效管理访问：HOOPCUT_ANALYTICS_SECRET（production专用）、HOOPCUT_ANALYTICS_SECRET_HEADER=x-hoopcut-web-secret、HOOPCUT_ANALYTICS_RATE_SECRET、HOOPCUT_ANALYTICS_ORIGINS。预览须使用独立staging secret及准确preview origin。

本机HTTP-over-Unix-socket验证不替代公网CSP/SDK/BFF验收。真实YouTube播放验证通过：实际媒体currentTime=7.261秒、无媒体错误，捕获唯一video_play事件；页面为本地构建拦截映射，YouTube走真实网络，分析接口在该测试中mock避免production事件。见youtube-playback.json。这不替代部署后的公网入口验收。正式发布继续原审核流程。AF安装及App installation_id关联仍为109范围。

### Git与预览回执

实施commit：ea1d9fa；审核Draft PR：https://github.com/diifan/hoopcut-website/pull/19 。未合并，生产未部署。
Vercel于2026-11-10 02:33 UTC完成该commit的Preview构建，GitHub状态success。地址：https://hoopcut-website-git-feat-web-attribution-v1-diifans-projects.vercel.app 。匿名访问重定向到Vercel登录页，不能将登录页200计为官网验收。当前卡点还包含预览SSO访问；需要已有项目管理访问恢复后配置环境变量和预览访问，再进行公网验收。
