import assert from "node:assert/strict";
import * as ui from "../index";

assert.equal(typeof ui.Button, "function");
assert.equal(typeof ui.Panel, "function");
assert.equal(typeof ui.StatCard, "function");
