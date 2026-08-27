"use strict";

const fs = require("fs");
const vm = require("vm");
const path = require("path");

const root = path.resolve(__dirname, "../..");

function run(relativePath) {
  const registrations = [];
  const slots = [];
  const React = { createElement: (...args) => ({ args }) };
  const SDK = {
    React,
    components: new Proxy({}, { get: (_target, name) => String(name) }),
    hooks: {
      useState: (value) => [value, () => {}],
      useEffect: () => {},
    },
    utils: { cn: (...values) => values.filter(Boolean).join(" ") },
    api: { getStatus: async () => ({ gateway_online: true }) },
    fetchJSON: async () => ({ message: "fixture" }),
  };
  const PLUGINS = {
    register: (name, component) => registrations.push({ name, component }),
    registerSlot: (name, slot, component) => slots.push({ name, slot, component }),
  };
  const context = {
    window: {
      __HERMES_PLUGIN_SDK__: SDK,
      __HERMES_PLUGINS__: PLUGINS,
    },
    console,
  };
  const source = fs.readFileSync(path.join(root, relativePath), "utf8");
  vm.runInNewContext(source, context, { filename: relativePath, timeout: 1000 });
  if (registrations.length !== 1) throw new Error(`${relativePath}: registration`);
  return { name: registrations[0].name, slots: slots.map((item) => item.slot) };
}

const example = run("vendor/hermes-dashboard-base/dashboard/dist/index.js");
const cockpit = run("vendor/cockpit/dashboard/dist/index.js");
if (example.name !== "example") throw new Error("example name mismatch");
if (cockpit.slots.join(",") !== "sidebar,header-left,footer-right") {
  throw new Error("cockpit slot mismatch");
}
process.stdout.write(JSON.stringify({ status: "PASS", example, cockpit }) + "\n");

