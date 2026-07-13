// Renders the SS_SIGNAL_1 / SS_SIGNAL_2 arrays (see sm.js signalsHandler) as a
// live oscilloscope-style trace instead of just summing them to the console.
var Scope = (function() {
    var canvas, ctx, width, height;

    function init() {
        canvas = document.getElementById('scope-canvas');
        if (!canvas) return;
        ctx = canvas.getContext('2d');
        width = canvas.width;
        height = canvas.height;
        drawGrid();
    }

    function drawGrid() {
        ctx.fillStyle = '#101010';
        ctx.fillRect(0, 0, width, height);
        ctx.strokeStyle = '#2b2b2b';
        ctx.lineWidth = 1;
        var divisions = 8;
        for (var i = 1; i < divisions; i++) {
            var x = Math.round((width / divisions) * i) + 0.5;
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, height);
            ctx.stroke();

            var y = Math.round((height / divisions) * i) + 0.5;
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(width, y);
            ctx.stroke();
        }
    }

    function drawTrace(values, color, toY) {
        if (!values || !values.length) return;
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        for (var i = 0; i < values.length; i++) {
            var x = (i / (values.length - 1)) * width;
            var y = toY(values[i]);
            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        }
        ctx.stroke();
    }

    // SS_SIGNAL_1 and SS_SIGNAL_2 don't share a fixed value range (observed
    // roughly [0,1] and [1,2] respectively), so auto-scale to whatever range
    // is actually present each frame rather than assuming one.
    function rangeOf(values) {
        var min = Infinity, max = -Infinity;
        for (var i = 0; i < values.length; i++) {
            if (values[i] < min) min = values[i];
            if (values[i] > max) max = values[i];
        }
        return { min: min, max: max };
    }

    function render(sig1, sig2, sum1, sum2) {
        if (!ctx) init();
        if (!ctx) return;

        var r1 = sig1 && sig1.length ? rangeOf(sig1) : { min: 0, max: 1 };
        var r2 = sig2 && sig2.length ? rangeOf(sig2) : { min: 0, max: 1 };
        var min = Math.min(r1.min, r2.min);
        var max = Math.max(r1.max, r2.max);
        var span = (max - min) || 1;
        var margin = span * 0.05;
        min -= margin;
        max += margin;
        span = max - min;

        var toY = function(v) {
            return height - ((v - min) / span) * height;
        };

        drawGrid();
        drawTrace(sig1, '#3ea6ff', toY); // SS_SIGNAL_1
        drawTrace(sig2, '#ffb100', toY); // SS_SIGNAL_2

        var readout = document.getElementById('scope-readout');
        if (readout && sum1 !== undefined && sum2 !== undefined) {
            readout.textContent =
                'SIGNAL_1 sum: ' + sum1.toFixed(2) + '    SIGNAL_2 sum: ' + sum2.toFixed(2);
        }
    }

    return { init: init, render: render };
})();

$(document).ready(function() {
    Scope.init();
});
