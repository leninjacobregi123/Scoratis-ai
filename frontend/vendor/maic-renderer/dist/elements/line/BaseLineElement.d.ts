import type { PPTLineElement } from '@maic/dsl';
export interface BaseLineElementProps {
    elementInfo: PPTLineElement;
    animate?: boolean;
}
export declare function BaseLineElement({ elementInfo, animate }: BaseLineElementProps): import("react/jsx-runtime").JSX.Element;
