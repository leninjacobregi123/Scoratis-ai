import type { ChartData, ChartOptions, ChartType } from '@maic/dsl';
interface ChartProps {
    width: number;
    height: number;
    type: ChartType;
    data: ChartData;
    themeColors: string[];
    textColor?: string;
    lineColor?: string;
    options?: ChartOptions;
}
export declare function Chart({ width: _width, height: _height, type, data, themeColors: rawThemeColors, textColor, lineColor, options, }: ChartProps): import("react/jsx-runtime").JSX.Element;
export {};
