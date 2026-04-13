# 荆工智匠 - 微信小程序模板

本项目是「荆工智匠」H5 工程技能测评平台的微信小程序壳，通过 `web-view` 组件加载 H5 页面，实现在微信内访问平台的完整功能。

---

## 一、使用前准备

### 1. 注册微信小程序账号

1. 访问 [微信公众平台](https://mp.weixin.qq.com/)，点击右上角「立即注册」。
2. 选择账号类型为「小程序」。
3. 按照提示完成邮箱验证、信息登记（需提供企业资质或个人身份信息）。
4. 注册完成后，在「开发管理 → 开发设置」中获取 **AppID**。

### 2. 配置业务域名白名单

> **重要**：`web-view` 组件只能加载已配置在业务域名白名单中的 URL。

1. 登录 [微信公众平台](https://mp.weixin.qq.com/)。
2. 进入「开发管理 → 开发设置 → 业务域名」。
3. 点击「开始配置」，按提示下载校验文件，将其上传到你的 H5 服务器根目录。
4. 在域名列表中添加你的 H5 域名，例如 `https://jgzj.org.cn`。
5. 点击「保存并提交」，等待校验通过。

### 3. 配置 AppID

1. 打开本项目中的 `project.config.json` 文件。
2. 将 `appid` 字段的值替换为你在微信公众平台获取的真实 AppID。

### 4. 配置 H5 访问地址

打开 `pages/index/index.js` 文件，顶部有两个环境配置：

```javascript
// 正式环境（HTTPS，需业务域名白名单）
const BASE_URL_PROD = 'https://jgzj.org.cn'
// 开发环境（HTTP + 8000，需勾选"不校验合法域名"）
const BASE_URL_DEV = 'http://jgzj.org.cn:8000'

// 当前使用：默认正式环境；开发联调时改成 BASE_URL_DEV
const BASE_URL = BASE_URL_PROD
```

- **ICP 备案完成前**：`const BASE_URL = BASE_URL_DEV`，并在开发者工具「详情 → 本地设置」勾选"不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书"
- **ICP 备案完成后**：保持 `const BASE_URL = BASE_URL_PROD`，并在微信公众平台配置业务域名白名单

---

## 二、开发与部署

### 1. 安装微信开发者工具

1. 下载 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)。
2. 安装并使用微信扫码登录。

### 2. 导入项目

1. 打开微信开发者工具，选择「导入项目」。
2. 项目目录选择本模板所在的文件夹（即包含 `app.json` 的目录）。
3. AppID 填写你的真实 AppID。
4. 点击「导入」。

### 3. 本地调试

- 导入后可在模拟器中预览效果。
- 注意：`web-view` 在模拟器中可能无法正常加载，建议使用「真机调试」功能。
- 在「详情 → 本地设置」中勾选「不校验合法域名」可在开发阶段跳过域名校验。

### 4. 上传并发布

1. 在开发者工具中点击右上角「上传」按钮。
2. 填写版本号和备注，点击「上传」。
3. 登录微信公众平台，进入「管理 → 版本管理」。
4. 在「开发版本」中找到刚上传的版本，点击「提交审核」。
5. 审核通过后，点击「全量发布」即可上线。

---

## 三、项目结构

```
miniprogram/
├── app.js                  # 全局逻辑（获取微信登录凭证）
├── app.json                # 全局配置
├── app.wxss                # 全局样式
├── project.config.json     # 项目配置
├── README.md               # 说明文档（本文件）
└── pages/
    └── index/
        ├── index.js        # 首页逻辑（构造 web-view URL）
        ├── index.wxml      # 首页模板（web-view 组件）
        └── index.wxss      # 首页样式
```

---

## 四、工作原理

1. 用户打开小程序时，`app.js` 调用 `wx.login()` 获取临时登录凭证 `code`。
2. 首页 `index.js` 从全局数据中取出 `code`，拼接到 H5 URL 的查询参数中。
3. `web-view` 组件加载完整 URL：`https://{域名}/?wx_code={code}`。
4. H5 端收到 `wx_code` 后，可调用后端接口换取用户的 `openid` 和 `session_key`，完成登录。

---

## 五、常见问题

**Q: web-view 页面打不开？**
A: 请确认业务域名白名单已正确配置，且域名使用 HTTPS 协议。

**Q: wx.login 获取的 code 过期了怎么办？**
A: `code` 的有效期为 5 分钟。若用户停留时间过长，H5 端应实现 code 过期后的重新获取逻辑。

**Q: 如何在 H5 和小程序之间通信？**
A: H5 页面可通过 `wx.miniProgram.postMessage()` 向小程序发送消息，小程序在 `web-view` 的 `bindmessage` 事件中接收。
