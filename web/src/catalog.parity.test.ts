import { describe, expect, it } from "vitest";
import { type Catalog, filterCatalog } from "./catalog";
import type { FilterInput } from "./types";

type Checks = {
	asOfDate: string;
	cases: { filter: FilterInput; expectedIds: string[] }[];
};

// export_catalog.py가 만든 파일이 있어야 비교할 수 있다. 정답은 파이썬 필터(build_filter)의 결과다.
// 파일이 없으면 glob이 비어 있어 이 검사는 건너뛴다.
const catalogs = import.meta.glob("../public/demo/catalog.json", {
	eager: true,
	import: "default",
}) as Record<string, Catalog>;
const checkFiles = import.meta.glob("./catalog_checks.json", {
	eager: true,
	import: "default",
}) as Record<string, Checks>;
const catalog = Object.values(catalogs)[0];
const checks = Object.values(checkFiles)[0];
const ready = catalog !== undefined && checks !== undefined;

describe.skipIf(!ready)("파이썬 필터와 화면 필터의 결과 일치", () => {
	it("기준일이 같다", () => {
		expect(catalog.asOfDate).toBe(checks.asOfDate);
	});

	it("검증 사례가 충분하다", () => {
		expect(checks.cases.length).toBeGreaterThanOrEqual(20);
	});

	for (const c of ready ? checks.cases : []) {
		it(`조건 ${JSON.stringify(c.filter)}`, () => {
			const got = filterCatalog(
				catalog.items,
				c.filter,
				catalog.asOfDate,
				catalog.regionExpansion,
			)
				.map((i) => i.id)
				.sort();
			expect(got).toEqual(c.expectedIds);
		});
	}
});
