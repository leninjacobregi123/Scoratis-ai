import type { PPTTextElement } from '@maic/dsl';
export interface BaseTextElementProps {
    elementInfo: PPTTextElement;
    target?: string;
}
export declare function BaseTextElement({ elementInfo, target }: BaseTextElementProps): import("react/jsx-runtime").JSX.Element;
