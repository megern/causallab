import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import test from "node:test";
import { documentFromHTML } from "./ui-test-dom.mjs";

// Synthetic transport fixture: values deliberately distinct to identify every field.
const response = {
  treatment_effect: 2.25,
  robust_standard_error: 0.3,
  approximate_95_percent_interval: [1.66, 2.84],
  poor_overlap_fraction: 0,
  group_counts: { control: 30, treated: 30 },
  covariate_balance: [
    {
      confounder: "age",
      control_mean: 30,
      treated_mean: 31,
      pooled_sample_sd: 4,
      standardized_mean_difference: 0.25,
      descriptive_imbalance_flag: true,
    },
  ],
  balance_method: "Synthetic descriptive balance fixture",
  propensity_range: [0.2, 0.8],
  warnings: [],
  assumptions:
    "Synthetic response for UI regression; not a scientific measurement.",
  ipw: {
    ate: 1.75,
    effective_sample_size: { control: 21.5, treated: 23.25 },
    clipped_observations: 3,
    clipped_fraction: 0.05,
    weighted_balance: [
      { confounder: "age", raw_smd: 0.25, weighted_smd: 0.03 },
    ],
    warnings: ["Inspect clipping."],
    limitations: "No uncertainty interval.",
  },
};

test("actual IPW checkbox and run handler retain ATE, ESS, clipping and weighted balance", async () => {
  const root = new URL("../app/static/", import.meta.url);
  const document = documentFromHTML(
    fs.readFileSync(new URL("index.html", root), "utf8"),
  );
  document.getElementById("chart").getContext = () =>
    new Proxy(
      {},
      {
        get: (target, key) => target[key] || (() => {}),
        set: (target, key, value) => {
          target[key] = value;
          return true;
        },
      },
    );
  const requests = [],
    blobs = [];
  const context = {
    document,
    console,
    TextEncoder,
    Blob,
    setTimeout: () => {},
    URL: {
      createObjectURL: (blob) => {
        blobs.push(blob);
        return "blob:synthetic";
      },
      revokeObjectURL: () => {},
    },
    fetch: async (path, options) => {
      requests.push({ path, input: JSON.parse(options.body) });
      return { ok: true, json: async () => response };
    },
  };
  context.window = context;
  vm.createContext(context);
  for (const filename of [
    "config.js",
    "data.js",
    "causal-chart.js",
    "workbench.js",
  ])
    vm.runInContext(fs.readFileSync(new URL(filename, root), "utf8"), context, {
      filename,
    });
  const get = (id) => document.getElementById(id);
  get("load-example").click();
  get("include-ipw").checked = true;
  await get("run").onclick();
  assert.equal(requests.length, 1, get("status").textContent);
  assert.equal(requests[0].input.include_ipw, true);
  assert.equal(get("results").hidden, false, get("status").textContent);
  assert.match(get("status").textContent, /Analysis finished/);
  const text = get("ipw-results").textContent;
  assert.match(text, /Hájek IPW estimate \(no uncertainty interval\)/);
  assert.match(
    text,
    /ATE 1.75; control ESS 21.5, treated ESS 23.25; clipped 3 observations \(5%\)/,
  );
  assert.match(text, /Weighted SMD \(raw SD denominator\)/);
  assert.match(text, /age0.250.03/);
  assert.match(text, /Inspect clipping/);
  get("export-result").click();
  const exported = JSON.parse(await blobs[0].text());
  assert.equal(exported.result.ipw.ate, 1.75);
  assert.equal(exported.configuration.parameters.include_ipw, true);
});
