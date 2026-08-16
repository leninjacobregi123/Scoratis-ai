'use strict';

var SlideCanvas = require('./chunks/SlideCanvas-BjVHdBXf.cjs');
var jsxRuntime = require('react/jsx-runtime');
var react = require('motion/react');
var clsx = require('clsx');
var tailwindMerge = require('tailwind-merge');
var dsl = require('@maic/dsl');
require('react');
require('./chunks/BaseCodeElement-C4RFPT0H.cjs');
require('tinycolor2');
require('echarts/core');
require('echarts/charts');
require('echarts/components');
require('echarts/renderers');

function ZoomWrapper({ children, zoom, geometry }) {
    if (!zoom || !geometry) {
        return jsxRuntime.jsx(jsxRuntime.Fragment, { children: children });
    }
    const { scale } = zoom;
    const { centerX, centerY } = geometry;
    return (jsxRuntime.jsx(react.motion.div, { initial: { scale: 1 }, animate: { scale }, exit: { scale: 1 }, transition: { type: 'spring', stiffness: 200, damping: 25 }, style: {
            width: '100%',
            height: '100%',
            transformOrigin: `${centerX}% ${centerY}%`,
        }, children: children }));
}

function cn(...inputs) {
    return tailwindMerge.twMerge(clsx.clsx(inputs));
}

exports.HighlightOverlay = SlideCanvas.HighlightOverlay;
exports.LaserOverlay = SlideCanvas.LaserOverlay;
exports.SlideCanvas = SlideCanvas.SlideCanvas;
exports.SlideElement = SlideCanvas.SlideElement;
exports.SlideRendererProvider = SlideCanvas.SlideRendererProvider;
exports.SpotlightOverlay = SlideCanvas.SpotlightOverlay;
exports.findElementGeometry = SlideCanvas.findElementGeometry;
exports.findNearestCorner = SlideCanvas.findNearestCorner;
exports.getElementPercentageGeometry = SlideCanvas.getElementPercentageGeometry;
exports.useOptionalSlideContext = SlideCanvas.useOptionalSlideContext;
exports.useSlideBackgroundStyle = SlideCanvas.useSlideBackgroundStyle;
exports.useSlideContext = SlideCanvas.useSlideContext;
exports.useViewportSize = SlideCanvas.useViewportSize;
exports.ZoomWrapper = ZoomWrapper;
exports.cn = cn;
Object.keys(dsl).forEach(function (k) {
    if (k !== 'default' && !Object.prototype.hasOwnProperty.call(exports, k)) Object.defineProperty(exports, k, {
        enumerable: true,
        get: function () { return dsl[k]; }
    });
});
//# sourceMappingURL=index.cjs.map
