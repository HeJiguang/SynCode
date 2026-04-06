import assert from "node:assert/strict";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import * as ui from "../index";

assert.equal(typeof ui.Button, "function");
assert.equal(typeof ui.Panel, "function");
assert.equal(typeof ui.StatCard, "function");

const disabledButtonHtml = renderToStaticMarkup(
  React.createElement(ui.Button, { variant: "secondary", disabled: true }, "Disabled")
);

assert.match(disabledButtonHtml, /disabled:bg-\[rgba\(120,136,182,0\.2\)\]/);
assert.match(disabledButtonHtml, /disabled:text-\[color:color-mix\(in_srgb,var\(--text-primary\)_68%,transparent\)\]/);
