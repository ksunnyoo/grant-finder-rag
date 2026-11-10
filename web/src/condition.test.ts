import { describe, expect, it } from "vitest";
import {
	type Condition,
	conditionError,
	EMPTY_CONDITION,
	toFilterInput,
} from "./condition";

function make(patch: Partial<Condition>): Condition {
	return { ...EMPTY_CONDITION, ...patch };
}

describe("conditionError", () => {
	it("아무것도 입력하지 않으면 오류가 없다", () => {
		expect(conditionError(EMPTY_CONDITION)).toBeNull();
	});

	it("마감 시작일이 종료일보다 늦으면 오류를 돌려준다", () => {
		const c = make({ endFrom: "2026-12-31", endTo: "2026-12-01" });
		expect(conditionError(c)).toBe("마감 기간의 시작일이 종료일보다 늦습니다.");
	});

	it("시작일과 종료일이 같거나 시작일이 빠르면 오류가 없다", () => {
		expect(
			conditionError(make({ endFrom: "2026-12-01", endTo: "2026-12-01" })),
		).toBeNull();
		expect(
			conditionError(make({ endFrom: "2026-12-31", endTo: "2027-01-31" })),
		).toBeNull();
	});

	it("날짜가 하나만 있으면 순서를 검사하지 않는다", () => {
		expect(conditionError(make({ endFrom: "2026-12-31" }))).toBeNull();
		expect(conditionError(make({ endTo: "2026-12-01" }))).toBeNull();
	});

	it("연령이 0~120 범위 밖이거나 숫자가 아니면 오류를 돌려준다", () => {
		const message = "연령은 0~120 사이의 숫자로 입력해 주십시오.";
		expect(conditionError(make({ age: "-1" }))).toBe(message);
		expect(conditionError(make({ age: "121" }))).toBe(message);
		expect(conditionError(make({ age: "abc" }))).toBe(message);
	});

	it("연령 0과 120은 허용한다", () => {
		expect(conditionError(make({ age: "0" }))).toBeNull();
		expect(conditionError(make({ age: "120" }))).toBeNull();
	});
});

describe("toFilterInput", () => {
	it("빈 조건은 빈 목록과 undefined로 바뀐다", () => {
		expect(toFilterInput(EMPTY_CONDITION)).toEqual({
			region: [],
			target: [],
			category: [],
			bizAge: [],
			age: undefined,
			endFrom: undefined,
			endTo: undefined,
			includeClosed: false,
		});
	});

	it("입력한 값만 담고 연령은 숫자로 바꾼다", () => {
		const c = make({
			region: "서울",
			bizAge: "예비창업자",
			age: "29",
			endFrom: "2026-11-11",
			endTo: "2026-12-12",
			includeClosed: true,
		});
		expect(toFilterInput(c)).toEqual({
			region: ["서울"],
			target: [],
			category: [],
			bizAge: ["예비창업자"],
			age: 29,
			endFrom: "2026-11-11",
			endTo: "2026-12-12",
			includeClosed: true,
		});
	});
});
