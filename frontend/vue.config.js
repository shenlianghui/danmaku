const { defineConfig } = require('@vue/cli-service')

module.exports = defineConfig({
  transpileDependencies: true,
  // 生产环境是否生成 sourceMap 文件
  productionSourceMap: false,
  // 关闭 ESLint 格式化功能
  lintOnSave: false,

  // 配置开发服务器
  devServer: {
    port: 8080, // 前端开发服务器端口
    proxy: {
      '/api': {
        target: process.env.VUE_APP_API_BASE_URL || 'http://localhost:8000',
        changeOrigin: true,
        pathRewrite: {
          '^/api': '/api'
        }
      }
    },
    client: {
      overlay: {
        errors: true,
        warnings: false,  // 不显示警告，减少干扰
      },
    },
    historyApiFallback: true, // 支持路由模式
  },

  // 输出设置
  outputDir: 'dist',
  publicPath: process.env.NODE_ENV === 'production' ? './' : '/',
  
  // 增加配置解决 Vue 警告
  configureWebpack: {
    performance: {
      hints: false // 关闭性能提示
    },
    plugins: [
      // 定义Vue 3特性标志
      new (require('webpack').DefinePlugin)({
        '__VUE_PROD_DEVTOOLS__': false,
        '__VUE_PROD_HYDRATION_MISMATCH_DETAILS__': false
      })
    ]
  }
}) 
