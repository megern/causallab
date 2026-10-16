/* Outcome-unit coefficient interval chart, kept separate from the workbench DOM. */
(function (global) {
  "use strict";

  function layout(coefficient, interval, width = 900) {
    const [lower, upper] = interval;
    if (![coefficient, lower, upper].every(Number.isFinite) || lower > upper) {
      throw new Error(
        "Coefficient interval must contain finite ordered values.",
      );
    }
    let minimum = Math.min(0, lower, coefficient);
    let maximum = Math.max(0, upper, coefficient);
    if (minimum === maximum) {
      minimum -= 1;
      maximum += 1;
    }
    const padding = (maximum - minimum) * 0.15;
    minimum -= padding;
    maximum += padding;
    const left = 90;
    const right = width - 90;
    const coordinate = (value) =>
      left + ((value - minimum) / (maximum - minimum)) * (right - left);
    return {
      minimum,
      maximum,
      left,
      right,
      lowerX: coordinate(lower),
      upperX: coordinate(upper),
      coefficientX: coordinate(coefficient),
      zeroX: coordinate(0),
      intervalY: 115,
      axisY: 220,
    };
  }

  function draw(
    canvas,
    coefficient,
    interval,
    format = (value) => Number(value.toPrecision(4)).toString(),
  ) {
    canvas.width = 900;
    canvas.height = 300;
    const ctx = canvas.getContext("2d");
    const chart = layout(coefficient, interval, canvas.width);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.font = "14px system-ui";
    ctx.fillStyle = "#27485d";
    ctx.strokeStyle = "#a9bdc8";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(chart.left, chart.axisY);
    ctx.lineTo(chart.right, chart.axisY);
    ctx.stroke();

    // Five outcome-unit ticks share the same scale as the point and interval.
    ctx.textAlign = "center";
    for (let index = 0; index <= 4; index++) {
      const x = chart.left + ((chart.right - chart.left) * index) / 4;
      const value =
        chart.minimum + ((chart.maximum - chart.minimum) * index) / 4;
      ctx.beginPath();
      ctx.moveTo(x, chart.axisY);
      ctx.lineTo(x, chart.axisY + 5);
      ctx.stroke();
      ctx.fillText(format(value), x, chart.axisY + 24);
    }
    ctx.fillText(
      "Adjusted treatment coefficient (outcome units)",
      canvas.width / 2,
      286,
    );

    ctx.setLineDash([5, 5]);
    ctx.strokeStyle = "#78919e";
    ctx.beginPath();
    ctx.moveTo(chart.zeroX, 55);
    ctx.lineTo(chart.zeroX, chart.axisY);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillText("Zero reference", chart.zeroX, 42);

    ctx.strokeStyle = "#167665";
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(chart.lowerX, chart.intervalY);
    ctx.lineTo(chart.upperX, chart.intervalY);
    ctx.stroke();
    [chart.lowerX, chart.upperX].forEach((x) => {
      ctx.beginPath();
      ctx.moveTo(x, chart.intervalY - 12);
      ctx.lineTo(x, chart.intervalY + 12);
      ctx.stroke();
    });
    ctx.fillStyle = "#167665";
    ctx.beginPath();
    ctx.arc(chart.coefficientX, chart.intervalY, 8, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#27485d";
    ctx.fillText("Estimate " + format(coefficient), chart.coefficientX, 82);
    // Endpoint labels use separate lines so narrow intervals remain readable.
    ctx.textAlign = "right";
    ctx.fillText("Lower " + format(interval[0]), chart.lowerX, 167);
    ctx.textAlign = "left";
    ctx.fillText("Upper " + format(interval[1]), chart.upperX, 188);
    ctx.textAlign = "left";
    canvas.setAttribute(
      "aria-label",
      `Adjusted coefficient ${format(coefficient)}. Approximate 95 percent interval ${format(interval[0])} to ${format(interval[1])}. Zero reference shown. Exact values are in the table.`,
    );
    return chart;
  }

  const api = { layout, draw };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else global.LabCausalChart = api;
})(typeof window === "undefined" ? globalThis : window);
