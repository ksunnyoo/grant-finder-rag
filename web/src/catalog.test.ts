import { describe, expect, it } from "vitest";
import {
	type CatalogItem,
	effectiveAsOf,
	filterCatalog,
	matchKeywords,
	sortByEnd,
	todayISO,
	toSource,
} from "./catalog";

const EXP = { 전남: ["전남", "전남광주"], 광주: ["광주", "전남광주"] };
const AS_OF = "2026-11-06";

function item(over: Partial<CatalogItem>): CatalogItem {
	return {
		id: "x",
		title: "t",
		agency: null,
		category: "사업화",
		region: "서울",
		target: [],
		bizAge: [],
		ages: [],
		startDate: null,
		endDate: "2026-12-01",
		url: null,
		snippet: "",
		...over,
	};
}
const ids = (xs: CatalogItem[]) => xs.map((i) => i.id);

describe("filterCatalog", () => {
	it("조건이 없으면 마감된 공고만 뺀다", () => {
		const items = [
			item({ id: "a" }),
			item({ id: "b", endDate: "2026-11-01" }),
			item({ id: "c", endDate: null }),
		];
		expect(ids(filterCatalog(items, {}, AS_OF, EXP))).toEqual(["a"]);
		expect(
			ids(filterCatalog(items, { includeClosed: true }, AS_OF, EXP)),
		).toEqual(["a", "b", "c"]);
	});

	it("지역은 전국을 포함하고 지역이 비면 뺀다", () => {
		const items = [
			item({ id: "s", region: "서울" }),
			item({ id: "n", region: "전국" }),
			item({ id: "b", region: "부산" }),
			item({ id: "e", region: null }),
		];
		expect(ids(filterCatalog(items, { region: ["서울"] }, AS_OF, EXP))).toEqual(
			["s", "n"],
		);
	});

	it("전남과 광주는 전남광주 공고도 본다", () => {
		const items = [
			item({ id: "g", region: "전남광주" }),
			item({ id: "j", region: "전남" }),
			item({ id: "k", region: "광주" }),
		];
		expect(ids(filterCatalog(items, { region: ["전남"] }, AS_OF, EXP))).toEqual(
			["g", "j"],
		);
		expect(ids(filterCatalog(items, { region: ["광주"] }, AS_OF, EXP))).toEqual(
			["g", "k"],
		);
	});

	it("업력 대상 연령은 값이 비면 통과하고 있으면 겹쳐야 한다", () => {
		const items = [
			item({ id: "empty" }),
			item({ id: "pre", bizAge: ["예비창업자"] }),
			item({ id: "y3", bizAge: ["3년미만"] }),
			item({ id: "age", ages: [[20, 39]] }),
			item({ id: "old", ages: [[40, 60]] }),
		];
		expect(
			ids(filterCatalog(items, { bizAge: ["예비창업자"] }, AS_OF, EXP)),
		).toEqual(["empty", "pre", "age", "old"]);
		expect(ids(filterCatalog(items, { age: 30 }, AS_OF, EXP))).toEqual([
			"empty",
			"pre",
			"y3",
			"age",
		]);
	});

	it("분야는 값이 같아야 하고 마감 기간은 마감일 없는 공고를 뺀다", () => {
		const items = [
			item({ id: "a", category: "사업화", endDate: "2026-12-05" }),
			item({ id: "b", category: "인력", endDate: "2026-12-05" }),
			item({ id: "c", category: "사업화", endDate: "2027-01-05" }),
			item({ id: "d", category: "사업화", endDate: null }),
		];
		expect(
			ids(filterCatalog(items, { category: ["사업화"] }, AS_OF, EXP)),
		).toEqual(["a", "c"]);
		expect(
			ids(filterCatalog(items, { endTo: "2026-12-31" }, AS_OF, EXP)),
		).toEqual(["a", "b"]);
	});

	it("마감 시작일이 기준일보다 빠르면 기준일을 쓴다", () => {
		const items = [item({ id: "old", endDate: "2026-10-20" })];
		expect(
			filterCatalog(items, { endFrom: "2026-10-01" }, AS_OF, EXP),
		).toHaveLength(0);
		expect(
			filterCatalog(
				items,
				{ endFrom: "2026-10-01", includeClosed: true },
				AS_OF,
				EXP,
			),
		).toHaveLength(1);
	});
});

describe("matchKeywords / sortByEnd / toSource", () => {
	const items = [
		item({ id: "a", title: "푸드테크 창업교육", endDate: "2026-12-10" }),
		item({
			id: "b",
			title: "투자유치",
			snippet: "푸드테크 기업",
			endDate: null,
		}),
		item({ id: "c", title: "R&D", endDate: "2026-11-20" }),
	];
	it("낱말이 모두 있어야 남긴다", () => {
		expect(ids(matchKeywords(items, "푸드테크"))).toEqual(["a", "b"]);
		expect(ids(matchKeywords(items, "푸드테크 창업교육"))).toEqual(["a"]);
		expect(matchKeywords(items, "  ")).toHaveLength(3);
	});
	it("마감이 가까운 순으로 정렬하고 없으면 뒤로 보낸다", () => {
		expect(ids(sortByEnd(items))).toEqual(["c", "a", "b"]);
	});
	it("D-day와 미기재 표시를 계산한다", () => {
		const s = toSource(
			item({ id: "z", endDate: "2026-11-09" }),
			{ bizAge: ["예비창업자"], age: 30 },
			AS_OF,
		);
		expect(s.dDay).toBe(3);
		expect(s.flags).toEqual(["업력 미기재", "연령 미기재"]);
	});
});

describe("오늘 날짜 기준", () => {
	it("날짜를 YYYY-MM-DD로 만든다", () => {
		expect(todayISO(new Date(2026, 10, 11))).toBe("2026-11-11");
		expect(todayISO(new Date(2026, 0, 5))).toBe("2026-01-05");
	});
	it("저장 기준일과 오늘 중 늦은 날짜를 쓴다", () => {
		expect(effectiveAsOf("2026-11-06", "2026-11-11")).toBe("2026-11-11");
		expect(effectiveAsOf("2026-11-20", "2026-11-11")).toBe("2026-11-20");
	});
	it("오늘 기준으로 마감된 공고는 빠지고 D-day가 줄어든다", () => {
		const items = [
			item({ id: "gone", endDate: "2026-11-09" }),
			item({ id: "stay", endDate: "2026-11-30" }),
		];
		const asOf = effectiveAsOf("2026-11-06", "2026-11-11");
		const got = filterCatalog(items, {}, asOf, EXP);
		expect(ids(got)).toEqual(["stay"]);
		expect(toSource(got[0], {}, asOf).dDay).toBe(19);
	});
});
