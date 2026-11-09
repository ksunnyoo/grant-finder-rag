import type { FilterInput } from "./types";

export type Condition = {
	region: string;
	target: string;
	category: string;
	includeClosed: boolean;
};

export const EMPTY_CONDITION: Condition = {
	region: "",
	target: "",
	category: "",
	includeClosed: false,
};

export function toFilterInput(c: Condition): FilterInput {
	return {
		region: c.region ? [c.region] : [],
		target: c.target ? [c.target] : [],
		category: c.category ? [c.category] : [],
		includeClosed: c.includeClosed,
	};
}
