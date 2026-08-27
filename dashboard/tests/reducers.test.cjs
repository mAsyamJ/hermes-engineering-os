"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const esbuild = require("esbuild");

function load(entry) {
  const result = esbuild.buildSync({
    entryPoints: [entry],
    bundle: true,
    write: false,
    platform: "node",
    format: "cjs",
  });
  const module = { exports: {} };
  new Function("module", "exports", "require", result.outputFiles[0].text)(
    module,
    module.exports,
    require,
  );
  return module.exports;
}

test("Hermes events retain sequence and coalesce adjacent output", () => {
  const { coalesceEvents } = load("../vendor/ai-agent-board-ui/event-coalescing.ts");
  const result = coalesceEvents([
    { id: 2, runId: 7, sequence: 2, type: "output", content: "second" },
    { id: 1, runId: 7, sequence: 1, type: "command_output", content: "first" },
  ]);
  assert.equal(result.length, 1);
  assert.equal(result[0].content, "first\nsecond");
  assert.deepEqual(result[0].sourceIds, [1, 2]);
});

test("status bus deduplicates transitions and replays to late subscribers", () => {
  const bus = load("../vendor/hivemind-ui/agent-status-bus.ts");
  bus.resetAgentStatusBus();
  const first = [];
  bus.subscribeAgentStatus((event) => first.push(event));
  bus.publishAgentStatus({ profile: "default", status: "running", sequence: 1 });
  bus.publishAgentStatus({ profile: "default", status: "running", sequence: 1 });
  assert.equal(first.length, 1);
  const late = [];
  bus.subscribeAgentStatus((event) => late.push(event));
  assert.equal(late.length, 1);
  assert.equal(late[0].status, "running");
});

