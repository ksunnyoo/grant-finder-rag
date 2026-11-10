import type { FilterInput } from "./types";

export type Condition = {
	region: string;
	target: string;
	category: string;
	bizAge: string;
	age: string;
	endFrom: string;
	endTo: string;
	includeClosed: boolean;
};

export const EMPTY_CONDITION: Condition = {
	region: "",
	target: "",
	category: "",
	bizAge: "",
	age: "",
	endFrom: "",
	endTo: "",
	includeClosed: false,
};

function parseAge(text: string): number | undefined {
	const n = Number.parseInt(text, 10);
	return Number.isNaN(n) ? undefined : n;
}

/** 입력값이 잘못되었으면 오류 문구를, 아니면 null을 돌려준다. */
export function conditionError(c: Condition): string | null {
	if (c.endFrom && c.endTo && c.endFrom > c.endTo) {
		return "마감 기간의 시작일이 종료일보다 늦습니다.";
	}
	if (c.age) {
		const n = parseAge(c.age);
		if (n === undefined || n < 0 || n > 120) {
			return "연령은 0~120 사이의 숫자로 입력해 주십시오.";
		}
	}
	return null;
}

export function toFilterInput(c: Condition): FilterInput {
	return {
		region: c.region ? [c.region] : [],
		target: c.target ? [c.target] : [],
		category: c.category ? [c.category] : [],
		bizAge: c.bizAge ? [c.bizAge] : [],
		age: parseAge(c.age),
		endFrom: c.endFrom || undefined,
		endTo: c.endTo || undefined,
		includeClosed: c.includeClosed,
	};
}
