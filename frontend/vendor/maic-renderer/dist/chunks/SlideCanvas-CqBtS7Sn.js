import { jsxs, jsx } from 'react/jsx-runtime';
import { useMemo, useState, useCallback, useEffect, useRef, useLayoutEffect, createContext, useContext } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { ElementTypes } from '@maic/dsl';
import { g as BaseTextElement, e as BaseShapeElement, b as BaseImageElement, d as BaseLineElement, B as BaseChartElement, c as BaseLatexElement, f as BaseTableElement, h as BaseVideoElement, a as BaseCodeElement } from './BaseCodeElement-Bh-Bfdz6.js';

function getElementPercentageGeometry(element, viewportSize = 1000) {
    if (!('left' in element) ||
        !('top' in element) ||
        !('width' in element) ||
        !('height' in element)) {
        return null;
    }
    const { left, top, width, height } = element;
    const x = (left / viewportSize) * 100;
    const y = (top / (viewportSize * 0.5625)) * 100;
    const w = (width / viewportSize) * 100;
    const h = (height / (viewportSize * 0.5625)) * 100;
    const centerX = x + w / 2;
    const centerY = y + h / 2;
    return { x, y, w, h, centerX, centerY };
}
function findElementGeometry(elements, elementId, viewportSize = 1000) {
    const element = elements.find((el) => el.id === elementId);
    if (!element)
        return null;
    return getElementPercentageGeometry(element, viewportSize);
}
function findNearestCorner(geometry) {
    const { centerX, centerY } = geometry;
    const corners = [
        { x: 0, y: 0 },
        { x: 100, y: 0 },
        { x: 0, y: 100 },
        { x: 100, y: 100 },
    ];
    let minDistance = Infinity;
    let nearestCorner = corners[0];
    for (const corner of corners) {
        const distance = Math.sqrt(Math.pow(corner.x - centerX, 2) + Math.pow(corner.y - centerY, 2));
        if (distance < minDistance) {
            minDistance = distance;
            nearestCorner = corner;
        }
    }
    return nearestCorner;
}

function useSlideBackgroundStyle(background) {
    const backgroundStyle = useMemo(() => {
        if (!background)
            return { backgroundColor: '#fff' };
        const { type, color, image, gradient } = background;
        if (type === 'solid')
            return { backgroundColor: color };
        if (type === 'image' && image) {
            const { src, size } = image;
            if (!src)
                return { backgroundColor: '#fff' };
            if (size === 'repeat') {
                return {
                    backgroundImage: `url(${src})`,
                    backgroundRepeat: 'repeat',
                    backgroundSize: 'contain',
                };
            }
            return {
                backgroundImage: `url(${src})`,
                backgroundRepeat: 'no-repeat',
                backgroundSize: size || 'cover',
            };
        }
        if (type === 'gradient' && gradient) {
            const { type: gradientType, colors, rotate } = gradient;
            const list = colors.map((item) => `${item.color} ${item.pos}%`);
            if (gradientType === 'radial') {
                return { backgroundImage: `radial-gradient(${list.join(',')})` };
            }
            return {
                backgroundImage: `linear-gradient(${rotate}deg, ${list.join(',')})`,
            };
        }
        return { backgroundColor: '#fff' };
    }, [background]);
    return { backgroundStyle };
}

/**
 * Compute the viewport rect and fit-scale needed to center a slide of size
 * `viewportSize × viewportSize*viewportRatio` inside `canvasRef`.
 *
 * Pure: no store access. Re-runs on container resize via ResizeObserver.
 */
function useViewportSize(canvasRef, options = {}) {
    const { viewportSize = 1000, viewportRatio = 0.5625, canvasPercentage = 100 } = options;
    const [viewportLeft, setViewportLeft] = useState(0);
    const [viewportTop, setViewportTop] = useState(0);
    const [fitScale, setFitScale] = useState(1);
    const computeFit = useCallback(() => {
        if (!canvasRef.current)
            return;
        const canvasWidth = canvasRef.current.clientWidth;
        const canvasHeight = canvasRef.current.clientHeight;
        if (canvasHeight / canvasWidth > viewportRatio) {
            const viewportActualWidth = canvasWidth * (canvasPercentage / 100);
            setFitScale(viewportActualWidth / viewportSize);
            setViewportLeft((canvasWidth - viewportActualWidth) / 2);
            setViewportTop((canvasHeight - viewportActualWidth * viewportRatio) / 2);
        }
        else {
            const viewportActualHeight = canvasHeight * (canvasPercentage / 100);
            setFitScale(viewportActualHeight / (viewportSize * viewportRatio));
            setViewportLeft((canvasWidth - viewportActualHeight / viewportRatio) / 2);
            setViewportTop((canvasHeight - viewportActualHeight) / 2);
        }
    }, [canvasRef, canvasPercentage, viewportRatio, viewportSize]);
    useEffect(() => {
        computeFit();
    }, [computeFit]);
    useEffect(() => {
        const el = canvasRef.current;
        if (!el)
            return;
        const resizeObserver = new ResizeObserver(computeFit);
        resizeObserver.observe(el);
        return () => resizeObserver.unobserve(el);
    }, [canvasRef, computeFit]);
    const viewportStyles = useMemo(() => ({
        width: viewportSize,
        height: viewportSize * viewportRatio,
        left: viewportLeft,
        top: viewportTop,
    }), [viewportSize, viewportRatio, viewportLeft, viewportTop]);
    return { viewportStyles, fitScale };
}

const DEFAULT_THEME = {
    fontColor: '#333333',
    fontName: 'Microsoft YaHei',
};
function SlideElement({ elementInfo, elementIndex, theme, animate, renderImage, renderVideo, onElementClick, idPrefix = 'slide-element-', }) {
    const Component = useMemo(() => {
        switch (elementInfo.type) {
            case ElementTypes.IMAGE:
                return 'image';
            case ElementTypes.TEXT:
                return 'text';
            case ElementTypes.SHAPE:
                return 'shape';
            case ElementTypes.LINE:
                return 'line';
            case ElementTypes.CHART:
                return 'chart';
            case ElementTypes.LATEX:
                return 'latex';
            case ElementTypes.TABLE:
                return 'table';
            case ElementTypes.VIDEO:
                return 'video';
            case ElementTypes.CODE:
                return 'code';
            default:
                return null;
        }
    }, [elementInfo.type]);
    if (!Component)
        return null;
    const fontColor = theme?.fontColor ?? DEFAULT_THEME.fontColor;
    const fontName = theme?.fontName ?? DEFAULT_THEME.fontName;
    return (jsxs("div", { className: "slide-element", id: `${idPrefix}${elementInfo.id}`, style: { zIndex: elementIndex, color: fontColor, fontFamily: fontName }, onClick: onElementClick ? (e) => onElementClick(elementInfo, e) : undefined, children: [Component === 'text' && elementInfo.type === 'text' && (jsx(BaseTextElement, { elementInfo: elementInfo })), Component === 'shape' && elementInfo.type === 'shape' && (jsx(BaseShapeElement, { elementInfo: elementInfo })), Component === 'image' && elementInfo.type === 'image' && (jsx(BaseImageElement, { elementInfo: elementInfo, renderImage: renderImage })), Component === 'line' && elementInfo.type === 'line' && (jsx(BaseLineElement, { elementInfo: elementInfo, animate: animate })), Component === 'chart' && elementInfo.type === 'chart' && (jsx(BaseChartElement, { elementInfo: elementInfo })), Component === 'latex' && elementInfo.type === 'latex' && (jsx(BaseLatexElement, { elementInfo: elementInfo })), Component === 'table' && elementInfo.type === 'table' && (jsx(BaseTableElement, { elementInfo: elementInfo })), Component === 'video' && elementInfo.type === 'video' && (jsx(BaseVideoElement, { elementInfo: elementInfo, renderVideo: renderVideo })), Component === 'code' && elementInfo.type === 'code' && (jsx(BaseCodeElement, { elementInfo: elementInfo, animate: animate }))] }));
}

function HighlightOverlay({ element, options }) {
    if (element.type === 'line')
        return null;
    const color = options?.color ?? '#ff6b6b';
    const opacity = options?.opacity ?? 0.3;
    const borderWidth = options?.borderWidth ?? 3;
    const animated = options?.animated ?? true;
    const height = 'height' in element ? element.height : 0;
    const rotate = 'rotate' in element ? element.rotate : 0;
    return (jsxs("div", { className: "highlight-overlay", style: {
            position: 'absolute',
            pointerEvents: 'none',
            left: `${element.left}px`,
            top: `${element.top}px`,
            width: `${element.width}px`,
            height: `${height}px`,
            transform: `rotate(${rotate || 0}deg)`,
            transformOrigin: 'center',
            zIndex: 999,
            transition: 'all 0.3s ease-in-out',
        }, children: [jsx("div", { className: animated ? 'slide-renderer-pulse' : undefined, style: {
                    position: 'absolute',
                    inset: 0,
                    borderRadius: '4px',
                    border: `${borderWidth}px solid ${color}`,
                    boxShadow: `0 0 ${borderWidth * 3}px ${color}, inset 0 0 ${borderWidth * 2}px rgba(255,255,255,${opacity * 0.5})`,
                    backgroundColor: `${color}${Math.round(opacity * 255)
                        .toString(16)
                        .padStart(2, '0')}`,
                } }), animated && (jsx("div", { className: "slide-renderer-ping", style: {
                    position: 'absolute',
                    inset: 0,
                    borderRadius: '4px',
                    border: `${borderWidth}px solid ${color}`,
                    opacity: 0.5,
                    animationDuration: '2s',
                } }))] }));
}

function SpotlightOverlay({ options, elementIdPrefix = 'slide-element-', }) {
    const containerRef = useRef(null);
    const [rect, setRect] = useState(null);
    const spotlightElementId = options?.elementId;
    const measure = useCallback(() => {
        if (!spotlightElementId || !containerRef.current) {
            setRect(null);
            return;
        }
        const domElement = document.getElementById(`${elementIdPrefix}${spotlightElementId}`);
        if (!domElement) {
            setRect(null);
            return;
        }
        const contentEl = domElement.querySelector('.element-content');
        const targetEl = contentEl ?? domElement;
        const containerRect = containerRef.current.getBoundingClientRect();
        const targetRect = targetEl.getBoundingClientRect();
        if (containerRect.width === 0 || containerRect.height === 0) {
            setRect(null);
            return;
        }
        setRect({
            x: ((targetRect.left - containerRect.left) / containerRect.width) * 100,
            y: ((targetRect.top - containerRect.top) / containerRect.height) * 100,
            w: (targetRect.width / containerRect.width) * 100,
            h: (targetRect.height / containerRect.height) * 100,
        });
    }, [spotlightElementId, elementIdPrefix]);
    useLayoutEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect -- DOM measurement requires effect
        measure();
    }, [measure]);
    const active = !!spotlightElementId && !!rect;
    return (jsx("div", { ref: containerRef, style: {
            position: 'absolute',
            inset: 0,
            zIndex: 100,
            pointerEvents: 'none',
            overflow: 'hidden',
        }, children: jsx(AnimatePresence, { mode: "wait", children: active && rect && (jsx(motion.div, { initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 }, style: { position: 'absolute', inset: 0 }, children: jsxs("svg", { width: "100%", height: "100%", viewBox: "0 0 100 100", preserveAspectRatio: "none", style: { position: 'absolute', inset: 0 }, children: [jsx("defs", { children: jsxs("mask", { id: `mask-${spotlightElementId}`, children: [jsx("rect", { x: "0", y: "0", width: "100", height: "100", fill: "white" }), jsx(motion.rect, { fill: "black", initial: {
                                            x: rect.x - 8,
                                            y: rect.y - 8,
                                            width: rect.w + 16,
                                            height: rect.h + 16,
                                            rx: 4,
                                        }, animate: {
                                            x: rect.x - 0.4,
                                            y: rect.y - 0.6,
                                            width: rect.w + 0.8,
                                            height: rect.h + 1.2,
                                            rx: 1,
                                        }, transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] } })] }) }), jsx("rect", { width: "100", height: "100", fill: "rgba(0,0,0,0.7)", mask: `url(#mask-${spotlightElementId})` }), jsx(motion.rect, { initial: {
                                x: rect.x - 4,
                                y: rect.y - 4,
                                width: rect.w + 8,
                                height: rect.h + 8,
                                opacity: 0,
                                rx: 2,
                            }, animate: {
                                x: rect.x - 0.4,
                                y: rect.y - 0.6,
                                width: rect.w + 0.8,
                                height: rect.h + 1.2,
                                opacity: 1,
                                rx: 1,
                            }, fill: "none", stroke: "rgba(255,255,255,0.7)", strokeWidth: "1.2", style: { vectorEffect: 'non-scaling-stroke' }, transition: { duration: 0.5, delay: 0.05, ease: [0.16, 1, 0.3, 1] } })] }) }, `spotlight-${spotlightElementId}`)) }) }));
}

function LaserOverlay({ geometry, color = '#ff3b30', duration: _duration = 3000, }) {
    const { centerX, centerY } = geometry;
    const startPos = {
        x: centerX > 50 ? 105 : -5,
        y: centerY > 50 ? 105 : -5,
    };
    return (jsx(motion.div, { initial: { opacity: 0, left: `${startPos.x}%`, top: `${startPos.y}%` }, animate: { opacity: 1, left: `${centerX}%`, top: `${centerY}%` }, exit: {
            opacity: 0,
            left: `${startPos.x}%`,
            top: `${startPos.y}%`,
            transition: { duration: 0.25, ease: [0.4, 0, 1, 1] },
        }, transition: {
            left: { duration: 0.5, ease: [0.22, 1, 0.36, 1] },
            top: { duration: 0.5, ease: [0.22, 1, 0.36, 1] },
            opacity: { duration: 0.15 },
        }, style: { position: 'absolute', zIndex: 101, pointerEvents: 'none' }, children: jsxs("div", { style: { position: 'relative', transform: 'translate(-50%, -50%)' }, children: [jsx(motion.div, { animate: { scale: [1, 2.8], opacity: [0.6, 0] }, transition: {
                        repeat: Infinity,
                        duration: 1.5,
                        ease: 'easeOut',
                        repeatDelay: 0.3,
                    }, style: {
                        position: 'absolute',
                        inset: 0,
                        borderRadius: '9999px',
                        border: `1.5px solid ${color}`,
                    } }), jsx("div", { style: {
                        width: '10px',
                        height: '10px',
                        borderRadius: '9999px',
                        backgroundColor: color,
                        boxShadow: `0 0 8px 2px ${color}60`,
                    } })] }) }, `laser-${centerX}-${centerY}`));
}

const SlideContext = createContext(null);
function SlideRendererProvider({ children, className, style, ...value }) {
    return (jsx(SlideContext.Provider, { value: value, children: className || style ? (jsx("div", { className: className, style: style, children: children })) : (children) }));
}
/**
 * Read the closest SlideRendererProvider value.
 * Throws if used outside a provider — use `useOptionalSlideContext` for nullable access.
 */
function useSlideContext() {
    const value = useContext(SlideContext);
    if (!value) {
        throw new Error('useSlideContext must be used inside a <SlideRendererProvider>. ' +
            'Pass props directly to <SlideCanvas> if you do not need the provider.');
    }
    return value;
}
/** Nullable variant; returns null when outside a provider. */
function useOptionalSlideContext() {
    return useContext(SlideContext);
}

/**
 * Package-level CSS rules that can't be expressed inline (descendant selectors,
 * keyframes, pseudo-classes). Rendered once via `<style>` at the top of
 * `<SlideCanvas>` so the package stays self-contained without Tailwind.
 *
 * The `.slide-renderer-prose` rules are intentionally minimal "browser-default
 * resets" — they un-do the user-agent stylesheet (1em <p> margin, KaTeX block
 * margin) so the slide JSON is the single source of truth. They do not
 * positively style anything; spacing comes from the data via the
 * `--paragraphSpace` CSS variable, which is unset when undefined in data.
 */
const SLIDE_RENDERER_STYLES = `
.slide-renderer-prose p {
  margin-top: 0;
  margin-bottom: var(--paragraphSpace, 0);
}
.slide-renderer-prose p:last-child {
  margin-bottom: 0;
}
.slide-renderer-prose .katex-display {
  margin: 0 !important;
}
/* Table cell inner container — matches the classroom (Vue) .cell-text design:
   tight base line-height, and a small spacing between adjacent <p> siblings
   so multi-paragraph cells don't collapse into a single visual block. The
   <p> margin reset above sets the baseline to 0; this rule re-adds spacing
   only between adjacent siblings, leaving the first/last paragraph flush. */
.slide-renderer-cell-text p + p {
  margin-top: 0.4em;
}
@keyframes slide-renderer-pulse {
  50% { opacity: 0.5; }
}
@keyframes slide-renderer-ping {
  75%, 100% { transform: scale(2); opacity: 0; }
}
@keyframes slide-renderer-code-cursor-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
.slide-renderer-pulse {
  animation: slide-renderer-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
.slide-renderer-ping {
  animation: slide-renderer-ping 1s cubic-bezier(0, 0, 0.2, 1) infinite;
}
`;

function SlideCanvas(props) {
    const ctx = useOptionalSlideContext();
    const slide = props.slide ?? ctx?.slide;
    if (!slide) {
        throw new Error('<SlideCanvas> requires `slide` either as a prop or via <SlideRendererProvider>.');
    }
    const scale = props.scale ?? ctx?.scale;
    const background = props.background ?? ctx?.background;
    const effects = props.effects ?? ctx?.effects;
    const renderImage = props.renderImage ?? ctx?.renderImage;
    const renderVideo = props.renderVideo ?? ctx?.renderVideo;
    const onElementClick = props.onElementClick ?? ctx?.onElementClick;
    const { className, style } = props;
    const chrome = props.chrome ?? true;
    const canvasRef = useRef(null);
    const elements = slide.elements;
    const { viewportStyles, fitScale } = useViewportSize(canvasRef, {
        viewportSize: slide.viewportSize,
        viewportRatio: slide.viewportRatio,
    });
    const canvasScale = scale ?? fitScale;
    const resolvedBackground = background ?? slide.background;
    const { backgroundStyle } = useSlideBackgroundStyle(resolvedBackground);
    // Plain derivations: when this package is consumed in a React Compiler build
    // these are auto-memoized; otherwise the cost (O(elements) lookups) is trivial.
    const laserGeometry = effects?.laser
        ? findElementGeometry(elements, effects.laser.elementId, slide.viewportSize)
        : null;
    const zoomGeometry = effects?.zoom
        ? findElementGeometry(elements, effects.zoom.elementId, slide.viewportSize)
        : null;
    const highlightElement = effects?.highlight
        ? (elements.find((el) => el.id === effects.highlight.elementId) ?? null)
        : null;
    return (jsxs("div", { ref: canvasRef, className: className, style: {
            position: 'relative',
            width: '100%',
            height: '100%',
            overflow: 'hidden',
            userSelect: 'none',
            ...style,
        }, children: [jsx("style", { dangerouslySetInnerHTML: { __html: SLIDE_RENDERER_STYLES } }), jsxs("div", { style: {
                    position: 'absolute',
                    ...(chrome
                        ? {
                            boxShadow: '0 0 0 1px rgba(0, 0, 0, 0.01), 0 0 12px 0 rgba(0, 0, 0, 0.1)',
                            borderRadius: '0.5rem',
                        }
                        : {}),
                    overflow: 'hidden',
                    transitionProperty: 'transform',
                    transitionDuration: '700ms',
                    width: `${viewportStyles.width * canvasScale}px`,
                    height: `${viewportStyles.height * canvasScale}px`,
                    left: `${viewportStyles.left}px`,
                    top: `${viewportStyles.top}px`,
                    ...(effects?.zoom && zoomGeometry
                        ? {
                            transform: `scale(${effects.zoom.scale})`,
                            transformOrigin: `${zoomGeometry.centerX}% ${zoomGeometry.centerY}%`,
                        }
                        : {}),
                }, children: [jsx("div", { style: {
                            width: '100%',
                            height: '100%',
                            backgroundPosition: 'center',
                            ...(chrome ? { borderRadius: '0.5rem' } : {}),
                            ...backgroundStyle,
                        } }), jsxs("div", { style: {
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            transformOrigin: 'top left',
                            width: `${viewportStyles.width}px`,
                            height: `${viewportStyles.height}px`,
                            transform: `scale(${canvasScale})`,
                        }, children: [elements.map((element, index) => (jsx(SlideElement, { elementInfo: element, elementIndex: index + 1, theme: slide.theme, renderImage: renderImage, renderVideo: renderVideo, onElementClick: onElementClick }, element.id))), highlightElement && (jsx(HighlightOverlay, { element: highlightElement, options: effects?.highlight }))] }), jsx(SpotlightOverlay, { options: effects?.spotlight }), jsx("div", { style: {
                            position: 'absolute',
                            inset: 0,
                            pointerEvents: 'none',
                            padding: '5%',
                        }, children: jsx("div", { style: { position: 'relative', width: '100%', height: '100%' }, children: jsx(AnimatePresence, { children: effects?.laser && laserGeometry && (jsx(LaserOverlay, { geometry: laserGeometry, color: effects.laser.color, duration: effects.laser.duration }, `laser-${effects.laser.elementId}`)) }) }) })] })] }));
}

export { HighlightOverlay as H, LaserOverlay as L, SlideCanvas as S, SlideElement as a, SlideRendererProvider as b, SpotlightOverlay as c, findNearestCorner as d, useSlideBackgroundStyle as e, findElementGeometry as f, getElementPercentageGeometry as g, useSlideContext as h, useViewportSize as i, useOptionalSlideContext as u };
//# sourceMappingURL=SlideCanvas-CqBtS7Sn.js.map
