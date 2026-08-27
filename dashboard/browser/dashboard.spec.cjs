const { test, expect } = require("@playwright/test");
const fs = require("node:fs");
const path = require("node:path");

const bundle = fs.readFileSync(path.resolve(__dirname, "../dist/index.js"), "utf8");

async function mount(page, fail = false) {
  await page.setContent("<main id='root'></main>");
  await page.evaluate(
    ({ source, fail }) => {
      const state = [];
      let cursor = 0;
      const effectDeps = [];
      let effectCursor = 0;
      let updates = [];
      const hooks = {
        useState(initial) {
          const index = cursor++;
          if (!(index in state)) state[index] = initial;
          return [
            state[index],
            (value) => {
              state[index] = typeof value === "function" ? value(state[index]) : value;
              updates.push({ index, value: state[index] });
            },
          ];
        },
        useEffect(effect, deps) {
          const index = effectCursor++;
          const previous = effectDeps[index];
          const changed = !previous || deps.some((value, i) => value !== previous[i]);
          effectDeps[index] = deps;
          if (changed) effect();
        },
        useMemo(factory) {
          return factory();
        },
      };
      const responses = {
        overview: {
          runtime: { status: "AVAILABLE", data: { version: "fixture", storage: {} } },
          kanban: { status: "AVAILABLE", data: { board: "fixture" } },
          github: { github_api: { status: "BLOCKED_AUTH", data: {} } },
        },
        github: {
          local_git: { status: "AVAILABLE", data: [] },
          github_api: { status: "BLOCKED_AUTH", data: {}, detail: "fixture" },
        },
      };
      const React = {
        createElement(type, props, ...children) {
          return { type, props: props || {}, children: children.flat(Infinity) };
        },
      };
      let component;
      window.__HERMES_PLUGIN_SDK__ = {
        React,
        hooks,
        components: {},
        utils: { cn: (...items) => items.filter(Boolean).join(" ") },
        fetchJSON: async (url) => {
          if (fail) throw new Error("fixture API unavailable");
          const key = url.split("/").pop();
          return responses[key] || { status: "AVAILABLE", data: [] };
        },
      };
      window.__HERMES_PLUGINS__ = {
        register(_name, value) {
          component = value;
        },
        registerSlot() {},
      };
      eval(source);
      function renderNode(node) {
        if (node == null || node === false) return document.createTextNode("");
        if (typeof node === "string" || typeof node === "number") {
          return document.createTextNode(String(node));
        }
        const element = document.createElement(node.type);
        for (const [key, value] of Object.entries(node.props || {})) {
          if (key === "className") element.className = value;
          else if (key === "onClick") element.addEventListener("click", value);
          else if (key === "role") element.setAttribute("role", value);
          else if (key.startsWith("aria-")) element.setAttribute(key, value);
        }
        for (const child of node.children || []) element.appendChild(renderNode(child));
        return element;
      }
      window.__rerenderEngineeringOS = async () => {
        await Promise.resolve();
        cursor = 0;
        effectCursor = 0;
        const tree = component();
        const root = document.querySelector("#root");
        root.replaceChildren(renderNode(tree));
      };
      window.__engineeringState = { state, updates };
    },
    { source: bundle, fail },
  );
  await page.evaluate(() => window.__rerenderEngineeringOS());
  await page.evaluate(() => window.__rerenderEngineeringOS());
}

test("renders live overview and navigates without lifecycle controls", async ({ page }) => {
  await mount(page);
  await expect(page.getByRole("heading", { name: "Engineering OS" })).toBeVisible();
  await expect(page.getByText("Hermes runtime")).toBeVisible();
  await page.getByRole("button", { name: "GitHub" }).click();
  await page.evaluate(() => window.__rerenderEngineeringOS());
  await page.evaluate(() => window.__rerenderEngineeringOS());
  await expect(page.getByText("Mutation disabled")).toBeVisible();
  await expect(page.getByText("Blocked auth")).toBeVisible();
  await expect(page.getByRole("button", { name: /create|merge|delete/i })).toHaveCount(0);
});

test("surfaces backend failure without leaking a fake secret", async ({ page }) => {
  await mount(page, true);
  await page.waitForFunction(() =>
    window.__engineeringState.updates.some((entry) =>
      String(entry.value).includes("fixture API unavailable")
    )
  );
  await page.evaluate(() => window.__rerenderEngineeringOS());
  await expect(page.getByRole("alert")).toContainText("fixture API unavailable");
  await expect(page.locator("body")).not.toContainText("ghp_fixture_secret_value");
});

