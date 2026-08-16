import type { ComposeOption } from 'echarts/core';
import type { BarSeriesOption, LineSeriesOption, PieSeriesOption, ScatterSeriesOption, RadarSeriesOption } from 'echarts/charts';
import type { ChartData, ChartType } from '@maic/dsl';
type EChartOption = ComposeOption<BarSeriesOption | LineSeriesOption | PieSeriesOption | ScatterSeriesOption | RadarSeriesOption>;
export interface ChartOptionPayload {
    type: ChartType;
    data: ChartData;
    themeColors: string[];
    textColor?: string;
    lineColor?: string;
    lineSmooth?: boolean;
    stack?: boolean;
}
export declare const getChartOption: ({ type, data, themeColors, textColor, lineColor, lineSmooth, stack, }: ChartOptionPayload) => EChartOption | null;
export {};
