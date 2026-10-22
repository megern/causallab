import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { parseCSV, numericColumn, payload } = require("../app/static/data.js");
const context = { window: {} };
vm.runInNewContext(
  fs.readFileSync(new URL("../app/static/config.js", import.meta.url), "utf8"),
  context,
);
const cfg = context.window.APP_CONFIG;
let checks = 0;
test("quoted-empty single-column record preserved then rejected as missing numeric", () => {
  const data = parseCSV('values\n1\n""\n2');
  assert.deepEqual(data.rows, [["1"], [""], ["2"]]);
  assert.throws(() => numericColumn(data, "values"), /Row 3.*missing values/);
});
test("trailing quoted-empty record at EOF preserved", () => {
  const data = parseCSV('values\r\n1\r\n""');
  assert.deepEqual(data.rows, [["1"], [""]]);
  assert.throws(() => numericColumn(data, "values"), /Row 3/);
});
test("whitespace-only field is data, not a blank physical line", () => {
  const data = parseCSV("values\n1\n   \n2");
  assert.equal(data.rows.length, 3);
  assert.throws(() => numericColumn(data, "values"), /Row 3/);
});
test("truly empty physical lines ignored while delimiter-empty rows retained", () => {
  assert.deepEqual(parseCSV("values\n\n1\n\n2\n").rows, [["1"], ["2"]]);
  assert.deepEqual(parseCSV("a,b\n,\n1,2").rows, [
    ["", ""],
    ["1", "2"],
  ]);
});
function test(name, callback) {
  callback();
  checks++;
  console.log("PASS " + name);
}
test("quoted comma, multiline, escaped quote and CRLF", () => {
  const data = parseCSV('name,value\r\n"a,b",1\r\n"line\n""two""",2\r\n');
  assert.deepEqual(data.rows, [
    ["a,b", "1"],
    ['line\n"two"', "2"],
  ]);
});
test("BOM header parsed", () =>
  assert.deepEqual(parseCSV("\uFEFFa,b\n1,2").headers, ["a", "b"]));
test("duplicate headers rejected", () =>
  assert.throws(() => parseCSV("a,a\n1,2"), /unique/));
test("ragged row actionable", () =>
  assert.throws(() => parseCSV("a,b\n1"), /row 2/));
test("unclosed quoted field rejected", () =>
  assert.throws(() => parseCSV('a,b\n"1,2'), /unclosed/));
test("empty matrix row not silently dropped", () =>
  assert.equal(parseCSV("a,b\n,\n1,2").rows.length, 2));
test("blank physical lines ignored", () =>
  assert.equal(parseCSV("a,b\n\n1,2\n").rows.length, 1));
test("missing numeric value is an error", () =>
  assert.throws(() => numericColumn(parseCSV("a,b\n,2"), "a"), /Row 2/));
test("nonfinite and oversized numbers rejected", () => {
  for (const value of ["1e400", "1e101", "NaN", "Infinity", "0x10"])
    assert.throws(() => numericColumn(parseCSV("a\n" + value), "a"));
});
test("scientific notation and decimal values", () =>
  assert.deepEqual(
    numericColumn(parseCSV("a\n-1.2e2\n+.5"), "a"),
    [-120, 0.5],
  ));
test("hostile text remains plain CSV text", () => {
  assert.equal(
    parseCSV("name,value\n<img src=x onerror=alert(1)>,2").rows[0][0],
    "<img src=x onerror=alert(1)>",
  );
});
test("synthetic CSV produces actual API request", () => {
  const data = parseCSV(cfg.sample),
    map = {};
  cfg.mapping.forEach(
    ([key], i) =>
      (map[key] = data.headers.includes(key) ? key : data.headers[i]),
  );
  if (cfg.multi)
    map[cfg.multi[0]] = data.headers.filter(
      (h) => !Object.values(map).includes(h),
    );
  const params = {};
  cfg.params.forEach(([key, , value]) => (params[key] = value));
  if (cfg.method) params.method = "drift";
  const request = payload(cfg.slug, data, map, params);
  assert.equal(Object.keys(request).length > 0, true);
  const roundtrip = JSON.parse(JSON.stringify(request));
  assert.deepEqual(roundtrip, request);
  if (cfg.slug === "quantforge") {
    assert.equal(request.prices.length, 48);
    assert.throws(
      () => payload(cfg.slug, data, { ...map, signals: "missing" }, params),
      /Select a column/,
    );
  }
  if (cfg.slug === "causallab") {
    assert.equal(request.confounders[0].length, 2);
    assert.throws(
      () =>
        payload(
          cfg.slug,
          data,
          { ...map, confounders: [map.treatment] },
          params,
        ),
      /cannot also/,
    );
  }
  if (cfg.slug === "neuralscope") {
    assert.equal(request.features.length, 100);
    assert.throws(
      () => payload(cfg.slug, data, { ...map, features: [map.target] }, params),
      /leakage/,
    );
  }
  if (cfg.slug === "timesense") {
    assert.equal(request.values.length, 48);
    assert.throws(
      () => payload(cfg.slug, data, map, { ...params, holdout: 46 }),
      /five training/,
    );
  }
});

const causalChart = require("../app/static/causal-chart.js");
test("causal interval spans outcome units and includes zero reference", () => {
  const positive = causalChart.layout(3, [2.8, 3.2]);
  assert.ok(positive.minimum < 0 && positive.maximum > 3.2);
  assert.ok(positive.zeroX < positive.lowerX);
  assert.ok(
    positive.lowerX < positive.coefficientX &&
      positive.coefficientX < positive.upperX,
  );
  const crossesZero = causalChart.layout(-1, [-3, 1]);
  assert.ok(
    crossesZero.lowerX < crossesZero.zeroX &&
      crossesZero.zeroX < crossesZero.upperX,
  );
  const negative = causalChart.layout(-3, [-4, -2]);
  assert.ok(negative.upperX < negative.zeroX);
  const exactZero = causalChart.layout(0, [0, 0]);
  assert.ok(Number.isFinite(exactZero.coefficientX));
});
test("canvas actually draws one point, a horizontal interval and dashed zero reference", () => {
  const strokes = [],
    points = [],
    labels = [];
  let path = [],
    dash = [];
  const ctx = {
    clearRect() {},
    beginPath() {
      path = [];
    },
    moveTo(x, y) {
      path.push([x, y]);
    },
    lineTo(x, y) {
      path.push([x, y]);
    },
    stroke() {
      strokes.push({ path: [...path], dash: [...dash] });
    },
    setLineDash(value) {
      dash = value;
    },
    arc(x, y, radius) {
      points.push([x, y, radius]);
    },
    fill() {},
    fillText(text) {
      labels.push(text);
    },
  };
  const canvas = {
    getContext() {
      return ctx;
    },
    setAttribute(name, value) {
      this[name] = value;
    },
  };
  const geometry = causalChart.draw(canvas, 3, [2, 4]);
  assert.deepEqual(points, [[geometry.coefficientX, geometry.intervalY, 8]]);
  assert.ok(
    strokes.some(
      (s) =>
        JSON.stringify(s.path) ===
        JSON.stringify([
          [geometry.lowerX, geometry.intervalY],
          [geometry.upperX, geometry.intervalY],
        ]),
    ),
  );
  assert.ok(
    strokes.some(
      (s) =>
        s.dash.length > 0 &&
        s.path.length === 2 &&
        s.path[0][0] === geometry.zeroX &&
        s.path[1][0] === geometry.zeroX,
    ),
  );
  assert.ok(labels.includes("Zero reference"));
  assert.match(canvas["aria-label"], /Approximate 95 percent interval 2 to 4/);
});
console.log(
  `${checks} total frontend checks passed after causal chart validation`,
);

test("selected confounder labels preserved in replay payload", () => {
  const data = parseCSV(
    "outcome,treatment,Baseline\n" +
      Array.from({ length: 12 }, (_, i) => `${i + 2},${i % 2},${i % 5}`).join(
        "\n",
      ),
  );
  const request = payload(
    "causallab",
    data,
    { outcome: "outcome", treatment: "treatment", confounders: ["Baseline"] },
    {},
  );
  assert.deepEqual(request.confounder_names, ["Baseline"]);
  assert.equal(request.confounders[7][0], 2);
});

test("new scientific option is wired through the actual parameter collector", () => {
  const source = fs.readFileSync(
    new URL("../app/static/workbench.js", import.meta.url),
    "utf8",
  );
  const collector = source.slice(
    source.indexOf("function parameters()"),
    source.indexOf("function mapping()"),
  );
  const fields = Object.fromEntries(
    cfg.params.map(([name, , value]) => [
      "param-" + name,
      {
        value: String(value),
        checkValidity: () => true,
        labels: [{ textContent: name }],
      },
    ]),
  );
  fields["include-ipw"] = { checked: true };
  fields["param-model"] = { value: "random_forest" };
  const settings = vm.runInNewContext(collector + ";parameters()", {
    cfg,
    $: (id) => fields[id],
  });
  if (cfg.slug === "causallab") {
    assert.equal(settings.include_ipw, true);
    assert.equal(settings.propensity_clip, 0.02);
  } else {
    assert.equal(settings.model, "random_forest");
    assert.equal(settings.trees, 50);
  }
});

console.log(`${checks} frontend checks passed for ${cfg.title} v0.4.0`);
