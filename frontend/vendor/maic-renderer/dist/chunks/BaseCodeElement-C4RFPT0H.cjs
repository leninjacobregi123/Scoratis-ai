'use strict';

var jsxRuntime = require('react/jsx-runtime');
var react = require('react');
var tinycolor = require('tinycolor2');
var echarts = require('echarts/core');
var charts = require('echarts/charts');
var components = require('echarts/components');
var renderers = require('echarts/renderers');
var react$1 = require('motion/react');

function _interopNamespaceDefault(e) {
    var n = Object.create(null);
    if (e) {
        Object.keys(e).forEach(function (k) {
            if (k !== 'default') {
                var d = Object.getOwnPropertyDescriptor(e, k);
                Object.defineProperty(n, k, d.get ? d : {
                    enumerable: true,
                    get: function () { return e[k]; }
                });
            }
        });
    }
    n.default = e;
    return Object.freeze(n);
}

var echarts__namespace = /*#__PURE__*/_interopNamespaceDefault(echarts);

function useElementShadow(shadow) {
    const shadowStyle = react.useMemo(() => {
        if (shadow) {
            const { h, v, blur, color } = shadow;
            return `${h}px ${v}px ${blur}px ${color}`;
        }
        return '';
    }, [shadow]);
    return { shadowStyle };
}

function useElementFlip(flipH, flipV) {
    const flipStyle = react.useMemo(() => {
        let style = '';
        if (flipH && flipV)
            style = 'rotateX(180deg) rotateY(180deg)';
        else if (flipV)
            style = 'rotateX(180deg)';
        else if (flipH)
            style = 'rotateY(180deg)';
        return style;
    }, [flipH, flipV]);
    return { flipStyle };
}

var ClipPathTypes;
(function (ClipPathTypes) {
    ClipPathTypes["RECT"] = "rect";
    ClipPathTypes["ELLIPSE"] = "ellipse";
    ClipPathTypes["POLYGON"] = "polygon";
})(ClipPathTypes || (ClipPathTypes = {}));
const CLIPPATHS = {
    rect: {
        name: '矩形',
        type: ClipPathTypes.RECT,
        radius: '0',
        style: '',
    },
    rect2: {
        name: '矩形2',
        type: ClipPathTypes.POLYGON,
        style: 'polygon(0% 0%, 80% 0%, 100% 20%, 100% 100%, 0 100%)',
        createPath: (width, height) => `M 0 0 L ${width * 0.8} 0 L ${width} ${height * 0.2} L ${width} ${height} L 0 ${height} Z`,
    },
    rect3: {
        name: '矩形3',
        type: ClipPathTypes.POLYGON,
        style: 'polygon(0% 0%, 80% 0%, 100% 20%, 100% 100%, 20% 100%, 0% 80%)',
        createPath: (width, height) => `M 0 0 L ${width * 0.8} 0 L ${width} ${height * 0.2} L ${width} ${height} L ${width * 0.2} ${height} L 0 ${height * 0.8} Z`,
    },
    roundRect: {
        name: '圆角矩形',
        type: ClipPathTypes.RECT,
        radius: '10px',
        style: 'inset(0 round 10px)',
    },
    ellipse: {
        name: '圆形',
        type: ClipPathTypes.ELLIPSE,
        style: 'ellipse(50% 50% at 50% 50%)',
    },
    triangle: {
        name: '三角形',
        type: ClipPathTypes.POLYGON,
        style: 'polygon(50% 0%, 0% 100%, 100% 100%)',
        createPath: (width, height) => `M ${width * 0.5} 0 L 0 ${height} L ${width} ${height} Z`,
    },
    triangle2: {
        name: '三角形2',
        type: ClipPathTypes.POLYGON,
        style: 'polygon(50% 100%, 0% 0%, 100% 0%)',
        createPath: (width, height) => `M ${width * 0.5} ${height} L 0 0 L ${width} 0 Z`,
    },
    triangle3: {
        name: '三角形3',
        type: ClipPathTypes.POLYGON,
        style: 'polygon(0% 0%, 0% 100%, 100% 100%)',
        createPath: (width, height) => `M 0 0 L 0 ${height} L ${width} ${height} Z`,
    },
    rhombus: {
        name: '菱形',
        type: ClipPathTypes.POLYGON,
        style: 'polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)',
        createPath: (width, height) => `M ${width * 0.5} 0 L ${width} ${height * 0.5} L ${width * 0.5} ${height} L 0 ${height * 0.5} Z`,
    },
    pentagon: {
        name: '五边形',
        type: ClipPathTypes.POLYGON,
        style: 'polygon(50% 0%, 100% 38%, 82% 100%, 18% 100%, 0% 38%)',
        createPath: (width, height) => `M ${width * 0.5} 0 L ${width} ${0.38 * height} L ${0.82 * width} ${height} L ${0.18 * width} ${height} L 0 ${0.38 * height} Z`,
    },
    hexagon: {
        name: '六边形',
        type: ClipPathTypes.POLYGON,
        style: 'polygon(20% 0%, 80% 0%, 100% 50%, 80% 100%, 20% 100%, 0% 50%)',
        createPath: (width, height) => `M ${width * 0.2} 0 L ${width * 0.8} 0 L ${width} ${height * 0.5} L ${width * 0.8} ${height} L ${width * 0.2} ${height} L 0 ${height * 0.5} Z`,
    },
    heptagon: {
        name: '七边形',
        type: ClipPathTypes.POLYGON,
        style: 'polygon(50% 0%, 90% 20%, 100% 60%, 75% 100%, 25% 100%, 0% 60%, 10% 20%)',
        createPath: (width, height) => `M ${width * 0.5} 0 L ${width * 0.9} ${height * 0.2} L ${width} ${height * 0.6} L ${width * 0.75} ${height} L ${width * 0.25} ${height} L 0 ${height * 0.6} L ${width * 0.1} ${height * 0.2} Z`,
    },
    octagon: {
        name: '八边形',
        type: ClipPathTypes.POLYGON,
        style: 'polygon(30% 0%, 70% 0%, 100% 30%, 100% 70%, 70% 100%, 30% 100%, 0% 70%, 0% 30%)',
        createPath: (width, height) => `M ${width * 0.3} 0 L ${width * 0.7} 0 L ${width} ${height * 0.3} L ${width} ${height * 0.7} L ${width * 0.7} ${height} L ${width * 0.3} ${height} L 0 ${height * 0.7} L 0 ${height * 0.3} Z`,
    },
    chevron: {
        name: 'V形',
        type: ClipPathTypes.POLYGON,
        style: 'polygon(75% 0%, 100% 50%, 75% 100%, 0% 100%, 25% 50%, 0% 0%)',
        createPath: (width, height) => `M ${width * 0.75} 0 L ${width} ${height * 0.5} L ${width * 0.75} ${height} L 0 ${height} L ${width * 0.25} ${height * 0.5} L 0 0 Z`,
    },
    point: {
        name: '点',
        type: ClipPathTypes.POLYGON,
        style: 'polygon(0% 0%, 75% 0%, 100% 50%, 75% 100%, 0% 100%)',
        createPath: (width, height) => `M 0 0 L ${width * 0.75} 0 L ${width} ${height * 0.5} L ${width * 0.75} ${height} L 0 ${height} Z`,
    },
    arrow: {
        name: '箭头',
        type: ClipPathTypes.POLYGON,
        style: 'polygon(0% 20%, 60% 20%, 60% 0%, 100% 50%, 60% 100%, 60% 80%, 0% 80%)',
        createPath: (width, height) => `M 0 ${height * 0.2} L ${width * 0.6} ${height * 0.2} L ${width * 0.6} 0 L ${width} ${height * 0.5} L ${width * 0.6} ${height} L ${width * 0.6} ${height * 0.8} L 0 ${height * 0.8} Z`,
    },
    parallelogram: {
        name: '平行四边形',
        type: ClipPathTypes.POLYGON,
        style: 'polygon(30% 0%, 100% 0%, 70% 100%, 0% 100%)',
        createPath: (width, height) => `M ${width * 0.3} 0 L ${width} 0 L ${width * 0.7} ${height} L 0 ${height} Z`,
    },
    parallelogram2: {
        name: '平行四边形2',
        type: ClipPathTypes.POLYGON,
        style: 'polygon(30% 100%, 100% 100%, 70% 0%, 0% 0%)',
        createPath: (width, height) => `M ${width * 0.3} ${height} L ${width} ${height} L ${width * 0.7} 0 L 0 0 Z`,
    },
    trapezoid: {
        name: '梯形',
        type: ClipPathTypes.POLYGON,
        style: 'polygon(25% 0%, 75% 0%, 100% 100%, 0% 100%)',
        createPath: (width, height) => `M ${width * 0.25} 0 L ${width * 0.75} 0 L ${width} ${height} L 0 ${height} Z`,
    },
    trapezoid2: {
        name: '梯形2',
        type: ClipPathTypes.POLYGON,
        style: 'polygon(0% 0%, 100% 0%, 75% 100%, 25% 100%)',
        createPath: (width, height) => `M 0 0 L ${width} 0 L ${width * 0.75} ${height} L ${width * 0.25} ${height} Z`,
    },
};

function useClipImage(element) {
    const clipShape = react.useMemo(() => {
        let _clipShape = CLIPPATHS.rect;
        if (element.clip) {
            const shape = element.clip.shape || ClipPathTypes.RECT;
            _clipShape = CLIPPATHS[shape] ?? CLIPPATHS.rect;
        }
        if (_clipShape.radius !== undefined && element.radius) {
            _clipShape = {
                ..._clipShape,
                radius: `${element.radius}px`,
                style: `inset(0 round ${element.radius}px)`,
            };
        }
        return _clipShape;
    }, [element.clip, element.radius]);
    const imgPosition = react.useMemo(() => {
        if (!element.clip || !element.clip.range) {
            return { top: '0', left: '0', width: '100%', height: '100%' };
        }
        const [start, end] = element.clip.range;
        const widthScale = (end[0] - start[0]) / 100;
        const heightScale = (end[1] - start[1]) / 100;
        const left = start[0] / widthScale;
        const top = start[1] / heightScale;
        return {
            left: -left + '%',
            top: -top + '%',
            width: 100 / widthScale + '%',
            height: 100 / heightScale + '%',
        };
    }, [element.clip]);
    return { clipShape, imgPosition };
}

const FILTER_UNITS = {
    blur: 'px',
    brightness: '%',
    contrast: '%',
    grayscale: '%',
    saturate: '%',
    'hue-rotate': 'deg',
    sepia: '%',
    invert: '%',
    opacity: '%',
};
function useFilter(filters) {
    const filter = react.useMemo(() => {
        if (!filters)
            return '';
        const parts = [];
        for (const [name, value] of Object.entries(filters)) {
            if (value === undefined || value === null || value === '')
                continue;
            const unit = FILTER_UNITS[name] ?? '';
            parts.push(`${name}(${value}${unit})`);
        }
        return parts.join(' ');
    }, [filters]);
    return { filter };
}

function useElementOutline(outline) {
    const outlineWidth = react.useMemo(() => outline?.width ?? 0, [outline?.width]);
    const outlineStyle = react.useMemo(() => outline?.style || 'solid', [outline?.style]);
    const outlineColor = react.useMemo(() => outline?.color || '#d14424', [outline?.color]);
    const strokeDashArray = react.useMemo(() => {
        const size = outlineWidth;
        if (outlineStyle === 'dashed')
            return size <= 6 ? `${size * 4.5} ${size * 2}` : `${size * 4} ${size * 1.5}`;
        if (outlineStyle === 'dotted')
            return size <= 6 ? `${size * 1.8} ${size * 1.6}` : `${size * 1.5} ${size * 1.2}`;
        return '0 0';
    }, [outlineWidth, outlineStyle]);
    return { outlineWidth, outlineStyle, outlineColor, strokeDashArray };
}

function ImageRectOutline({ width, height, outline, radius = '0' }) {
    const { outlineWidth, outlineColor, strokeDashArray } = useElementOutline(outline);
    if (!outline)
        return null;
    return (jsxRuntime.jsx("svg", { style: { position: 'absolute', top: 0, left: 0, zIndex: 2, overflow: 'visible' }, width: width, height: height, children: jsxRuntime.jsx("rect", { vectorEffect: "non-scaling-stroke", strokeLinecap: "butt", strokeMiterlimit: "8", fill: "transparent", rx: radius, ry: radius, width: width, height: height, stroke: outlineColor, strokeWidth: outlineWidth, strokeDasharray: strokeDashArray }) }));
}
function ImageEllipseOutline({ width, height, outline }) {
    const { outlineWidth, outlineColor, strokeDashArray } = useElementOutline(outline);
    if (!outline)
        return null;
    return (jsxRuntime.jsx("svg", { style: { position: 'absolute', top: 0, left: 0, zIndex: 2, overflow: 'visible' }, width: width, height: height, children: jsxRuntime.jsx("ellipse", { vectorEffect: "non-scaling-stroke", strokeLinecap: "butt", strokeMiterlimit: "8", fill: "transparent", cx: width / 2, cy: height / 2, rx: width / 2, ry: height / 2, stroke: outlineColor, strokeWidth: outlineWidth, strokeDasharray: strokeDashArray }) }));
}
function ImagePolygonOutline({ width, height, createPath, outline }) {
    const { outlineWidth, outlineColor, strokeDashArray } = useElementOutline(outline);
    if (!outline)
        return null;
    return (jsxRuntime.jsx("svg", { style: { position: 'absolute', top: 0, left: 0, zIndex: 2, overflow: 'visible' }, width: width, height: height, children: jsxRuntime.jsx("path", { vectorEffect: "non-scaling-stroke", strokeLinecap: "butt", strokeMiterlimit: "8", fill: "transparent", d: createPath(width, height), stroke: outlineColor, strokeWidth: outlineWidth, strokeDasharray: strokeDashArray }) }));
}
function ImageOutline({ elementInfo }) {
    const { clipShape } = useClipImage(elementInfo);
    return (jsxRuntime.jsxs("div", { className: "image-outline", children: [clipShape.type === 'rect' && (jsxRuntime.jsx(ImageRectOutline, { width: elementInfo.width, height: elementInfo.height, radius: clipShape.radius, outline: elementInfo.outline })), clipShape.type === 'ellipse' && (jsxRuntime.jsx(ImageEllipseOutline, { width: elementInfo.width, height: elementInfo.height, outline: elementInfo.outline })), clipShape.type === 'polygon' && clipShape.createPath && (jsxRuntime.jsx(ImagePolygonOutline, { width: elementInfo.width, height: elementInfo.height, outline: elementInfo.outline, createPath: clipShape.createPath }))] }));
}

function BaseImageElement({ elementInfo, renderImage }) {
    const { shadowStyle } = useElementShadow(elementInfo.shadow);
    const { flipStyle } = useElementFlip(elementInfo.flipH, elementInfo.flipV);
    const { clipShape, imgPosition } = useClipImage(elementInfo);
    const { filter } = useFilter(elementInfo.filters);
    const src = elementInfo.src;
    // Soft-edge feather (a:softEdge): fade the image alpha to transparent over
    // `softEdge` px at every edge. Two intersecting linear-gradient masks feather
    // all four sides (corners get both). html2canvas-pro ignores CSS masks, so
    // slideToPng bakes the same feather into pixels via the data-soft-edge hook.
    const softEdge = elementInfo.softEdge && elementInfo.softEdge > 0 ? elementInfo.softEdge : undefined;
    const softEdgeMaskStyle = softEdge
        ? (() => {
            const grad = (dir) => `linear-gradient(${dir}, transparent 0, #000 ${softEdge}px, #000 calc(100% - ${softEdge}px), transparent 100%)`;
            const mask = `${grad('to right')}, ${grad('to bottom')}`;
            return {
                maskImage: mask,
                WebkitMaskImage: mask,
                maskComposite: 'intersect',
                WebkitMaskComposite: 'source-in',
                maskRepeat: 'no-repeat',
                WebkitMaskRepeat: 'no-repeat',
            };
        })()
        : {};
    return (jsxRuntime.jsx("div", { className: "element-content", style: {
            position: 'absolute',
            top: `${elementInfo.top}px`,
            left: `${elementInfo.left}px`,
            width: `${elementInfo.width}px`,
            height: `${elementInfo.height}px`,
        }, children: jsxRuntime.jsx("div", { style: {
                width: '100%',
                height: '100%',
                transform: `rotate(${elementInfo.rotate}deg)`,
            }, children: jsxRuntime.jsxs("div", { style: {
                    position: 'relative',
                    width: '100%',
                    height: '100%',
                    filter: shadowStyle ? `drop-shadow(${shadowStyle})` : '',
                    transform: flipStyle,
                }, children: [jsxRuntime.jsx(ImageOutline, { elementInfo: elementInfo }), jsxRuntime.jsx("div", { style: {
                            position: 'relative',
                            width: '100%',
                            height: '100%',
                            overflow: 'hidden',
                            clipPath: clipShape.style,
                        }, children: renderImage ? (renderImage(elementInfo, src)) : src ? (jsxRuntime.jsxs(jsxRuntime.Fragment, { children: [jsxRuntime.jsx("img", { src: src, draggable: false, "data-soft-edge": softEdge || undefined, style: {
                                        position: 'absolute',
                                        top: imgPosition.top,
                                        left: imgPosition.left,
                                        width: imgPosition.width,
                                        height: imgPosition.height,
                                        maxWidth: 'none',
                                        maxHeight: 'none',
                                        filter,
                                        ...softEdgeMaskStyle,
                                    }, alt: "", onDragStart: (e) => e.preventDefault() }), elementInfo.colorMask && (jsxRuntime.jsx("div", { style: {
                                        position: 'absolute',
                                        inset: 0,
                                        backgroundColor: elementInfo.colorMask,
                                    } }))] })) : null })] }) }) }));
}

function ElementOutline({ width, height, outline }) {
    const { outlineWidth, outlineColor, strokeDashArray } = useElementOutline(outline);
    if (!outline)
        return null;
    return (jsxRuntime.jsx("svg", { className: "element-outline", style: { position: 'absolute', top: 0, left: 0, overflow: 'visible' }, width: width, height: height, children: jsxRuntime.jsx("path", { vectorEffect: "non-scaling-stroke", strokeLinecap: "butt", strokeMiterlimit: "8", fill: "transparent", d: `M0,0 L${width},0 L${width},${height} L0,${height} Z`, stroke: outlineColor, strokeWidth: outlineWidth, strokeDasharray: strokeDashArray }) }));
}

function BaseTextElement({ elementInfo, target }) {
    const { shadowStyle } = useElementShadow(elementInfo.shadow);
    const vAlign = elementInfo.vAlign ?? 'top';
    const justifyContent = vAlign === 'middle' ? 'center' : vAlign === 'bottom' ? 'flex-end' : 'flex-start';
    return (jsxRuntime.jsx("div", { className: "base-element-text", style: {
            position: 'absolute',
            top: `${elementInfo.top}px`,
            left: `${elementInfo.left}px`,
            width: `${elementInfo.width}px`,
            height: `${elementInfo.height}px`,
            // PowerPoint fills the entire shape rectangle with its solid/gradient
            // fill, regardless of how much vertical room the text actually
            // occupies. The inner .element-content div has height: auto so flex
            // alignment can park the text at top/middle/bottom — but if the
            // background lived there, a tall shape with short text (e.g. the 22
            // empty paragraphs that author full-bleed black slide backgrounds in
            // some decks) would only fill the content height and the slide's own
            // background would bleed through below.
            backgroundColor: elementInfo.fill,
            opacity: elementInfo.opacity,
        }, children: jsxRuntime.jsx("div", { className: "rotate-wrapper", style: {
                width: '100%',
                height: '100%',
                transform: `rotate(${elementInfo.rotate}deg)`,
                display: 'flex',
                flexDirection: 'column',
                justifyContent,
            }, children: jsxRuntime.jsxs("div", { className: "element-content slide-renderer-prose", style: {
                    position: 'relative',
                    width: elementInfo.vertical ? 'auto' : '100%',
                    height: elementInfo.vertical ? '100%' : 'auto',
                    textShadow: shadowStyle,
                    lineHeight: elementInfo.lineHeight,
                    letterSpacing: elementInfo.wordSpace !== undefined ? `${elementInfo.wordSpace}px` : undefined,
                    color: elementInfo.defaultColor,
                    fontFamily: elementInfo.defaultFontName,
                    writingMode: elementInfo.vertical ? 'vertical-rl' : 'horizontal-tb',
                    ...(elementInfo.paragraphSpace !== undefined
                        ? { '--paragraphSpace': `${elementInfo.paragraphSpace}px` }
                        : null),
                }, children: [jsxRuntime.jsx(ElementOutline, { width: elementInfo.width, height: elementInfo.height, outline: elementInfo.outline }), jsxRuntime.jsx("div", { className: "text ProseMirror-static", style: {
                            position: 'relative',
                            pointerEvents: target === 'thumbnail' ? 'none' : undefined,
                        }, dangerouslySetInnerHTML: { __html: elementInfo.content } })] }) }) }));
}

function useElementFill(element, source) {
    const fill = react.useMemo(() => {
        if (element.pattern)
            return `url(#${source}-pattern-${element.id})`;
        if (element.gradient)
            return `url(#${source}-gradient-${element.id})`;
        return element.fill || 'none';
    }, [element.pattern, element.gradient, element.fill, element.id, source]);
    return { fill };
}

function GradientDefs({ id, type, colors, rotate = 0 }) {
    if (type === 'linear') {
        return (jsxRuntime.jsx("linearGradient", { id: id, x1: "0%", y1: "0%", x2: "100%", y2: "0%", gradientTransform: `rotate(${rotate},0.5,0.5)`, children: colors.map((item, index) => (jsxRuntime.jsx("stop", { offset: `${item.pos}%`, stopColor: item.color }, index))) }));
    }
    return (jsxRuntime.jsx("radialGradient", { id: id, children: colors.map((item, index) => (jsxRuntime.jsx("stop", { offset: `${item.pos}%`, stopColor: item.color }, index))) }));
}

function PatternDefs({ id, src }) {
    return (jsxRuntime.jsx("pattern", { id: id, patternContentUnits: "objectBoundingBox", patternUnits: "objectBoundingBox", width: "1", height: "1", children: jsxRuntime.jsx("image", { href: src, width: "1", height: "1", preserveAspectRatio: "xMidYMid slice" }) }));
}

/**
 * Bounding box of a path's coordinates (path/viewBox space). Uses control
 * points for curves (a safe superset). Handles the commands our shapes emit
 * (M/L/C/Q/S/H/V/A/T/Z, absolute). Returns null if no coordinates.
 */
function pathCoordBBox(d) {
    const tokens = d.match(/[a-zA-Z]|-?\d*\.?\d+(?:e[-+]?\d+)?/gi);
    if (!tokens)
        return null;
    let i = 0;
    let cmd = '';
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    const addX = (x) => {
        if (x < minX)
            minX = x;
        if (x > maxX)
            maxX = x;
    };
    const addY = (y) => {
        if (y < minY)
            minY = y;
        if (y > maxY)
            maxY = y;
    };
    const num = () => parseFloat(tokens[i++]);
    while (i < tokens.length) {
        // Path commands are single letters. Use an anchored test so number tokens
        // in scientific notation (e.g. "4.74e-16") aren't misread as commands.
        if (/^[a-zA-Z]$/.test(tokens[i])) {
            cmd = tokens[i];
            i++;
        }
        const c = cmd.toUpperCase();
        if (c === 'M' || c === 'L' || c === 'T') {
            addX(num());
            addY(num());
        }
        else if (c === 'C') {
            addX(num());
            addY(num());
            addX(num());
            addY(num());
            addX(num());
            addY(num());
        }
        else if (c === 'Q' || c === 'S') {
            addX(num());
            addY(num());
            addX(num());
            addY(num());
        }
        else if (c === 'H') {
            addX(num());
        }
        else if (c === 'V') {
            addY(num());
        }
        else if (c === 'A') {
            num();
            num();
            num();
            num();
            num();
            addX(num());
            addY(num());
        }
        else if (c === 'Z') ;
        else {
            i++; // unknown token, skip to avoid infinite loop
        }
    }
    if (!Number.isFinite(minX) ||
        !Number.isFinite(minY) ||
        !Number.isFinite(maxX) ||
        !Number.isFinite(maxY)) {
        return null;
    }
    return { minX, minY, maxX, maxY };
}
function BaseShapeElement({ elementInfo }) {
    const { fill } = useElementFill(elementInfo, 'base');
    const { outlineWidth, outlineColor, strokeDashArray } = useElementOutline(elementInfo.outline);
    const { shadowStyle } = useElementShadow(elementInfo.shadow);
    const { flipStyle } = useElementFlip(elementInfo.flipH, elementInfo.flipV);
    const text = elementInfo.text || {
        content: '',
        align: 'middle',
        defaultFontName: 'Microsoft YaHei',
        defaultColor: '#333333',
    };
    const justifyContent = text.align === 'top' ? 'flex-start' : text.align === 'bottom' ? 'flex-end' : 'center';
    return (jsxRuntime.jsx("div", { className: "base-element-shape", style: {
            position: 'absolute',
            top: `${elementInfo.top}px`,
            left: `${elementInfo.left}px`,
            width: `${elementInfo.width}px`,
            height: `${elementInfo.height}px`,
        }, children: jsxRuntime.jsx("div", { className: "rotate-wrapper", style: {
                width: '100%',
                height: '100%',
                transform: `rotate(${elementInfo.rotate}deg)`,
            }, children: jsxRuntime.jsxs("div", { className: "element-content", style: {
                    position: 'relative',
                    width: '100%',
                    height: '100%',
                    opacity: elementInfo.opacity,
                    filter: shadowStyle ? `drop-shadow(${shadowStyle})` : '',
                    transform: flipStyle,
                    color: text.defaultColor,
                    fontFamily: text.defaultFontName,
                }, children: [(() => {
                        // The shape's path can extend OUTSIDE its width×height box (e.g.
                        // curved connectors whose extreme adj values bulge the curve far
                        // past the bbox). A browser shows that via overflow:visible, but
                        // html2canvas-pro rasterizes each SVG to its width×height viewport
                        // and CLIPS the overflow — turning connector arcs into stubs in the
                        // exported PNG. Fix: grow the SVG viewport to contain the full path
                        // bbox and offset it back, so the geometry renders in the exact same
                        // place but nothing falls outside the captured viewport.
                        const sx = elementInfo.width / (elementInfo.viewBox[0] || elementInfo.width || 1);
                        const sy = elementInfo.height / (elementInfo.viewBox[1] || elementInfo.height || 1);
                        const bbox = pathCoordBBox(elementInfo.path);
                        const CAP = 4000; // guard against pathological coords blowing up the SVG
                        let padL = 0;
                        let padT = 0;
                        let padR = 0;
                        let padB = 0;
                        if (bbox) {
                            padL = Math.min(CAP, Math.max(0, -bbox.minX * sx));
                            padT = Math.min(CAP, Math.max(0, -bbox.minY * sy));
                            padR = Math.min(CAP, Math.max(0, bbox.maxX * sx - elementInfo.width));
                            padB = Math.min(CAP, Math.max(0, bbox.maxY * sy - elementInfo.height));
                        }
                        return (jsxRuntime.jsxs("svg", { overflow: "visible", width: elementInfo.width + padL + padR, height: elementInfo.height + padT + padB, style: {
                                position: 'absolute',
                                left: -padL,
                                top: -padT,
                                transformOrigin: '0 0',
                                overflow: 'visible',
                                display: 'block',
                            }, children: [jsxRuntime.jsxs("defs", { children: [elementInfo.pattern && (jsxRuntime.jsx(PatternDefs, { id: `base-pattern-${elementInfo.id}`, src: elementInfo.pattern })), elementInfo.gradient && (jsxRuntime.jsx(GradientDefs, { id: `base-gradient-${elementInfo.id}`, type: elementInfo.gradient.type, colors: elementInfo.gradient.colors, rotate: elementInfo.gradient.rotate }))] }), jsxRuntime.jsx("g", { transform: `translate(${padL},${padT}) scale(${sx}, ${sy})`, children: jsxRuntime.jsx("path", { vectorEffect: "non-scaling-stroke", strokeLinecap: "butt", strokeMiterlimit: "8", d: elementInfo.path, fill: fill, stroke: outlineColor, strokeWidth: outlineWidth, strokeDasharray: strokeDashArray }) })] }));
                    })(), jsxRuntime.jsx("div", { className: "shape-text", style: {
                            position: 'absolute',
                            inset: 0,
                            display: 'flex',
                            flexDirection: 'column',
                            justifyContent,
                            overflowWrap: 'break-word',
                            lineHeight: text.lineHeight,
                            letterSpacing: `${text.wordSpace || 0}px`,
                            // PowerPoint/WPS 在 group flipH/flipV 时只镜像几何与位置，文字字形保持
                            // 正向。父层 element-content 已应用 flipStyle 镜像 SVG path；这里给文字
                            // 叠加同一个 flipStyle，两次 flip 抵消，让文字保持正向。
                            transform: flipStyle,
                        }, children: jsxRuntime.jsx("div", { className: "ProseMirror-static slide-renderer-prose", style: {
                                // @ts-expect-error CSS custom properties
                                '--paragraphSpace': `${text.paragraphSpace === undefined ? 5 : text.paragraphSpace}px`,
                            }, dangerouslySetInnerHTML: { __html: text.content } }) })] }) }) }));
}

const getRectRotatedRange = (element) => {
    const { left, top, width, height, rotate = 0 } = element;
    const radius = Math.sqrt(Math.pow(width, 2) + Math.pow(height, 2)) / 2;
    const auxiliaryAngle = (Math.atan(height / width) * 180) / Math.PI;
    const tlbraRadian = ((180 - rotate - auxiliaryAngle) * Math.PI) / 180;
    const trblaRadian = ((auxiliaryAngle - rotate) * Math.PI) / 180;
    const middleLeft = left + width / 2;
    const middleTop = top + height / 2;
    const xAxis = [
        middleLeft + radius * Math.cos(tlbraRadian),
        middleLeft + radius * Math.cos(trblaRadian),
        middleLeft - radius * Math.cos(tlbraRadian),
        middleLeft - radius * Math.cos(trblaRadian),
    ];
    const yAxis = [
        middleTop - radius * Math.sin(tlbraRadian),
        middleTop - radius * Math.sin(trblaRadian),
        middleTop + radius * Math.sin(tlbraRadian),
        middleTop + radius * Math.sin(trblaRadian),
    ];
    return {
        xRange: [Math.min(...xAxis), Math.max(...xAxis)],
        yRange: [Math.min(...yAxis), Math.max(...yAxis)],
    };
};
const getElementRange = (element) => {
    let minX, maxX, minY, maxY;
    if (element.type === 'line') {
        minX = element.left;
        maxX = element.left + Math.max(element.start[0], element.end[0]);
        minY = element.top;
        maxY = element.top + Math.max(element.start[1], element.end[1]);
    }
    else if ('rotate' in element && element.rotate) {
        const { left, top, width, height, rotate } = element;
        const { xRange, yRange } = getRectRotatedRange({ left, top, width, height, rotate });
        minX = xRange[0];
        maxX = xRange[1];
        minY = yRange[0];
        maxY = yRange[1];
    }
    else {
        minX = element.left;
        maxX = element.left + element.width;
        minY = element.top;
        maxY = element.top + element.height;
    }
    return { minX, maxX, minY, maxY };
};
const getTableSubThemeColor = (themeColor) => {
    const rgba = tinycolor(themeColor);
    return [rgba.setAlpha(0.3).toRgbString(), rgba.setAlpha(0.1).toRgbString()];
};
const getLineElementPath = (element) => {
    const startArr = Array.isArray(element.start) ? element.start : [0, 0];
    const endArr = Array.isArray(element.end) ? element.end : [100, 100];
    const start = startArr.join(',');
    const end = endArr.join(',');
    if (element.broken) {
        const mid = element.broken.join(',');
        return `M${start} L${mid} L${end}`;
    }
    else if (element.broken2) {
        const { minX, maxX, minY, maxY } = getElementRange(element);
        if (maxX - minX >= maxY - minY)
            return `M${start} L${element.broken2[0]},${startArr[1]} L${element.broken2[0]},${endArr[1]} ${end}`;
        return `M${start} L${startArr[0]},${element.broken2[1]} L${endArr[0]},${element.broken2[1]} ${end}`;
    }
    else if (element.curve) {
        const mid = element.curve.join(',');
        return `M${start} Q${mid} ${end}`;
    }
    else if (element.cubic) {
        const [c1, c2] = element.cubic;
        const p1 = c1.join(',');
        const p2 = c2.join(',');
        return `M${start} C${p1} ${p2} ${end}`;
    }
    return `M${start} L${end}`;
};

const pathMap = {
    dot: 'm0 5a5 5 0 1 0 10 0a5 5 0 1 0 -10 0z',
    arrow: 'M0,0 L10,5 0,10 Z',
};
const rotateMap = {
    'arrow-start': 180,
    'arrow-end': 0,
};
function LinePointMarker({ id, position, type, baseSize, color }) {
    const path = pathMap[type];
    const rotate = rotateMap[`${type}-${position}`] || 0;
    const size = baseSize < 2 ? 2 : baseSize;
    return (jsxRuntime.jsx("marker", { id: `${id}-${type}-${position}`, markerUnits: "userSpaceOnUse", orient: "auto", markerWidth: size * 3, markerHeight: size * 3, refX: size * 1.5, refY: size * 1.5, children: jsxRuntime.jsx("path", { d: path, fill: color, transform: `scale(${size * 0.3}, ${size * 0.3}) rotate(${rotate}, 5, 5)` }) }));
}

const DRAW_ANIMATION_MS = 600;
function BaseLineElement({ elementInfo, animate }) {
    const { shadowStyle } = useElementShadow(elementInfo.shadow);
    const pathRef = react.useRef(null);
    const [drawComplete, setDrawComplete] = react.useState(!animate);
    const svgWidth = react.useMemo(() => {
        const width = Math.abs(elementInfo.start[0] - elementInfo.end[0]);
        return width < 24 ? 24 : width;
    }, [elementInfo.start, elementInfo.end]);
    const svgHeight = react.useMemo(() => {
        const height = Math.abs(elementInfo.start[1] - elementInfo.end[1]);
        return height < 24 ? 24 : height;
    }, [elementInfo.start, elementInfo.end]);
    const lineDashArray = react.useMemo(() => {
        const size = elementInfo.width;
        if (elementInfo.style === 'dashed')
            return size <= 8 ? `${size * 5} ${size * 2.5}` : `${size * 5} ${size * 1.5}`;
        if (elementInfo.style === 'dotted')
            return size <= 8 ? `${size * 1.8} ${size * 1.6}` : `${size * 1.5} ${size * 1.2}`;
        return '0 0';
    }, [elementInfo.width, elementInfo.style]);
    const path = react.useMemo(() => getLineElementPath(elementInfo), [elementInfo]);
    react.useEffect(() => {
        if (!animate)
            return;
        const pathEl = pathRef.current;
        if (!pathEl)
            return;
        const length = pathEl.getTotalLength();
        if (length === 0) {
            const t = setTimeout(() => setDrawComplete(true), 0);
            return () => clearTimeout(t);
        }
        pathEl.style.strokeDasharray = `${length}`;
        pathEl.style.strokeDashoffset = `${length}`;
        pathEl.style.transition = 'none';
        pathEl.getBoundingClientRect();
        pathEl.style.transition = `stroke-dashoffset ${DRAW_ANIMATION_MS}ms ease-out`;
        pathEl.style.strokeDashoffset = '0';
        const timer = setTimeout(() => {
            pathEl.style.transition = 'none';
            pathEl.style.strokeDasharray = '';
            pathEl.style.strokeDashoffset = '';
            setDrawComplete(true);
        }, DRAW_ANIMATION_MS + 50);
        return () => clearTimeout(timer);
    }, [animate]);
    return (jsxRuntime.jsx("div", { className: "base-element-line", style: {
            position: 'absolute',
            top: `${elementInfo.top}px`,
            left: `${elementInfo.left}px`,
        }, children: jsxRuntime.jsx("div", { className: "element-content", style: {
                position: 'relative',
                width: '100%',
                height: '100%',
                filter: shadowStyle ? `drop-shadow(${shadowStyle})` : '',
            }, children: jsxRuntime.jsxs("svg", { overflow: "visible", width: svgWidth, height: svgHeight, style: { transformOrigin: '0 0', overflow: 'visible' }, children: [jsxRuntime.jsxs("defs", { children: [elementInfo.points[0] && (jsxRuntime.jsx(LinePointMarker, { id: elementInfo.id, position: "start", type: elementInfo.points[0], color: elementInfo.color, baseSize: elementInfo.width })), elementInfo.points[1] && (jsxRuntime.jsx(LinePointMarker, { id: elementInfo.id, position: "end", type: elementInfo.points[1], color: elementInfo.color, baseSize: elementInfo.width }))] }), jsxRuntime.jsx("path", { ref: pathRef, d: path, stroke: elementInfo.color, strokeWidth: elementInfo.width, strokeDasharray: lineDashArray, fill: "none", markerStart: drawComplete && elementInfo.points[0]
                            ? `url(#${elementInfo.id}-${elementInfo.points[0]}-start)`
                            : '', markerEnd: drawComplete && elementInfo.points[1]
                            ? `url(#${elementInfo.id}-${elementInfo.points[1]}-end)`
                            : '' })] }) }) }));
}

const getChartOption = ({ type, data, themeColors, textColor, lineColor, lineSmooth, stack, }) => {
    const textStyle = textColor ? { color: textColor } : {};
    const axisLine = textColor ? { lineStyle: { color: textColor } } : undefined;
    const axisLabel = textColor ? { color: textColor } : undefined;
    const splitLine = lineColor ? { lineStyle: { color: lineColor } } : {};
    if (!Array.isArray(data?.series) || data.series.length === 0) {
        return null;
    }
    const legend = data.series.length > 1 ? { top: 'bottom', textStyle } : undefined;
    if (type === 'bar') {
        return {
            color: themeColors,
            textStyle,
            legend,
            xAxis: { type: 'category', data: data.labels, axisLine, axisLabel },
            yAxis: { type: 'value', axisLine, axisLabel, splitLine },
            series: data.series.map((item, index) => {
                const seriesItem = {
                    data: item,
                    name: data.legends[index],
                    type: 'bar',
                    label: { show: true },
                    itemStyle: { borderRadius: [2, 2, 0, 0] },
                };
                if (stack)
                    seriesItem.stack = 'A';
                return seriesItem;
            }),
        };
    }
    if (type === 'column') {
        return {
            color: themeColors,
            textStyle,
            legend,
            yAxis: { type: 'category', data: data.labels, axisLine, axisLabel },
            xAxis: { type: 'value', axisLine, axisLabel, splitLine },
            series: data.series.map((item, index) => {
                const seriesItem = {
                    data: item,
                    name: data.legends[index],
                    type: 'bar',
                    label: { show: true },
                    itemStyle: { borderRadius: [0, 2, 2, 0] },
                };
                if (stack)
                    seriesItem.stack = 'A';
                return seriesItem;
            }),
        };
    }
    if (type === 'line') {
        return {
            color: themeColors,
            textStyle,
            legend,
            xAxis: { type: 'category', data: data.labels, axisLine, axisLabel },
            yAxis: { type: 'value', axisLine, axisLabel, splitLine },
            series: data.series.map((item, index) => {
                const seriesItem = {
                    data: item,
                    name: data.legends[index],
                    type: 'line',
                    smooth: lineSmooth,
                    label: { show: true },
                };
                if (stack)
                    seriesItem.stack = 'A';
                return seriesItem;
            }),
        };
    }
    if (type === 'pie') {
        const series0 = data.series[0];
        if (!Array.isArray(series0))
            return null;
        return {
            color: themeColors,
            textStyle,
            legend: { top: 'bottom', textStyle },
            series: [
                {
                    data: series0.map((item, index) => ({ value: item, name: data.labels[index] })),
                    label: textColor ? { color: textColor } : {},
                    type: 'pie',
                    radius: '70%',
                    emphasis: {
                        itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' },
                        label: { show: true, fontSize: 14, fontWeight: 'bold' },
                    },
                },
            ],
        };
    }
    if (type === 'ring') {
        const series0 = data.series[0];
        if (!Array.isArray(series0))
            return null;
        return {
            color: themeColors,
            textStyle,
            legend: { top: 'bottom', textStyle },
            series: [
                {
                    data: series0.map((item, index) => ({ value: item, name: data.labels[index] })),
                    label: textColor ? { color: textColor } : {},
                    type: 'pie',
                    radius: ['40%', '70%'],
                    padAngle: 1,
                    avoidLabelOverlap: false,
                    itemStyle: { borderRadius: 4 },
                    emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
                },
            ],
        };
    }
    if (type === 'area') {
        return {
            color: themeColors,
            textStyle,
            legend,
            xAxis: { type: 'category', boundaryGap: false, data: data.labels, axisLine, axisLabel },
            yAxis: { type: 'value', axisLine, axisLabel, splitLine },
            series: data.series.map((item, index) => {
                const seriesItem = {
                    data: item,
                    name: data.legends[index],
                    type: 'line',
                    areaStyle: {},
                    label: { show: true },
                };
                if (stack)
                    seriesItem.stack = 'A';
                return seriesItem;
            }),
        };
    }
    if (type === 'radar') {
        return {
            color: themeColors,
            textStyle,
            legend,
            radar: {
                indicator: data.labels.map((item) => ({ name: item })),
                splitLine,
                axisLine: lineColor ? { lineStyle: { color: lineColor } } : undefined,
            },
            series: [
                {
                    data: data.series.map((item, index) => ({ value: item, name: data.legends[index] })),
                    type: 'radar',
                },
            ],
        };
    }
    if (type === 'scatter') {
        const series0 = data.series[0];
        if (!Array.isArray(series0))
            return null;
        const formatedData = [];
        for (let i = 0; i < series0.length; i++) {
            const x = series0[i];
            const y = data.series[1]?.[i] ?? x;
            formatedData.push([x, y]);
        }
        return {
            color: themeColors,
            textStyle,
            xAxis: { axisLine, axisLabel, splitLine },
            yAxis: { axisLine, axisLabel, splitLine },
            series: [{ symbolSize: 12, data: formatedData, type: 'scatter' }],
        };
    }
    return null;
};

echarts__namespace.use([
    charts.BarChart,
    charts.LineChart,
    charts.PieChart,
    charts.ScatterChart,
    charts.RadarChart,
    components.LegendComponent,
    renderers.SVGRenderer,
]);
function Chart({ width: _width, height: _height, type, data, themeColors: rawThemeColors, textColor, lineColor, options, }) {
    const chartRef = react.useRef(null);
    const chartInstance = react.useRef(null);
    const themeColors = react.useMemo(() => {
        let colors = [];
        if (rawThemeColors.length >= 10) {
            colors = rawThemeColors;
        }
        else if (rawThemeColors.length === 1) {
            colors = tinycolor(rawThemeColors[0])
                .analogous(10)
                .map((color) => color.toRgbString());
        }
        else {
            const len = rawThemeColors.length;
            const supplement = tinycolor(rawThemeColors[len - 1])
                .analogous(10 + 1 - len)
                .map((color) => color.toRgbString());
            colors = [...rawThemeColors.slice(0, len - 1), ...supplement];
        }
        return colors;
    }, [rawThemeColors]);
    const updateOption = react.useMemo(() => {
        return () => {
            if (!chartInstance.current)
                return;
            const option = getChartOption({
                type,
                data,
                themeColors,
                textColor,
                lineColor,
                lineSmooth: options?.lineSmooth || false,
                stack: options?.stack || false,
            });
            if (option) {
                chartInstance.current.setOption(option, true);
            }
        };
    }, [type, data, themeColors, textColor, lineColor, options]);
    react.useEffect(() => {
        if (!chartRef.current)
            return;
        chartInstance.current = echarts__namespace.init(chartRef.current, null, { renderer: 'svg' });
        updateOption();
        const resizeObserver = new ResizeObserver(() => {
            chartInstance.current?.resize();
        });
        resizeObserver.observe(chartRef.current);
        return () => {
            resizeObserver.disconnect();
            chartInstance.current?.dispose();
            chartInstance.current = null;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps -- Init-only effect
    }, []);
    react.useEffect(() => {
        updateOption();
    }, [updateOption]);
    return jsxRuntime.jsx("div", { ref: chartRef, className: "chart", style: { width: '100%', height: '100%' } });
}

function BaseChartElement({ elementInfo, target }) {
    return (jsxRuntime.jsx("div", { className: "base-element-chart", style: {
            position: 'absolute',
            top: `${elementInfo.top}px`,
            left: `${elementInfo.left}px`,
            width: `${elementInfo.width}px`,
            height: `${elementInfo.height}px`,
            pointerEvents: target === 'thumbnail' ? 'none' : undefined,
        }, children: jsxRuntime.jsx("div", { className: "rotate-wrapper", style: {
                width: '100%',
                height: '100%',
                transform: `rotate(${elementInfo.rotate}deg)`,
            }, children: jsxRuntime.jsxs("div", { className: "element-content", style: { width: '100%', height: '100%', backgroundColor: elementInfo.fill }, children: [jsxRuntime.jsx(ElementOutline, { width: elementInfo.width, height: elementInfo.height, outline: elementInfo.outline }), jsxRuntime.jsx(Chart, { width: elementInfo.width, height: elementInfo.height, type: elementInfo.chartType, data: elementInfo.data, themeColors: elementInfo.themeColors, textColor: elementInfo.textColor, lineColor: elementInfo.lineColor, options: elementInfo.options })] }) }) }));
}

function BaseLatexElement({ elementInfo }) {
    return (jsxRuntime.jsx("div", { className: "base-element-latex", style: {
            position: 'absolute',
            top: `${elementInfo.top}px`,
            left: `${elementInfo.left}px`,
            width: `${elementInfo.width}px`,
            height: `${elementInfo.height}px`,
        }, children: jsxRuntime.jsx("div", { className: "rotate-wrapper", style: {
                width: '100%',
                height: '100%',
                transform: `rotate(${elementInfo.rotate}deg)`,
            }, children: jsxRuntime.jsx("div", { className: "element-content", style: {
                    position: 'relative',
                    width: '100%',
                    height: '100%',
                    // KaTeX glyphs inherit `color`; apply the formula's resolved color
                    // (e.g. 蓝色权重) so it isn't forced to the browser default.
                    ...(elementInfo.color ? { color: elementInfo.color } : {}),
                }, children: elementInfo.html ? (jsxRuntime.jsx(KatexContent, { html: elementInfo.html, width: elementInfo.width, height: elementInfo.height, align: elementInfo.align })) : elementInfo.path && elementInfo.viewBox ? (jsxRuntime.jsx("svg", { overflow: "visible", width: elementInfo.width, height: elementInfo.height, stroke: elementInfo.color, strokeWidth: elementInfo.strokeWidth, fill: "none", strokeLinecap: "round", strokeLinejoin: "round", style: { transformOrigin: '0 0', overflow: 'visible' }, children: jsxRuntime.jsx("g", { transform: `scale(${elementInfo.width / elementInfo.viewBox[0]}, ${elementInfo.height / elementInfo.viewBox[1]}) translate(0,0) matrix(1,0,0,1,0,0)`, children: jsxRuntime.jsx("path", { d: elementInfo.path }) }) })) : null }) }) }));
}
const ALIGN_MAP = {
    left: 'flex-start',
    center: 'center',
    right: 'flex-end',
};
function KatexContent({ html, width, height, align = 'center', }) {
    const innerRef = react.useRef(null);
    const [scale, setScale] = react.useState(1);
    react.useLayoutEffect(() => {
        if (!innerRef.current)
            return;
        const naturalW = innerRef.current.scrollWidth;
        const naturalH = innerRef.current.scrollHeight;
        if (naturalW > 0 && naturalH > 0) {
            // Cap at 1: only ever shrink the formula to fit its box, never enlarge.
            // A short formula sitting in a large frame (e.g. slide 29 的右侧推理框)
            // would otherwise get scaled up to fill the box and render huge.
            setScale(Math.min(width / naturalW, height / naturalH, 1));
        }
    }, [html, width, height]);
    const justify = ALIGN_MAP[align];
    const origin = align === 'left' ? 'left center' : align === 'right' ? 'right center' : 'center center';
    return (jsxRuntime.jsx("div", { style: {
            width,
            height,
            overflow: 'hidden',
            display: 'flex',
            alignItems: 'center',
            justifyContent: justify,
        }, children: jsxRuntime.jsx("div", { ref: innerRef, className: "slide-renderer-prose", style: {
                transformOrigin: origin,
                transform: `scale(${scale})`,
                whiteSpace: 'nowrap',
            }, dangerouslySetInnerHTML: { __html: html } }) }));
}

function getTextStyle(style) {
    if (!style)
        return {};
    const css = {};
    if (style.bold)
        css.fontWeight = 'bold';
    if (style.em)
        css.fontStyle = 'italic';
    if (style.underline)
        css.textDecoration = 'underline';
    if (style.strikethrough) {
        css.textDecoration = css.textDecoration ? `${css.textDecoration} line-through` : 'line-through';
    }
    if (style.color)
        css.color = style.color;
    if (style.backcolor)
        css.backgroundColor = style.backcolor;
    if (style.fontsize)
        css.fontSize = style.fontsize;
    if (style.fontname)
        css.fontFamily = style.fontname;
    if (style.align)
        css.textAlign = style.align;
    return css;
}

function cellBorderCss(b) {
    if (!b || b.width <= 0)
        return undefined;
    const style = b.style === 'dashed' || b.style === 'dotted' ? b.style : 'solid';
    return `${b.width}px ${style} ${b.color}`;
}
function StaticTable({ elementInfo }) {
    const { width, data, colWidths, cellMinHeight, rowHeights, outline, theme } = elementInfo;
    const [subThemeDark, subThemeLight] = react.useMemo(() => {
        if (!theme)
            return ['', ''];
        return getTableSubThemeColor(theme.color);
    }, [theme]);
    const borderStyle = react.useMemo(() => {
        if (!outline)
            return 'none';
        const w = outline.width ?? 1;
        const c = outline.color ?? '#000';
        const s = outline.style === 'dashed' ? 'dashed' : 'solid';
        return `${w}px ${s} ${c}`;
    }, [outline]);
    const getCellBg = (rowIdx, colIdx, cellBackcolor) => {
        if (cellBackcolor)
            return cellBackcolor;
        if (!theme)
            return undefined;
        const rowCount = data.length;
        const colCount = data[0]?.length ?? 0;
        if (theme.rowHeader && rowIdx === 0)
            return theme.color;
        if (theme.rowFooter && rowIdx === rowCount - 1)
            return theme.color;
        if (theme.colHeader && colIdx === 0)
            return subThemeDark;
        if (theme.colFooter && colIdx === colCount - 1)
            return subThemeDark;
        const effectiveRow = theme.rowHeader ? rowIdx - 1 : rowIdx;
        if (effectiveRow >= 0 && effectiveRow % 2 === 0)
            return subThemeLight;
        return undefined;
    };
    const getHeaderTextColor = (rowIdx) => {
        if (!theme)
            return undefined;
        const rowCount = data.length;
        if (theme.rowHeader && rowIdx === 0)
            return '#fff';
        if (theme.rowFooter && rowIdx === rowCount - 1)
            return '#fff';
        return undefined;
    };
    return (jsxRuntime.jsxs("table", { className: "slide-renderer-prose", style: {
            width: '100%',
            borderCollapse: 'collapse',
            tableLayout: 'fixed',
        }, children: [jsxRuntime.jsx("colgroup", { children: colWidths.map((w, i) => (jsxRuntime.jsx("col", { style: { width: `${w * width}px` } }, i))) }), jsxRuntime.jsx("tbody", { children: data.map((row, rowIdx) => (jsxRuntime.jsx("tr", { style: { height: `${rowHeights?.[rowIdx] ?? cellMinHeight}px` }, children: row.map((cell, colIdx) => {
                        // parser side (transformParsedToSlides) 已经把 hMerge/vMerge
                        // continuation 单元格剔除了，data[r] 只剩 top-left cells；浏览器
                        // 的 HTML table layout 通过 td.colSpan/rowSpan 自动算正确位置，
                        // 不需要再手动算 hiddenCells（旧实现用 data-index 比对 grid-coord
                        // key，混了两种坐标系，把 colspan 跨过的 grid-coord 等于另一格
                        // 的 data-index 时会误隐藏，slide 26 表头 "权重"/"好" 就是中招）。
                        const bgColor = getCellBg(rowIdx, colIdx, cell.style?.backcolor);
                        const headerColor = getHeaderTextColor(rowIdx);
                        const textStyle = getTextStyle(cell.style);
                        if (headerColor && !cell.style?.color) {
                            textStyle.color = headerColor;
                        }
                        // 单元格自带逐边描边时按边渲染（未定义的边不画）；否则回退到
                        // 表级 outline 套四边的旧行为，保留真·网格表格的表现。
                        const cellBorders = cell.borders;
                        const borderCss = cellBorders &&
                            (cellBorders.top || cellBorders.bottom || cellBorders.left || cellBorders.right)
                            ? {
                                borderTop: cellBorderCss(cellBorders.top) ?? 'none',
                                borderBottom: cellBorderCss(cellBorders.bottom) ?? 'none',
                                borderLeft: cellBorderCss(cellBorders.left) ?? 'none',
                                borderRight: cellBorderCss(cellBorders.right) ?? 'none',
                            }
                            : { border: borderStyle };
                        return (jsxRuntime.jsx("td", { colSpan: cell.colspan > 1 ? cell.colspan : undefined, rowSpan: cell.rowspan > 1 ? cell.rowspan : undefined, style: {
                                ...borderCss,
                                backgroundColor: bgColor,
                                ...textStyle,
                            }, children: jsxRuntime.jsx("div", { className: "slide-renderer-cell-text", style: {
                                    minHeight: `${(rowHeights?.[rowIdx] ?? cellMinHeight) - 4}px`,
                                    padding: cell.padding,
                                    display: 'flex',
                                    flexDirection: 'column',
                                    lineHeight: 1,
                                    justifyContent: cell.vAlign === 'top'
                                        ? 'flex-start'
                                        : cell.vAlign === 'bottom'
                                            ? 'flex-end'
                                            : cell.vAlign === 'middle'
                                                ? 'center'
                                                : undefined,
                                }, 
                                // cell.text is already final HTML (transformParsedToSlides
                                // escapes text + converts \n/spaces and keeps <p> positioning
                                // styles). Do NOT run formatText here — its space→&nbsp;
                                // replacement corrupts style attributes like
                                // `margin-left: calc(42px + 0.25em)` → the title indent is
                                // lost and collides with the cell's left icon (slide 5).
                                dangerouslySetInnerHTML: { __html: cell.text } }) }, cell.id));
                    }) }, rowIdx))) })] }));
}

function BaseTableElement({ elementInfo, target }) {
    return (jsxRuntime.jsx("div", { className: "base-element-table", style: {
            position: 'absolute',
            top: `${elementInfo.top}px`,
            left: `${elementInfo.left}px`,
            width: `${elementInfo.width}px`,
            height: `${elementInfo.height}px`,
            pointerEvents: target === 'thumbnail' ? 'none' : undefined,
        }, children: jsxRuntime.jsx("div", { className: "rotate-wrapper", style: {
                width: '100%',
                height: '100%',
                transform: `rotate(${elementInfo.rotate}deg)`,
            }, children: jsxRuntime.jsx("div", { className: "element-content", style: { width: '100%', height: '100%' }, children: jsxRuntime.jsx(StaticTable, { elementInfo: elementInfo }) }) }) }));
}

function BaseVideoElement({ elementInfo, renderVideo }) {
    return (jsxRuntime.jsx("div", { className: "element-content", "data-video-element": true, style: {
            position: 'absolute',
            top: `${elementInfo.top}px`,
            left: `${elementInfo.left}px`,
            width: `${elementInfo.width}px`,
            height: `${elementInfo.height}px`,
        }, onClick: (e) => e.stopPropagation(), onPointerDown: (e) => e.stopPropagation(), children: jsxRuntime.jsx("div", { style: {
                width: '100%',
                height: '100%',
                transform: `rotate(${elementInfo.rotate}deg)`,
            }, children: renderVideo ? (renderVideo(elementInfo)) : elementInfo.src || elementInfo.poster ? (
            // Render <video> when we have either a playable src OR just a
            // poster/preview frame. A PPTX「视频」often has no decodable src in
            // this pipeline but does carry a preview image; rendering
            // <video poster> still shows that frame on the live canvas (instead
            // of falling through to the gray play-icon placeholder — slide 34).
            // Snapshot capture of the poster frame is handled in slideToPng
            // (html2canvas can't draw <video> directly).
            jsxRuntime.jsx("video", { style: { width: '100%', height: '100%', objectFit: 'contain' }, ...(elementInfo.src ? { src: elementInfo.src } : {}), poster: elementInfo.poster, preload: "metadata", controls: !!elementInfo.src })) : (jsxRuntime.jsx("div", { style: {
                    width: '100%',
                    height: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    backgroundColor: 'rgba(0, 0, 0, 0.1)',
                    borderRadius: '4px',
                }, children: jsxRuntime.jsx("svg", { style: { width: '48px', height: '48px', color: '#9ca3af' }, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.5, strokeLinecap: "round", strokeLinejoin: "round", children: jsxRuntime.jsx("polygon", { points: "5 3 19 12 5 21 5 3" }) }) })) }) }));
}

// ==================== Shiki Singleton ====================
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let highlighterPromise = null;
function getHighlighter() {
    if (!highlighterPromise) {
        highlighterPromise = import('shiki').then(({ createHighlighter }) => createHighlighter({
            themes: ['github-light'],
            langs: [
                'python',
                'javascript',
                'typescript',
                'json',
                'go',
                'rust',
                'java',
                'c',
                'cpp',
                'html',
                'css',
                'bash',
                'sql',
                'yaml',
                'markdown',
                'jsx',
                'tsx',
            ],
        }));
    }
    return highlighterPromise;
}
// ==================== Helpers ====================
function parseShikiLines(html) {
    const codeMatch = html.match(/<code>([\s\S]*?)<\/code>/);
    if (!codeMatch)
        return [];
    const parts = codeMatch[1].split('<span class="line">');
    const lines = [];
    for (const part of parts) {
        if (!part)
            continue;
        const endIdx = part.lastIndexOf('</span>');
        if (endIdx !== -1) {
            lines.push(part.substring(0, endIdx));
        }
    }
    return lines;
}
// ==================== Typing Easing ====================
const STUTTER_COUNT = 5;
const STUTTER_AMOUNT = 0.04;
const LINE_GAP_MS = 120;
const TAB_SIZE = 4;
function visualLength(s) {
    let len = 0;
    for (const ch of s) {
        len += ch === '\t' ? TAB_SIZE : 1;
    }
    return len;
}
function getTypingCharCount(content) {
    const trimmed = content.replace(/^[\t ]+/, '');
    return trimmed.length;
}
function computeRevealSteps(content) {
    const total = visualLength(content);
    if (total === 0)
        return [1];
    const trimmed = content.replace(/^[\t ]+/, '');
    const indentPart = content.slice(0, content.length - trimmed.length);
    let cumVisual = 0;
    for (const ch of indentPart) {
        cumVisual += ch === '\t' ? TAB_SIZE : 1;
    }
    const steps = [cumVisual / total];
    for (const ch of trimmed) {
        cumVisual += ch === '\t' ? TAB_SIZE : 1;
        steps.push(cumVisual / total);
    }
    return steps;
}
function humanTypingEase(t) {
    const eased = 0.5 - 0.5 * Math.cos(Math.PI * t);
    const stutter = Math.sin(t * Math.PI * STUTTER_COUNT) * STUTTER_AMOUNT * 4 * t * (1 - t);
    return Math.min(Math.max(eased + stutter, 0), 1);
}
// ==================== TypingReveal ====================
function TypingReveal({ html, durationMs, revealSteps, onComplete, }) {
    const typingUnitCount = revealSteps.length - 1;
    const [revealPct, setRevealPct] = react.useState(revealSteps[0]);
    const rafRef = react.useRef(0);
    const startRef = react.useRef(0);
    react.useEffect(() => {
        if (typingUnitCount <= 0) {
            const t = setTimeout(() => {
                setRevealPct(1);
                onComplete();
            }, 0);
            return () => clearTimeout(t);
        }
        startRef.current = performance.now();
        const tick = (now) => {
            const elapsed = now - startRef.current;
            const linearT = Math.min(elapsed / durationMs, 1);
            const easedProgress = humanTypingEase(linearT);
            const stepIdx = Math.min(Math.floor(easedProgress * (typingUnitCount + 1)), typingUnitCount);
            setRevealPct(revealSteps[stepIdx]);
            if (linearT < 1) {
                rafRef.current = requestAnimationFrame(tick);
            }
            else {
                setRevealPct(1);
                onComplete();
            }
        };
        rafRef.current = requestAnimationFrame(tick);
        return () => cancelAnimationFrame(rafRef.current);
    }, [durationMs, typingUnitCount, revealSteps, onComplete]);
    return (jsxRuntime.jsxs("span", { style: { position: 'relative', display: 'inline-block' }, children: [jsxRuntime.jsx("span", { style: {
                    clipPath: `inset(0 ${(1 - revealPct) * 100}% 0 0)`,
                }, dangerouslySetInnerHTML: { __html: html } }), revealPct < 1 && (jsxRuntime.jsx("span", { style: {
                    position: 'absolute',
                    top: 0,
                    width: '2px',
                    backgroundColor: '#1f2937',
                    left: `${revealPct * 100}%`,
                    height: '1.1em',
                    animation: 'slide-renderer-code-cursor-blink 0.6s step-end infinite',
                } }))] }));
}
// ==================== CodeLineRow ====================
function getTypingDuration(content) {
    return Math.max(getTypingCharCount(content) * 40, 250);
}
const REPLACE_SELECT_MS = 350;
function CodeLineRow({ line, lineNumber, highlightedHtml, showLineNumbers, animState, animate, typingDelay, }) {
    const isNewLine = animate && !!animState && animState.type !== 'replaced';
    const isReplace = animate && animState?.type === 'replaced';
    const [mounted, setMounted] = react.useState(!isNewLine || typingDelay === 0);
    react.useEffect(() => {
        if (isNewLine && typingDelay > 0) {
            const timer = setTimeout(() => setMounted(true), typingDelay);
            return () => clearTimeout(timer);
        }
    }, [isNewLine, typingDelay]);
    const [typing, setTyping] = react.useState(isNewLine && typingDelay === 0);
    react.useEffect(() => {
        if (mounted && isNewLine) {
            const t = setTimeout(() => setTyping(true), 0);
            return () => clearTimeout(t);
        }
    }, [mounted, isNewLine]);
    const handleTypingComplete = react.useCallback(() => {
        setTyping(false);
    }, []);
    const prevHtmlRef = react.useRef(highlightedHtml);
    const [replacePhase, setReplacePhase] = react.useState('idle');
    const [oldHtml, setOldHtml] = react.useState(null);
    react.useEffect(() => {
        if (isReplace && prevHtmlRef.current !== highlightedHtml) {
            setOldHtml(prevHtmlRef.current);
            setReplacePhase('select');
            const timer = setTimeout(() => {
                setReplacePhase('type');
                setTyping(true);
                setOldHtml(null);
                prevHtmlRef.current = highlightedHtml;
            }, REPLACE_SELECT_MS);
            return () => clearTimeout(timer);
        }
        prevHtmlRef.current = highlightedHtml;
    }, [isReplace, highlightedHtml]);
    const [highlight, setHighlight] = react.useState(() => {
        if (!animState)
            return null;
        if (animState.type === 'inserted')
            return 'rgba(34, 197, 94, 0.12)';
        return null;
    });
    react.useEffect(() => {
        if (animState?.type === 'inserted') {
            const t = setTimeout(() => setHighlight('rgba(34, 197, 94, 0.12)'), 0);
            return () => clearTimeout(t);
        }
    }, [animState]);
    const [highlightFading, setHighlightFading] = react.useState(false);
    react.useEffect(() => {
        if (!highlight || highlightFading || typing)
            return;
        const fadeTimer = setTimeout(() => setHighlightFading(true), 0);
        const clearTimer = setTimeout(() => {
            setHighlight(null);
            setHighlightFading(false);
        }, 2000);
        return () => {
            clearTimeout(fadeTimer);
            clearTimeout(clearTimer);
        };
    }, [highlight, typing, highlightFading]);
    const typingDuration = getTypingDuration(line.content);
    const revealSteps = react.useMemo(() => computeRevealSteps(line.content), [line.content]);
    if (!mounted)
        return null;
    let bgColor = highlight || 'transparent';
    if (replacePhase === 'select')
        bgColor = 'rgba(59, 130, 246, 0.18)';
    let contentNode;
    if (replacePhase === 'select' && oldHtml) {
        contentNode = jsxRuntime.jsx("span", { dangerouslySetInnerHTML: { __html: oldHtml } });
    }
    else if (typing) {
        contentNode = (jsxRuntime.jsx(TypingReveal, { html: highlightedHtml, durationMs: typingDuration, revealSteps: revealSteps, onComplete: handleTypingComplete }));
    }
    else {
        contentNode = jsxRuntime.jsx("span", { dangerouslySetInnerHTML: { __html: highlightedHtml } });
    }
    return (jsxRuntime.jsxs(react$1.motion.div, { initial: isNewLine ? { opacity: 0, height: 0 } : false, animate: {
            opacity: 1,
            height: 'auto',
            backgroundColor: bgColor,
            transition: {
                duration: 0.3,
                ease: [0.16, 1, 0.3, 1],
                backgroundColor: { duration: 0.4 },
            },
        }, exit: {
            backgroundColor: 'rgba(59, 130, 246, 0.18)',
            height: 0,
            opacity: 0,
            transition: {
                backgroundColor: { duration: 0 },
                height: { duration: 0, delay: 0.3 },
                opacity: { duration: 0, delay: 0.3 },
            },
        }, style: {
            display: 'flex',
            lineHeight: 1.6,
            fontSize: 'inherit',
            overflow: 'hidden',
        }, children: [showLineNumbers && (jsxRuntime.jsx("span", { style: {
                    flexShrink: 0,
                    textAlign: 'right',
                    paddingRight: '16px',
                    paddingLeft: '8px',
                    width: '3.5em',
                    color: '#9ca3af',
                    userSelect: 'none',
                }, children: lineNumber })), jsxRuntime.jsx("span", { style: { flex: 1, paddingRight: '16px', whiteSpace: 'pre', tabSize: 4 }, children: contentNode })] }));
}
// ==================== BaseCodeElement ====================
function BaseCodeElement({ elementInfo, animate }) {
    const { language, lines, fileName, showLineNumbers = true, fontSize = 14 } = elementInfo;
    const wrapperRef = react.useRef(null);
    const codeBodyRef = react.useRef(null);
    react.useEffect(() => {
        const el = codeBodyRef.current;
        if (!el)
            return;
        let dragging = false;
        let startX = 0;
        let startY = 0;
        let startScrollLeft = 0;
        let startScrollTop = 0;
        let activePointer = null;
        const endDrag = () => {
            if (activePointer !== null && el.hasPointerCapture(activePointer)) {
                el.releasePointerCapture(activePointer);
            }
            dragging = false;
            activePointer = null;
            el.style.cursor = 'grab';
        };
        const onPointerDown = (e) => {
            if (e.button !== 0)
                return;
            dragging = true;
            activePointer = e.pointerId;
            startX = e.clientX;
            startY = e.clientY;
            startScrollLeft = el.scrollLeft;
            startScrollTop = el.scrollTop;
            el.setPointerCapture(e.pointerId);
            el.style.cursor = 'grabbing';
        };
        const onPointerMove = (e) => {
            if (!dragging || e.pointerId !== activePointer)
                return;
            el.scrollLeft = startScrollLeft - (e.clientX - startX);
            el.scrollTop = startScrollTop - (e.clientY - startY);
        };
        const onPointerEnd = (e) => {
            if (e.pointerId !== activePointer)
                return;
            endDrag();
        };
        const onLostCapture = () => {
            endDrag();
        };
        const onWheel = (e) => {
            e.stopPropagation();
        };
        el.style.cursor = 'grab';
        el.addEventListener('pointerdown', onPointerDown);
        el.addEventListener('pointermove', onPointerMove);
        el.addEventListener('pointerup', onPointerEnd);
        el.addEventListener('pointercancel', onPointerEnd);
        el.addEventListener('lostpointercapture', onLostCapture);
        el.addEventListener('wheel', onWheel, { passive: true });
        return () => {
            endDrag();
            el.removeEventListener('pointerdown', onPointerDown);
            el.removeEventListener('pointermove', onPointerMove);
            el.removeEventListener('pointerup', onPointerEnd);
            el.removeEventListener('pointercancel', onPointerEnd);
            el.removeEventListener('lostpointercapture', onLostCapture);
            el.removeEventListener('wheel', onWheel);
        };
    }, []);
    react.useEffect(() => {
        const el = wrapperRef.current;
        if (!el)
            return;
        const stopWheelOutsideBody = (e) => {
            const body = codeBodyRef.current;
            if (body && body.contains(e.target))
                return;
            e.stopPropagation();
        };
        el.addEventListener('wheel', stopWheelOutsideBody);
        return () => el.removeEventListener('wheel', stopWheelOutsideBody);
    }, []);
    const stopPointer = react.useCallback((e) => {
        e.stopPropagation();
    }, []);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [highlighter, setHighlighter] = react.useState(null);
    const prevLinesRef = react.useRef([]);
    const isFirstRenderRef = react.useRef(true);
    const [animStates, setAnimStates] = react.useState(() => new Map());
    react.useEffect(() => {
        const states = new Map();
        if (animate) {
            if (isFirstRenderRef.current) {
                isFirstRenderRef.current = false;
                lines.forEach((line, i) => {
                    states.set(line.id, { type: 'typing', timestamp: i * 80 });
                });
            }
            else {
                const prevIds = new Set(prevLinesRef.current.map((l) => l.id));
                for (const line of lines) {
                    if (!prevIds.has(line.id)) {
                        states.set(line.id, { type: 'inserted', timestamp: 0 });
                    }
                }
                for (const line of lines) {
                    const prev = prevLinesRef.current.find((p) => p.id === line.id);
                    if (prev && prev.content !== line.content) {
                        states.set(line.id, { type: 'replaced', timestamp: 0 });
                    }
                }
            }
            prevLinesRef.current = lines;
        }
        const t = setTimeout(() => setAnimStates(states), 0);
        return () => clearTimeout(t);
    }, [lines, animate]);
    react.useEffect(() => {
        getHighlighter().then(setHighlighter);
    }, []);
    const highlightedLines = react.useMemo(() => {
        if (!highlighter)
            return null;
        const code = lines.map((l) => l.content).join('\n');
        let lang = language;
        try {
            highlighter.getLoadedLanguages();
        }
        catch {
            lang = 'text';
        }
        try {
            const html = highlighter.codeToHtml(code, { lang, theme: 'github-light' });
            const parsed = parseShikiLines(html);
            return lines.map((line, i) => ({
                id: line.id,
                html: parsed[i] || escapeHtml(line.content),
            }));
        }
        catch {
            return lines.map((line) => ({
                id: line.id,
                html: escapeHtml(line.content),
            }));
        }
    }, [highlighter, lines, language]);
    const fallbackLines = react.useMemo(() => {
        return lines.map((line) => ({
            id: line.id,
            html: escapeHtml(line.content),
        }));
    }, [lines]);
    const lineHtmlMap = highlightedLines || fallbackLines;
    const typingDelays = react.useMemo(() => {
        const delays = new Map();
        let cumulative = 0;
        for (const line of lines) {
            if (animStates.has(line.id)) {
                delays.set(line.id, cumulative);
                cumulative += getTypingDuration(line.content) + LINE_GAP_MS;
            }
        }
        return delays;
    }, [lines, animStates]);
    const langDisplay = LANG_DISPLAY_NAMES[language] || language;
    return (jsxRuntime.jsx("div", { ref: wrapperRef, className: "base-element-code", style: {
            position: 'absolute',
            top: `${elementInfo.top}px`,
            left: `${elementInfo.left}px`,
            width: `${elementInfo.width}px`,
            height: `${elementInfo.height}px`,
        }, onPointerDown: stopPointer, onClick: stopPointer, children: jsxRuntime.jsx("div", { className: "rotate-wrapper", style: {
                width: '100%',
                height: '100%',
                transform: `rotate(${elementInfo.rotate}deg)`,
            }, children: jsxRuntime.jsxs("div", { className: "element-content", style: {
                    width: '100%',
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    overflow: 'hidden',
                    borderRadius: '8px',
                    border: '1px solid #d1d5db',
                    background: '#fafbfc',
                    boxShadow: '0 2px 6px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.05)',
                    fontFamily: '"JetBrains Mono", "Fira Code", "SF Mono", "Cascadia Code", ui-monospace, SFMono-Regular, "Liberation Mono", Menlo, Monaco, Consolas, monospace',
                    fontSize: `${fontSize}px`,
                }, children: [jsxRuntime.jsxs("div", { style: {
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            flexShrink: 0,
                            paddingLeft: '12px',
                            paddingRight: '12px',
                            height: '32px',
                            background: '#f8f9fa',
                            borderBottom: '1px solid #e5e7eb',
                        }, children: [jsxRuntime.jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: '8px' }, children: [jsxRuntime.jsxs("div", { style: { display: 'flex', gap: '6px' }, children: [jsxRuntime.jsx("div", { style: {
                                                    width: '10px',
                                                    height: '10px',
                                                    borderRadius: '9999px',
                                                    background: '#ff5f57',
                                                } }), jsxRuntime.jsx("div", { style: {
                                                    width: '10px',
                                                    height: '10px',
                                                    borderRadius: '9999px',
                                                    background: '#febc2e',
                                                } }), jsxRuntime.jsx("div", { style: {
                                                    width: '10px',
                                                    height: '10px',
                                                    borderRadius: '9999px',
                                                    background: '#28c840',
                                                } })] }), fileName && (jsxRuntime.jsx("span", { style: {
                                            marginLeft: '8px',
                                            overflow: 'hidden',
                                            textOverflow: 'ellipsis',
                                            whiteSpace: 'nowrap',
                                            color: '#6b7280',
                                            fontSize: '11px',
                                            letterSpacing: '0.01em',
                                        }, children: fileName }))] }), jsxRuntime.jsx("span", { style: {
                                    color: '#9ca3af',
                                    fontSize: '10px',
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.05em',
                                    fontWeight: 500,
                                }, children: langDisplay })] }), jsxRuntime.jsx("div", { ref: codeBodyRef, style: {
                            flex: 1,
                            overflow: 'auto',
                            paddingTop: '8px',
                            paddingBottom: '8px',
                            background: '#fafbfc',
                            color: '#24292e',
                            userSelect: 'none',
                            WebkitUserSelect: 'none',
                            touchAction: 'none',
                        }, children: jsxRuntime.jsx("div", { style: { minWidth: 'max-content' }, children: jsxRuntime.jsx(react$1.AnimatePresence, { initial: false, mode: "popLayout", children: lineHtmlMap.map((lineData, index) => {
                                    const line = lines[index];
                                    if (!line)
                                        return null;
                                    return (jsxRuntime.jsx(CodeLineRow, { line: line, lineNumber: index + 1, highlightedHtml: lineData.html, showLineNumbers: showLineNumbers, animState: animStates.get(line.id), animate: !!animate, typingDelay: typingDelays.get(line.id) ?? 0 }, line.id));
                                }) }) }) })] }) }) }));
}
// ==================== Utilities ====================
function escapeHtml(text) {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}
const LANG_DISPLAY_NAMES = {
    python: 'Python',
    javascript: 'JavaScript',
    typescript: 'TypeScript',
    json: 'JSON',
    go: 'Go',
    rust: 'Rust',
    java: 'Java',
    c: 'C',
    cpp: 'C++',
    html: 'HTML',
    css: 'CSS',
    bash: 'Bash',
    sql: 'SQL',
    yaml: 'YAML',
    markdown: 'Markdown',
    jsx: 'JSX',
    tsx: 'TSX',
};

exports.BaseChartElement = BaseChartElement;
exports.BaseCodeElement = BaseCodeElement;
exports.BaseImageElement = BaseImageElement;
exports.BaseLatexElement = BaseLatexElement;
exports.BaseLineElement = BaseLineElement;
exports.BaseShapeElement = BaseShapeElement;
exports.BaseTableElement = BaseTableElement;
exports.BaseTextElement = BaseTextElement;
exports.BaseVideoElement = BaseVideoElement;
exports.ElementOutline = ElementOutline;
exports.useElementFill = useElementFill;
exports.useElementFlip = useElementFlip;
exports.useElementOutline = useElementOutline;
exports.useElementShadow = useElementShadow;
//# sourceMappingURL=BaseCodeElement-C4RFPT0H.cjs.map
