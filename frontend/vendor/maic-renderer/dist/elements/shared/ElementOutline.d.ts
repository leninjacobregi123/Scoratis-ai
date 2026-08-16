import type { PPTElementOutline } from '@maic/dsl';
export interface ElementOutlineProps {
    width: number;
    height: number;
    outline?: PPTElementOutline;
}
export declare function ElementOutline({ width, height, outline }: ElementOutlineProps): import("react/jsx-runtime").JSX.Element | null;
