import type { PPTChartElement } from '@maic/dsl';
export interface BaseChartElementProps {
    elementInfo: PPTChartElement;
    target?: string;
}
export declare function BaseChartElement({ elementInfo, target }: BaseChartElementProps): import("react/jsx-runtime").JSX.Element;
