const path = require("node:path");

module.exports = {
  testDir: path.join(__dirname, "browser"),
  timeout: 15000,
  workers: 1,
  reporter: "line",
  use: {
    browserName: "chromium",
    headless: true,
    screenshot: "only-on-failure",
  },
  outputDir: path.join(__dirname, "test-results"),
};

