// pages/index/index.js - 荆工智匠小程序首页逻辑

/**
 * H5 平台部署域名（不含协议前缀）
 * 请修改为你实际部署的域名，例如 'exam.example.com'
 * 注意：该域名必须在微信公众平台「业务域名」白名单中配置
 */
const DOMAIN = 'jgzj.org.cn'

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
   * 格式：https://{DOMAIN}/?wx_code={code}
   * @param {string} code - 微信登录凭证
   */
  buildUrl: function (code) {
    var fullUrl = 'https://' + DOMAIN + '/?wx_code=' + encodeURIComponent(code)
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
