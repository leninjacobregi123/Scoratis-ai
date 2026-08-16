import type { ReactNode } from 'react';
import type { PPTImageElement } from '@maic/dsl';
export interface BaseImageElementProps {
    elementInfo: PPTImageElement;
    /**
     * Optional render slot: replace the default <img> with custom content.
     * The slot receives `(element, resolvedSrc)` and is responsible for rendering
     * placeholders, retry UI, business-specific resolvers (e.g. AI media generation),
     * etc. The package itself does not interpret `src` beyond passing it through.
     */
    renderImage?: (element: PPTImageElement, resolvedSrc: string) => ReactNode;
}
export declare function BaseImageElement({ elementInfo, renderImage }: BaseImageElementProps): import("react/jsx-runtime").JSX.Element;
