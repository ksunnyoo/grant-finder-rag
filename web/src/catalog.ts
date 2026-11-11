import type { FilterInput, Meta, Source } from "./types";

export type CatalogItem = {
	id: string;
	title: string;
	agency: string | null;
	category: string | null;
	region: string | null;
	target: string[];
	bizAge: string[];
	ages: [number, number][];
	startDate: string | null;
	endDate: string | null;
	url: string | null;
	snippet: string;
};

export type Catalog = {
	asOfDate: string;
	generatedAt: string;
	meta: Omit<Meta, "refuseThreshold">;
	regionExpansion: Record<string, string[]>;
	items: CatalogItem[];
};

export async function loadCatalog(): Promise<Catalog> {
	const res = await fetch(`${import.meta.env.BASE_URL}demo/catalog.json`);
	if (!res.ok) throw new Error("공고 목록을 불러오지 못했습니다.");
	return res.json() as Promise<Catalog>;
}

function overlaps(a: string[], b: string[]): boolean {
	return a.some((x) => b.includes(x));
}

/**
 * 조건으로 공고를 거른다. 의미는 SDD 5.2절과 같다.
 * 지역·분야는 값이 있어야 통과하고, 대상·업력·연령은 값이 비어 있으면 통과한다.
 */
export function filterCatalog(
	items: CatalogItem[],
	f: FilterInput,
	asOfDate: string,
	regionExpansion: Record<string, string[]>,
): CatalogItem[] {
	const regions = new Set<string>();
	if (f.region?.length) {
		regions.add("전국");
		for (const r of f.region) {
			for (const x of regionExpansion[r] ?? [r]) regions.add(x);
		}
	}
	let lower = f.endFrom;
	if (!f.includeClosed) {
		lower = lower && lower > asOfDate ? lower : asOfDate;
	}
	return items.filter((it) => {
		if (regions.size > 0 && !(it.region !== null && regions.has(it.region))) {
			return false;
		}
		if (f.target?.length && it.target.length > 0) {
			if (!overlaps(it.target, f.target)) return false;
		}
		if (f.bizAge?.length && it.bizAge.length > 0) {
			if (!overlaps(it.bizAge, f.bizAge)) return false;
		}
		if (f.age !== undefined && it.ages.length > 0) {
			const age = f.age;
			if (!it.ages.some(([lo, hi]) => lo <= age && age <= hi)) return false;
		}
		if (f.category?.length) {
			if (it.category === null || !f.category.includes(it.category)) {
				return false;
			}
		}
		if (lower || f.endTo) {
			if (it.endDate === null) return false;
			if (lower && it.endDate < lower) return false;
			if (f.endTo && it.endDate > f.endTo) return false;
		}
		return true;
	});
}

/** 공백으로 나눈 낱말이 모두 들어 있는 공고만 남긴다. 비어 있으면 모두 통과. */
export function matchKeywords(
	items: CatalogItem[],
	query: string,
): CatalogItem[] {
	const words = query.toLowerCase().split(/\s+/).filter(Boolean);
	if (words.length === 0) return items;
	return items.filter((it) => {
		const hay = [it.title, it.agency, it.category, it.region, it.snippet]
			.join(" ")
			.toLowerCase();
		return words.every((w) => hay.includes(w));
	});
}

/** 마감일이 가까운 순으로, 마감일이 없는 공고는 맨 뒤로 정렬한다. */
export function sortByEnd(items: CatalogItem[]): CatalogItem[] {
	return [...items].sort((a, b) => {
		if (a.endDate === b.endDate) return a.id.localeCompare(b.id);
		if (a.endDate === null) return 1;
		if (b.endDate === null) return -1;
		return a.endDate < b.endDate ? -1 : 1;
	});
}

function daysBetween(from: string, to: string): number {
	const a = Date.parse(`${from}T00:00:00Z`);
	const b = Date.parse(`${to}T00:00:00Z`);
	return Math.round((b - a) / 86_400_000);
}

export function toSource(
	it: CatalogItem,
	f: FilterInput,
	asOfDate: string,
): Source {
	const flags: string[] = [];
	if (f.target?.length && it.target.length === 0) flags.push("대상 미기재");
	if (f.bizAge?.length && it.bizAge.length === 0) flags.push("업력 미기재");
	if (f.age !== undefined && it.ages.length === 0) flags.push("연령 미기재");
	return {
		id: it.id,
		title: it.title,
		agency: it.agency,
		category: it.category,
		region: it.region,
		endDate: it.endDate,
		dDay: it.endDate ? daysBetween(asOfDate, it.endDate) : null,
		snippet: it.snippet,
		url: it.url ?? "",
		flags,
	};
}
