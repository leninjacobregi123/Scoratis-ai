export { H as HighlightOverlay, L as LaserOverlay, S as SlideCanvas, a as SlideElement, b as SlideRendererProvider, c as SpotlightOverlay, f as findElementGeometry, d as findNearestCorner, g as getElementPercentageGeometry, u as useOptionalSlideContext, e as useSlideBackgroundStyle, h as useSlideContext, i as useViewportSize } from './chunks/SlideCanvas-CqBtS7Sn.js';
import { jsx, Fragment } from 'react/jsx-runtime';
import { motion } from 'motion/react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
export * from '@maic/dsl';
import 'react';
import './chunks/BaseCodeElement-Bh-Bfdz6.js';
import 'tinycolor2';
import 'echarts/core';
import 'echarts/charts';
import 'echarts/components';
import 'echarts/renderers';

function ZoomWrapper({ children, zoom, geometry }) {
    if (!zoom || !geometry) {
        return jsx(Fragment, { children: children });
    }
    const { scale } = zoom;
    const { centerX, centerY } = geometry;
    return (jsx(motion.div, { initial: { scale: 1 }, animate: { scale }, exit: { scale: 1 }, transition: { type: 'spring', stiffness: 200, damping: 25 }, style: {
            width: '100%',
            height: '100%',
            transformOrigin: `${centerX}% ${centerY}%`,
        }, children: children }));
}

function cn(...inputs) {
    return twMerge(clsx(inputs));
}

export { ZoomWrapper, cn };
//# sourceMappingURL=index.js.map
