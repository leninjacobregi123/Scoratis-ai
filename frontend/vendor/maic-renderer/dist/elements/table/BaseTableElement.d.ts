import type { PPTTableElement } from '@maic/dsl';
export interface BaseTableElementProps {
    elementInfo: PPTTableElement;
    target?: string;
}
export declare function BaseTableElement({ elementInfo, target }: BaseTableElementProps): import("react/jsx-runtime").JSX.Element;
