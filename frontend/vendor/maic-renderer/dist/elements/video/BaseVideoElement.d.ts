import type { ReactNode } from 'react';
import type { PPTVideoElement } from '@maic/dsl';
export interface BaseVideoElementProps {
    elementInfo: PPTVideoElement;
    /**
     * Optional render slot: replace the default <video> with custom content.
     * Lets consumers inject placeholders, retry UI, lazy media resolvers, or
     * controlled playback bound to their own orchestration state.
     * When omitted, the package renders a plain <video src controls preload="metadata">.
     */
    renderVideo?: (element: PPTVideoElement) => ReactNode;
}
export declare function BaseVideoElement({ elementInfo, renderVideo }: BaseVideoElementProps): import("react/jsx-runtime").JSX.Element;
