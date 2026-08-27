import { EngineeringOSPage, FooterStatus } from "./app";

(function register(): void {
  const sdk = window.__HERMES_PLUGIN_SDK__;
  const plugins = window.__HERMES_PLUGINS__;
  if (!sdk || !plugins?.register) {
    console.error("[engineering-os] Hermes dashboard SDK 1.1 unavailable");
    return;
  }
  plugins.register("engineering-os", EngineeringOSPage);
  if (plugins.registerSlot) {
    plugins.registerSlot("engineering-os", "footer-right", FooterStatus);
  }
})();

