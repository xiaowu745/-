// pages/index/index.js - 荆工智匠小程序首页逻辑

/**
 * H5 平台访问地址配置
 *
 * 开发期：ICP 备案未通过 → 用 http + 8000 端口，需在开发者工具勾选"不校验合法域名"
 * 正式期：ICP 备案通过 + HTTPS 证书 + 业务域名白名单配置好 → 用 https
 *
 * 切换方式：把对应的那一行赋值给 BASE_URL 即可
 */
// 正式环境（HTTPS，需业务域名白名单）
const BASE_URL_PROD = 'https://jgzj.org.cn'
// 开发环境（HTTP + 8000，需勾选"不校验合法域名"）
const BASE_URL_DEV = 'http://jgzj.org.cn:8000'

// 当前使用：默认正式环境；开发联调时改成 BASE_URL_DEV
const BASE_URL = BASE_URL_PROD

Page({
  data: {
    // web-view 要加载的完整 URL，初始为空表示尚未就绪
    url: ''
  },

  onLoad: function () {
    var that = this
    var app = getApp()

    // 检查全局数据中是否已有登录 code
    if (app.globalData.wxLoginCode) {
      // code 已就绪，直接构造 URL
      that.buildUrl(app.globalData.wxLoginCode)
    } else {
      // code 尚未获取完成，注册回调等待
      app.globalData.onLoginCodeReady = function (code) {
        that.buildUrl(code)
      }
    }
  },

  /**
   * 根据登录 code 构造 H5 页面的完整 URL
   * 格式：{BASE_URL}/?wx_code={code}
   * @param {string} code - 微信登录凭证
   */
  buildUrl: function (code) {
    var fullUrl = BASE_URL + '/?wx_code=' + encodeURIComponent(code)
    console.log('[荆工智匠] 加载 H5 页面:', fullUrl)
    this.setData({
      url: fullUrl
    })
  },

  /**
   * 处理来自 H5 页面的消息
   * H5 端可通过 wx.miniProgram.postMessage({ data: {...} }) 发送消息
   * 消息会在特定时机（后退、组件销毁、分享）触发此回调
   */
  onWebViewMessage: function (e) {
    console.log('[荆工智匠] 收到 H5 消息:', e.detail)
    // 根据业务需要处理消息，例如：
    // var data = e.detail.data
    // if (data && data.length > 0) {
    //   var latestMsg = data[data.length - 1]
    //   // 处理最新消息...
    // }
  },

  /**
   * web-view 加载完成回调
   */
  onWebViewLoad: function (e) {
    console.log('[荆工智匠] H5 页面加载完成')
  },

  /**
   * web-view 加载失败回调
   */
  onWebViewError: function (e) {
    console.error('[荆工智匠] H5 页面加载失败:', e.detail)
    wx.showToast({
      title: '页面加载失败，请检查网络',
      icon: 'none',
      duration: 3000
    })
  }
})
