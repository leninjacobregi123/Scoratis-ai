import type { SpotlightEffectOptions } from '../types/effects';
export interface SpotlightOverlayProps {
    options?: SpotlightEffectOptions;
    /** ID prefix the SlideElement uses on its root div. Default `slide-element-`. */
    elementIdPrefix?: string;
}
export declare function SpotlightOverlay({ options, elementIdPrefix, }: SpotlightOverlayProps): import("react/jsx-runtime").JSX.Element;
