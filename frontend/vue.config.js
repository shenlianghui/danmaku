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
        target: 'http://localhost:8000',  // 后端服务器地址
        changeOrigin: true,               // 开启代理
        secure: false,                    // 使用 http
        logLevel: 'debug'                 // 调试级别日志
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
  publicPath: '/',
  
  // 增加配置解决 Vue 警告
  configureWebpack: {
    performance: {
      hints: false // 关闭性能提示
    }
  }
}) 
