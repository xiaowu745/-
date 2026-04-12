// app.js - 荆工智匠小程序全局逻辑

App({
  /**
   * 小程序启动时执行
   * 调用 wx.login() 获取临时登录凭证 code，
   * 后续 H5 页面可使用该 code 向后端换取 openid。
   */
  onLaunch: function () {
    this.login()
  },

  /**
   * 调用微信登录接口获取 code
   * code 会存储在 globalData.wxLoginCode 中供页面使用
   */
  login: function () {
    var that = this
    wx.login({
      success: function (res) {
        if (res.code) {
          console.log('[荆工智匠] 登录成功，获取到 code:', res.code)
          that.globalData.wxLoginCode = res.code

          // 如果页面已经在等待 code，通过回调通知
          if (that.globalData.onLoginCodeReady) {
            that.globalData.onLoginCodeReady(res.code)
          }
        } else {
          console.error('[荆工智匠] 登录失败:', res.errMsg)
        }
      },
      fail: function (err) {
        console.error('[荆工智匠] wx.login 调用失败:', err)
      }
    })
  },

  /**
   * 全局数据
   * wxLoginCode: 微信登录凭证 code
   * onLoginCodeReady: 回调函数，当 code 获取完成时通知页面
   */
  globalData: {
    wxLoginCode: null,
    onLoginCodeReady: null
  }
})
