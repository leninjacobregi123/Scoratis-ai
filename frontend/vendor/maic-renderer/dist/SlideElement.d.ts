import { type ReactNode } from 'react';
import { type PPTElement, type PPTImageElement, type PPTVideoElement, type SlideTheme } from '@maic/dsl';
export interface SlideElementProps {
    elementInfo: PPTElement;
    elementIndex: number;
    theme?: Pick<SlideTheme, 'fontColor' | 'fontName'>;
    animate?: boolean;
    renderImage?: (element: PPTImageElement, resolvedSrc: string) => ReactNode;
    renderVideo?: (element: PPTVideoElement) => ReactNode;
    onElementClick?: (element: PPTElement, event: React.MouseEvent) => void;
    /** Prefix used for the root div id — must match SpotlightOverlay's `elementIdPrefix`. */
    idPrefix?: string;
}
export declare function SlideElement({ elementInfo, elementIndex, theme, animate, renderImage, renderVideo, onElementClick, idPrefix, }: SlideElementProps): import("react/jsx-runtime").JSX.Element | null;
