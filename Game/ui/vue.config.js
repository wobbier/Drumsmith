const { defineConfig } = require("@vue/cli-service");
const HtmlWebpackPlugin = require("html-webpack-plugin");

module.exports = defineConfig({
  filenameHashing: false,
  publicPath: "./",
  transpileDependencies: true,
  outputDir: "../../Assets/UI",
  pages: {
    index: {
      // entry for the main page
      entry: "src/main.js",
      template: "public/index.html",
      filename: "index.html",
    },
    MainMenu: {
      // entry for the first additional page
      entry: "src/MainMenu.js",
      template: "public/MainMenu.html",
      filename: "MainMenu.html",
    },
  },
  configureWebpack: (config) => {
    // Find the HtmlWebpackPlugin in the plugins array and modify its options
    config.plugins.forEach((plugin) => {
      if (plugin instanceof HtmlWebpackPlugin) {
        plugin.options.minify = {
          collapseWhitespace: false, // Disable whitespace collapsing
          keepClosingSlash: true, // Keep closing slash in self-closing elements
          removeComments: false, // Preserve comments
          removeRedundantAttributes: false, // Preserve redundant attributes
          removeEmptyAttributes: false, // Preserve empty attributes
          minifyCSS: false, // Disable CSS minification if necessary
          minifyJS: false, // Disable JS minification if necessary
        };
      }
    });
  },
});
