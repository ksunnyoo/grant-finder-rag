import { useMemo, useState } from "react";
import {
	type Catalog,
	effectiveAsOf,
	filterCatalog,
	matchKeywords,
	sortByEnd,
	toSource,
} from "../catalog";
import {
	type Condition,
	conditionError,
	EMPTY_CONDITION,
	toFilterInput,
} from "../condition";
import type { SavedNotice } from "../saved";
import type { Meta } from "../types";
import { ConditionPanel } from "./ConditionPanel";
import { SourceCard } from "./SourceCard";

const PAGE = 20;
const REPO_URL = "https://github.com/ksunnyoo/grant-finder-rag";
const CLOSED_URL =
	"https://www.k-startup.go.kr/web/contents/bizpbanc-deadline.do";

type Props = {
	catalog: Catalog | null;
	bookmarks: SavedNotice[];
	onToggleSave: (notice: SavedNotice, on: boolean) => void;
	error: string | null;
};

export function CatalogView({
	catalog,
	bookmarks,
	onToggleSave,
	error,
}: Props) {
	const [condition, setCondition] = useState<Condition>(EMPTY_CONDITION);
	const [keyword, setKeyword] = useState("");
	const [shown, setShown] = useState(PAGE);
	const invalid = conditionError(condition);
	const filter = useMemo(() => toFilterInput(condition), [condition]);
	const meta: Meta | null = catalog
		? { ...catalog.meta, refuseThreshold: 0 }
		: null;

	// 저장 기준일과 오늘 중 늦은 날짜를 기준으로 거르고 D-day를 센다.
	const asOf = catalog ? effectiveAsOf(catalog.asOfDate) : "";

	const results = useMemo(() => {
		if (!catalog || invalid) return [];
		const byCondition = filterCatalog(
			catalog.items,
			filter,
			asOf,
			catalog.regionExpansion,
		);
		return sortByEnd(matchKeywords(byCondition, keyword));
	}, [catalog, filter, keyword, invalid, asOf]);

	return (
		<>
			<div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">
				<p className="font-medium">조건으로 공고를 찾습니다.</p>
				<p className="mt-1 text-xs">
					서버 없이 브라우저에서 고른 조건에 맞는 공고를 거릅니다. AI가 답변을
					만들지는 않습니다. 질문에 답하는 AI 기능은{" "}
					<a
						className="underline"
						href={REPO_URL}
						target="_blank"
						rel="noreferrer"
					>
						저장소
					</a>
					의 실행 방법대로 내 컴퓨터에서 실행할 때 쓸 수 있습니다.
				</p>
				<p className="mt-1 text-xs">
					마감 전 공고만 담았습니다. 마감된 공고는{" "}
					<a
						className="underline"
						href={CLOSED_URL}
						target="_blank"
						rel="noreferrer"
					>
						K-Startup 모집마감 목록
					</a>
					에서 확인하십시오.
				</p>
			</div>

			<ConditionPanel
				meta={meta}
				value={condition}
				hideClosed
				note="고른 조건을 모두 만족하는 공고를 보여 줍니다. 대상, 업력, 연령이 비어 있는 공고는 통과시키고 '미기재'로 표시합니다."
				onChange={(next) => {
					setCondition(next);
					setShown(PAGE);
				}}
			/>

			<label className="block text-xs font-medium text-slate-600">
				낱말 검색 (선택, 공백으로 나누면 모두 들어간 공고만 찾습니다)
				<input
					type="search"
					className="mt-1 w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-800"
					placeholder="예: 푸드테크 창업교육"
					value={keyword}
					onChange={(e) => {
						setKeyword(e.target.value);
						setShown(PAGE);
					}}
				/>
			</label>

			{error && (
				<div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
					{error}
				</div>
			)}
			{!catalog && !error && (
				<p className="text-sm text-slate-500">공고 목록을 불러오는 중입니다.</p>
			)}

			{catalog && !invalid && (
				<section className="space-y-2">
					<h2 className="text-sm font-semibold text-slate-700">
						조건에 맞는 공고 {results.length}건
						<span className="ml-2 font-normal text-slate-500">
							(오늘 {asOf} 기준, 목록 수집 기준일 {catalog.asOfDate}, 전체{" "}
							{catalog.items.length}건 중)
						</span>
					</h2>
					{results.length === 0 && (
						<p className="text-sm text-slate-600">
							조건에 맞는 공고가 없습니다. 조건을 줄여 보십시오.
						</p>
					)}
					{results.slice(0, shown).map((it) => (
						<SourceCard
							key={it.id}
							source={toSource(it, filter, asOf)}
							saved={bookmarks.some((b) => b.id === it.id)}
							onToggleSave={() =>
								onToggleSave(
									{
										id: it.id,
										title: it.title,
										endDate: it.endDate,
										url: it.url ?? "",
									},
									!bookmarks.some((b) => b.id === it.id),
								)
							}
						/>
					))}
					{results.length > shown && (
						<button
							type="button"
							onClick={() => setShown(shown + PAGE)}
							className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm hover:bg-slate-100"
						>
							더 보기 ({results.length - shown}건 남음)
						</button>
					)}
				</section>
			)}
		</>
	);
}
