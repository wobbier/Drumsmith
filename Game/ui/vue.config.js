const { defineConfig } = require("@vue/cli-service");
module.exports = defineConfig({
  filenameHashing: false,
  publicPath: "./",
  transpileDependencies: true,
  outputDir: "../../Assets/UI/Vue",
});
