"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

test("bundle is a classic SDK IIFE with no second React or token access", () => {
  const source = fs.readFileSync(path.resolve(__dirname, "../dist/index.js"), "utf8");
  assert.match(source, /__HERMES_PLUGIN_SDK__/);
  assert.doesNotMatch(source, /from\s+["']react["']/);
  assert.doesNotMatch(source, /__HERMES_SESSION_TOKEN__/);
  assert.doesNotMatch(source, /^\s*(import|export)\s/m);

  const registrations = [];
  const slots = [];
  const context = {
    console,
    window: {
      __HERMES_PLUGIN_SDK__: {
        React: { createElement: (...args) => ({ args }) },
        hooks: {
          useState: (value) => [value, () => {}],
          useEffect: () => {},
          useMemo: (factory) => factory(),
        },
        components: {},
        fetchJSON: async () => ({}),
        utils: { cn: (...items) => items.filter(Boolean).join(" ") },
      },
      __HERMES_PLUGINS__: {
        register: (name, component) => registrations.push({ name, component }),
        registerSlot: (name, slot, component) => slots.push({ name, slot, component }),
      },
    },
  };
  vm.runInNewContext(source, context, { timeout: 1000 });
  assert.equal(registrations[0].name, "engineering-os");
  assert.equal(slots[0].slot, "footer-right");
});

