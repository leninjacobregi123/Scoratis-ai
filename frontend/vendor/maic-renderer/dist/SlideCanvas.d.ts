import { type CSSProperties, type ReactNode } from 'react';
import type { PPTElement, PPTImageElement, PPTVideoElement, Slide, SlideBackground } from '@maic/dsl';
import type { SlideEffects } from './types/effects';
export interface SlideCanvasProps {
    /**
     * Single slide data (PPTist-style). May be omitted when this component is
     * rendered inside a `<SlideRendererProvider>` that supplies it.
     */
    slide?: Slide;
    /**
     * Canvas scale. When omitted, the canvas auto-fits the container using
     * `slide.viewportSize` and `slide.viewportRatio`. Set to a fixed number
     * (e.g. 1) to skip auto-fit and render at slide-native dimensions.
     */
    scale?: number;
    /** Override `slide.background`. */
    background?: SlideBackground;
    /** Optional play-time effects, all default off. */
    effects?: SlideEffects;
    /** Replace default <img> rendering for image elements. */
    renderImage?: (element: PPTImageElement, resolvedSrc: string) => ReactNode;
    /** Replace default <video> rendering for video elements. */
    renderVideo?: (element: PPTVideoElement) => ReactNode;
    /** Click handler invoked on any element. */
    onElementClick?: (element: PPTElement, event: React.MouseEvent) => void;
    /** Class on the outer container. */
    className?: string;
    /** Inline style on the outer container. */
    style?: CSSProperties;
    /**
     * Card-style chrome on the inner slide container (drop shadow + rounded
     * corners). Defaults to `true` for on-screen previews. Snapshot pipelines
     * pass `false` so the captured PNG matches the source PPT's edges exactly
     * — html2canvas would otherwise bake the 1px shadow outline and the
     * 0.5rem corner radius into the output and the comparator reads them as
     * a thin border + rounded corners that the original PPT does not have.
     */
    chrome?: boolean;
}
export declare function SlideCanvas(props: SlideCanvasProps): import("react/jsx-runtime").JSX.Element;
